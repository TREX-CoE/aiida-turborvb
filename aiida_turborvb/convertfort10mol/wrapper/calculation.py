# -*- coding: utf-8 -*-
""" Calculations provided by aiida_turborvb turborvb main executable.
"""

from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.orm import SinglefileData, Dict, Str, StructureData

class TurboRVBConvertfort10molCalculationWRP(CalcJob):
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
        spec.input('fort10', valid_type=SinglefileData, help='')
        spec.input('pseudo', valid_type=SinglefileData, required=False, help='')
        spec.input('parameters', valid_type=Dict, help='')

        spec.output('fort10', valid_type=SinglefileData, help='')

        spec.inputs['metadata']['options']['parser_name'].default = 'turborvb.convertfort10molwrp'
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

        parameters = self.inputs.parameters.get_dict()

        with folder.open("fort.10_in", "w") as fhandle_out, \
             self.inputs.fort10.open() as fhandle_in:
            fhandle_out.write(fhandle_in.read())

        if "pseudo" in self.inputs:
            with folder.open("pseudo.dat", "w") as fhandle_out, \
                 self.inputs.pseudo.open() as fhandle_in:
                fhandle_out.write(fhandle_in.read())

        with folder.open(self.options.input_filename, "w") as fhandle:
            content = []
            content.append('turbo-genius.sh -j convertfort10mol -g')
            if "namelist_update" in parameters:
                content.append("cp convertfort10mol.input source")
                for key, value in parameters["namelist_update"].items():
                    content.append("sed 's/\s*!\?"+key+"\s*=.*$/"+key+"="+f"{value}"+"/g' source > dest")
                    content.append("cp dest source")
                content.append("cp dest convertfort10mol.input")
            content.append('convertfort10mol.x < convertfort10mol.input > convertfort10mol.output')

            fhandle.write("\n".join(content))

        codeinfo = datastructures.CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.cmdline_params = []
        codeinfo.stdin_name = f"{self.inputs.metadata.options.input_filename}"
        codeinfo.stdout_name = f"{self.inputs.metadata.options.output_filename}"

        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]

        calcinfo.retrieve_list = ["fort.10_new",
                                  self.options.output_filename]

        return calcinfo
