# -*- coding: utf-8 -*-
"""
Calculations provided by aiida_turborvb turborvb main executable.
"""
from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.orm import SinglefileData, Dict, Str, Float, List, FolderData
from aiida.plugins import DataFactory

class TurboRVBVmcCalculationWRP(CalcJob):
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

        spec.output('fort11', valid_type=SinglefileData, help='')
        spec.output('fort12', valid_type=SinglefileData, help='')
        spec.output('energydata', valid_type=SinglefileData, help='')
        spec.output('energy', valid_type=Float, help='')
        spec.output('energy_err', valid_type=Float, help='')
        spec.output('variance_square', valid_type=Float, help='')
        spec.output('variance_square_err', valid_type=Float, help='')
        spec.output('scratch', valid_type=FolderData, help='')

        spec.inputs['metadata']['options']['parser_name'].default = 'turborvb.vmcwrp'
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
            tg_command = 'turbo-genius.sh -j vmc -g'

            content.append(tg_command)
            content.append(f'cp datasvmc.input vmc.input')
            if "namelist_update" in parameters:
                content.append("cp vmc.input source")
                for key, value in parameters["namelist_update"].items():
                    content.append("sed 's/\s*!\?"+key+"\s*=.*$/"+key+"="+f"{value}"+"/g' source > dest")
                    content.append("cp dest source")
                content.append("cp dest vmc.input")
            content.append(f'mpirun -np {mpiproc} turborvb-mpi.x < vmc.input > vmc.output')
            content.append(f'cp vmc.output out_vmc')
            tg_command = 'turbo-genius.sh -j vmc -post -am manual'
            if "eq" in parameters:
                tg_command += f" -eq {parameters['eq']}"
            if "reb" in parameters:
                tg_command += f" -reb {parameters['reb']}"

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
        ]
        calcinfo.retrieve_list = ["fort.11",
                                  "fort.12",
                                  "fort.12_fn",
                                  "pip0.d",
                                  "out_forcevmc",
                                  "turborvb.scratch",
                                  self.options.output_filename]


        return calcinfo
