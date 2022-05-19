# -*- coding: utf-8 -*-
""" Calculations provided by aiida_turborvb turborvb main executable.
"""

from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.plugins import DataFactory
from aiida.orm import SinglefileData, Dict, Str, StructureData
from aiida_turborvb.auxiliary import NamelistHolder

BasisSet = DataFactory("gaussian.basisset")
BasisSetFree = DataFactory("gaussian.basissetfree")

nh_system = NamelistHolder("system")
nh_system.add_value("posunits", str, "bohr")
nh_system.add_value("natoms", int, 1)
nh_system.add_value("ntyp", int, 1)
nh_system.add_value("complexfort10", bool, False)
nh_system.add_value("pbcfort10", bool, False)

nh_electrons = NamelistHolder("electrons")
nh_electrons.add_value("orbtype", str, "normal")
nh_electrons.add_value("jorbtype", str, "normal")
nh_electrons.add_value("twobody", int, -15)
nh_electrons.add_value("twobodypar", float, 1.0)
nh_electrons.add_value("twobodypar(1)", float, 1.0, True)
nh_electrons.add_value("twobodypar(2)", float, 1.0, True)
nh_electrons.add_value("filling", str, "diagonal")
nh_electrons.add_value("yes_crystal", bool, False)
nh_electrons.add_value("yes_crystalj", bool, False)
nh_electrons.add_value("no_4body_jas", bool, True)
nh_electrons.add_value("neldiff", int, 0)
nh_electrons.add_value("onebodypar(1)", float, 1.0, True)

nh_symmetries = NamelistHolder("symmetries")
nh_symmetries.add_value("nosym", bool, False)
nh_symmetries.add_value("eqatoms", bool, True)
nh_symmetries.add_value("rot_det", bool, True)
nh_symmetries.add_value("symmagp", bool, True, True)
nh_symmetries.add_value("nosym_contr", bool, True, True)

class TurboRVBMakefort10CalculationSA(CalcJob):
    """
    AiiDA calculation plugin for TurboRVB.

    Serves as a calculation job provider for TurboRVB main executable,
    for execution of quantum monte carlo calculations
    """

    @classmethod
    def define(cls, spec):
        """Define inputs and outputs of the calculation."""
        # yapf: disable
        super().define(spec)

        # set default values for AiiDA options
        spec.inputs['metadata']['options']['resources'].default = {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1,
        }
        spec.input('structure', valid_type=StructureData, help='')
        spec.input('parameters', valid_type=Dict, help='')
        spec.input_namespace('determinant_basis', valid_type=(Dict, BasisSet, BasisSetFree), help='')
        spec.input_namespace('jastrow_basis',
                             valid_type=(Dict, BasisSet, BasisSetFree),
                             required=False,
                             default={},
                             help='')

        spec.output('fort10', valid_type=SinglefileData, help='')

        spec.inputs['metadata']['options']['parser_name'].default = 'turborvb.makefort10sa'
        spec.inputs['metadata']['options']['input_filename'].default = 'makefort10.input'
        spec.inputs['metadata']['options']['output_filename'].default = 'makefort10.output'

        spec.exit_code(300, 'ERROR_MISSING_OUTPUT_FILES', message='Calculation did not produce all expected output files.')

    def prepare_for_submission(self, folder):
        """
        Create input files.

        :param folder: an `aiida.common.folders.Folder` where the plugin should temporarily place all files
            needed by the calculation.
        :return: `aiida.common.datastructures.CalcInfo` instance
        """

        def toDict(basisset):
            if isinstance(basisset, Dict):
                return basisset.get_dict()
            if isinstance(basisset, (BasisSet, BasisSetFree)):
                ret = {"basis" : []}
                for block in basisset.attributes["blocks"]:
                    n = block["n"]
                    l = block["l"][0][0]
                    ao = [ [l, exp, cont] for exp, cont in block["coefficients"]]
                    ret["basis"].append(ao)
                ret["valence_electrons"] = basisset.attributes["n_el"]
                return ret

        from ase.data import atomic_numbers
        from ase.units import Bohr

        orbital_cont_library = { 0 : 300,
                                 1 : 400,
                                 2 : 500,
                                 3 : 600,
                                 4 : 700,
                                 5 : 800 }

        orbital_library = { 0 : 16,
                            1 : 36,
                            2 : 68,
                            3 : 48,
                            4 : 51,
                            5 : 72 }

        mf10_input = "makefort10.input"
        parameters = self.inputs.parameters.get_dict()
        ase_structure = self.inputs.structure.get_ase()
        atom_types = set(ase_structure.get_chemical_symbols())
        pseudo = False

        try:
            if parameters["pseudo"]:
                pseudo = True
        except:
            pass

        nh_electrons.update("twobody", -15)
        if pseudo:
            nh_electrons.update("twobody", -6)
        nh_system.update("natoms", len(ase_structure))
        nh_system.update("ntyp", len(atom_types))

        if "namelist_update" in parameters:
            for key, value in parameters["namelist_update"].items():
                if key in nh_system.get_keys():
                    nh_system.update(key, value)
                if key in nh_electrons.get_keys():
                    nh_electrons.update(key, value)
                if key in nh_symmetries.get_keys():
                    nh_symmetries.update(key, value)

        with folder.open(self.options.input_filename, "w") as fhandle:
            nh_system.dump(fhandle)
            nh_electrons.dump(fhandle)
            nh_symmetries.dump(fhandle)

            atom_basis = { atomt: toDict(self.inputs.determinant_basis[atomt]) for atomt in atom_types }
            atom_basisj = { atomt: toDict(self.inputs.jastrow_basis[atomt]) for atomt in atom_types if atomt in self.inputs.jastrow_basis }

            fhandle.write("ATOMIC_POSITIONS\n")
            for atom in ase_structure:
                fhandle.write(f"{float(atom_basis[atom.symbol]['valence_electrons'])} {float(atomic_numbers[atom.symbol])} " + ("  ".join(["{:3.10f}"] * 3)).format(*(atom.position/Bohr)) + "\n")
            fhandle.write("/\n")

            for element, basdict in atom_basis.items():
                det_bas = basdict["basis"]
                jas_bas = {}
                nshelldet = len(det_bas)
                fhandle.write(f"ATOM_{atomic_numbers[element]}\n")
                fhandle.write(f"&shells\n")
                fhandle.write(f"nshelldet={nshelldet}\n")
                try:
                    jas_bas = atom_basisj[element]["basis"]
                    nshelljas = len(jas_bas)
                    fhandle.write(f"nshelljas={nshelljas}\n")
                except:
                    pass
                fhandle.write("/\n")
                for ao in det_bas:
                    numgto = len(ao)
                    if numgto == 1:
                        # Single GTO case
                        gto = ao[0]
                        fhandle.write(f"{gto[0]*2 + 1} 1 {orbital_library[gto[0]]}\n")
                        fhandle.write(f"1 {gto[1]}\n")
                    else:
                        # Multiple GTO case one angular momentum
                        orbs = { orb for orb, exp, coef in ao }
                        if len(orbs) == 1:
                            angular_mom = orbs.pop()
                            number_orbs = len(ao)
                            fhandle.write(f"{angular_mom*2 + 1} {number_orbs*2} {orbital_cont_library[angular_mom]}\n")
                            fhandle.write(f"1 {' '.join([ '{:20.17f}'.format(b) for a, b, c in ao ])} {' '.join([ '{:20.17f}'.format(c) for a, b, c in ao ])}\n")
                fhandle.write("#  Parameters atomic Jastrow wf\n")
                for ao in jas_bas:
                    numgto = len(ao)
                    if numgto == 1:
                        # Single GTO case
                        gto = ao[0]
                        fhandle.write(f"{gto[0]*2 + 1} 1 {orbital_library[gto[0]]}\n")
                        fhandle.write(f"1 {gto[1]}\n")
                    else:
                        # Multiple GTO case one angular momentum
                        orbs = { orb for orb, exp, coef in ao }
                        if len(orbs) == 1:
                            angular_mom = orbs.pop()
                            number_orbs = len(ao)
                            fhandle.write(f"{angular_mom*2 + 1} {number_orbs*2} {orbital_cont_library[angular_mom]}\n")
                            fhandle.write(f"1 {' '.join([ '{:20.17f}'.format(b) for a, b, c in ao ])} {' '.join([ '{:20.17f}'.format(c) for a, b, c in ao ])}\n")

        codeinfo = datastructures.CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.cmdline_params = []
        codeinfo.stdin_name = f"{self.inputs.metadata.options.input_filename}"
        codeinfo.stdout_name = f"{self.inputs.metadata.options.output_filename}"

        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        structure = self.inputs.structure.get_ase()

        calcinfo.retrieve_list = ["fort.10_new",
                                  self.options.output_filename]

        return calcinfo
