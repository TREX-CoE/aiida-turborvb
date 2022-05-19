# -*- coding: utf-8 -*-
"""
Calculations provided by aiida_turborvb turborvb main executable.
"""
from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.orm import SinglefileData, Dict, Str, Float, List
from aiida.plugins import DataFactory

class TurboRVBPrepCalculationWRP(CalcJob):
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
        spec.input('parameters', valid_type=Dict, help='')
        spec.input('fort10', valid_type=SinglefileData, help='')
        spec.input('pseudo', valid_type=SinglefileData, required=False, help='')

        spec.output('fort10', valid_type=SinglefileData, help='')
        spec.output('occfile', valid_type=SinglefileData, help='')
        spec.output('energy', valid_type=Float, help='')
        spec.output('convergance', valid_type=List, help='')

        spec.inputs['metadata']['options']['parser_name'].default = 'turborvb.prepwrp'
        spec.inputs['metadata']['options']['input_filename'].default = 'execute.sh'
        spec.inputs['metadata']['options']['output_filename'].default = 'execute.out'

        spec.exit_code(300, 'ERROR_MISSING_OUTPUT_FILES', message='Calculation did not produce all expected output files.')

    def prepare_for_submission(self, folder):
        """
        Create input files.

        :param folder: an `aiida.common.folders.Folder` where the plugin should temporarily place all files
            needed by the calculation.
        :return: `aiida.common.datastructures.CalcInfo` instance
        """

        resources = self.inputs.metadata['options']['resources']
        parameters = self.inputs.parameters.get_dict()

        with folder.open("fort.10", "w") as fhandle_out, \
             self.inputs.fort10.open() as fhandle_in:
            fhandle_out.write(fhandle_in.read())

        if "pseudo" in self.inputs:
            with folder.open("pseudo.dat", "w") as fhandle_out, \
                 self.inputs.pseudo.open() as fhandle_in:
                fhandle_out.write(fhandle_in.read())

        with folder.open(self.options.input_filename, "w") as fhandle:
            content = []
            mpiproc = resources['num_machines'] * resources['num_mpiprocs_per_machine']
            tg_command = 'turbo-genius.sh -j prep -g'

            if "doublegrid" in parameters:
                if parameters["doublegrid"]:
                    tg_command += " --doublegrid"

            if "grid" in parameters:
                grid =  parameters["grid"]
                tg_command += f" -grid {grid}"

            if "box" in parameters:
                box = parameters["box"]
                if isinstance(box, (list, tuple)):
                    if len(box) == 1:
                        A = B = C = box[0]
                    elif len(box) == 3:
                        A, B, C = box
                    else:
                        raise Exception("Bad box")
                elif isinstance(box, (int, float)):
                    A = B = C = float(box)
                else:
                    raise Exception("Bad box")
                tg_command += f" -box {A} {B} {C}"

            content.append(tg_command)

            if "occupation_update" in parameters:
                content.append("cp prep.input source")
                if isinstance(parameters["occupation_update"], list):
                    if "namelist_update" not in parameters:
                        parameters["namelist_update"] = {}
                    parameters["namelist_update"]["nelocc"] = len(parameters["occupation_update"])
                    occs = " ".join([str(x) for x in parameters["occupation_update"]])
                    content.append("sed 's/^[012][012 ]*/"+occs+"/g' source > dest")
                content.append("cp dest prep.input")

            if "namelist_update" in parameters:
                content.append("cp prep.input source")
                for key, value in parameters["namelist_update"].items():
                    content.append("sed 's/\s*!\?"+key+"\s*=.*$/"+key+"="+f"{value}"+"/g' source > dest")
                    content.append("cp dest source")
                content.append("cp dest prep.input")

            content.append(f'mpirun -np {mpiproc} prep-mpi.x < prep.input > prep.output')

            fhandle.write("\n".join(content))

        codeinfo = datastructures.CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.cmdline_params = []
        codeinfo.stdin_name = f"{self.inputs.metadata.options.input_filename}"
        codeinfo.stdout_name = f"{self.inputs.metadata.options.output_filename}"

        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.local_copy_list = [
            (self.inputs.fort10.uuid, self.inputs.fort10.filename, "fort.10"),
        ]
        calcinfo.retrieve_list = ["fort.10_new",
                                  "occupationlevels.dat",
                                  "prep.output",
                                  self.options.output_filename]


        return calcinfo
