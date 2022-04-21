# -*- coding: utf-8 -*-
""" Calculations provided by aiida_turborvb turborvb main executable.
"""

from icecream import ic
from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.orm import SinglefileData, Dict, Str, StructureData

class TurboRVBAssemblingpseudoCalculationWRP(CalcJob):
    """
    AiiDA calculation plugin for TurboRVB assembling pseudo binary.

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
        spec.input('fort10', valid_type=SinglefileData, help='Input fort.10')
        spec.input('parameters', valid_type=Dict, help='Input parameters, only one is necessary: The name of the pseudo family')

        spec.output('pseudo', valid_type=SinglefileData, help='Output pseudo')

        spec.inputs['metadata']['options']['parser_name'].default = 'turborvb.assemblingpseudowrp'
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

        pseudo = self.inputs.parameters.get_dict()["pseudo"]

        with folder.open("fort.10", "w") as fhandle_out, \
             self.inputs.fort10.open() as fhandle_in:
            fhandle_out.write(fhandle_in.read())

        with folder.open(self.options.input_filename, "w") as fhandle:
            content = []
            content.append(f'echo {pseudo} | assembling_pseudo.x')

            fhandle.write("\n".join(content))

        codeinfo = datastructures.CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.cmdline_params = []
        codeinfo.stdin_name = f"{self.inputs.metadata.options.input_filename}"
        codeinfo.stdout_name = f"{self.inputs.metadata.options.output_filename}"

        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]

        calcinfo.retrieve_list = ["pseudo.dat",
                                  self.options.output_filename]

        return calcinfo
