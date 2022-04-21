# -*- coding: utf-8 -*-
""" Calculations provided by aiida_turborvb turborvb main executable.
"""

from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.orm import SinglefileData, Dict, Str, StructureData

parameters_help = """
Input parameters, one can setup basis, jasbasis and pseudo from Turbo-Genius database
"""

class TurboRVBMakefort10CalculationWRP(CalcJob):
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
        spec.input('structure', valid_type=StructureData, help='Input structure')
        spec.input('parameters', valid_type=Dict, help=parameters_help)

        spec.output('fort10', valid_type=SinglefileData, help='Output fort.10 file')

        spec.inputs['metadata']['options']['parser_name'].default = 'turborvb.makefort10wrp'
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

        structure_filename = "structure.xyz"
        with folder.open(structure_filename, "w") as fhandle:
            self.inputs.structure.get_ase().write(fhandle)

        with folder.open(self.options.input_filename, "w") as fhandle:
            content = []
            tg_command = f'turbo-genius.sh -j makefort10 -g '
            tg_command += f' -str {structure_filename}'
            parameters = self.inputs.parameters.get_dict()
            if "basis" in parameters:
                tg_command += f' -basis {parameters["basis"]}'
            if "basisjas" in parameters:
                tg_command += f' -basisjas {parameters["basisjas"]}'
            if "pseudo" in parameters:
                tg_command += f' -pp {parameters["pseudo"]}'
            content.append(tg_command)
            content.append('makefort10.x < makefort10.input > makefort10.output')

            fhandle.write("\n".join(content))


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
