# -*- coding: utf-8 -*-
"""
Calculations provided by aiida_turborvb turborvb main executable.
"""
from pathlib import Path
from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.orm import SinglefileData, Dict, Str, Float, List, FolderData
from aiida.plugins import DataFactory
from aiida_turborvb.auxiliary import copy_to_file

class TurboRVBLrdmcCalculationWRP(CalcJob):
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
        spec.input('fort11', valid_type=SinglefileData, help='')
        spec.input('fort12', valid_type=SinglefileData, help='')
        spec.input('pseudo', valid_type=SinglefileData, required=False, help='')
        spec.input('trial_energy', valid_type=Float, default=lambda: Float(0.0), required=False, help='')
        spec.input('scratch', valid_type=FolderData, help='')

        spec.output('fort10', valid_type=SinglefileData, help='')
        spec.output('fort11', valid_type=SinglefileData, help='')
        spec.output('fort12', valid_type=SinglefileData, help='')
        spec.output('energydata', valid_type=SinglefileData, help='')
        spec.output('energy', valid_type=Float, help='')
        spec.output('energy_err', valid_type=Float, help='')
        spec.output('variance_square', valid_type=Float, help='')
        spec.output('variance_square_err', valid_type=Float, help='')

        spec.inputs['metadata']['options']['parser_name'].default = 'turborvb.lrdmcwrp'
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

        copy_to_file("turborvb.scratch", ".", self.inputs.scratch, Path(folder.abspath))

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
            tg_command = 'turbo-genius.sh -j lrdmc -g'

            content.append(tg_command)
            content.append(f'cp datasfn.input fn.input')
            if "namelist_update" in parameters:
                content.append("cp fn.input source")
                content.append("sed 's/\s*!\?etry\s*=.*$/etry="+f"{str(self.inputs.trial_energy.value)}"+"/g' source > dest")
                content.append("cp dest source")
                for key, value in parameters["namelist_update"].items():
                    content.append("sed 's/\s*!\?"+key+"\s*=.*$/"+key+"="+f"{value}"+"/g' source > dest")
                    content.append("cp dest source")
                content.append("cp dest fn.input")
            content.append(f'mpirun -np {mpiproc} turborvb-mpi.x < fn.input > fn.output')
            content.append(f'cp fn.output out_fn')
            tg_command = 'turbo-genius.sh -j lrdmc -post -am manual'
            if "eq" in parameters:
                tg_command += f" -eq {parameters['eq']}"
            if "reb" in parameters:
                tg_command += f" -reb {parameters['reb']}"
            if "col" in parameters:
                tg_command += f" -col {parameters['col']}"

            content.append(tg_command)

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
            (self.inputs.fort11.uuid, self.inputs.fort11.filename, "fort.11"),
            (self.inputs.fort12.uuid, self.inputs.fort12.filename, "fort.12"),
        ]
        calcinfo.retrieve_list = ["fort.11",
                                  "fort.12",
                                  "pip0_fn.d",
                                  "turborvb.scratch",
                                  self.options.output_filename]


        return calcinfo
