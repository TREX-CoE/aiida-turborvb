# -*- coding: utf-8 -*-
""" Calculations provided by aiida_turborvb turborvb main executable.
"""

from aiida.engine import CalcJob
from aiida.common import datastructures
from aiida.plugins import DataFactory
from aiida.orm import SinglefileData, Dict, Str, StructureData
from aiida.common.datastructures import CalcInfo
import io
from aiida.engine import calcfunction

Pseudo = DataFactory("gaussian.pseudo")

class BytesIOWrapper(io.BufferedReader):
    """
    Taken from https://stackoverflow.com/questions/55889474/convert-io-stringio-to-io-bytesio

    Wrap a buffered bytes stream over TextIOBase string stream.
    """

    def __init__(self, text_io_buffer, encoding=None, errors=None, **kwargs):
        super(BytesIOWrapper, self).__init__(text_io_buffer, **kwargs)
        self.encoding = encoding or text_io_buffer.encoding or 'utf-8'
        self.errors = errors or text_io_buffer.errors or 'strict'

    def _encoding_call(self, method_name, *args, **kwargs):
        raw_method = getattr(self.raw, method_name)
        val = raw_method(*args, **kwargs)
        return val.encode(self.encoding, errors=self.errors)

    def read(self, size=-1):
        return self._encoding_call('read', size)

    def read1(self, size=-1):
        return self._encoding_call('read1', size)

    def peek(self, size=-1):
        return self._encoding_call('peek', size)

class TurboRVBAssemblingpseudoCalculationSA(CalcJob):
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
        spec.input_namespace('pseudodata', valid_type=Pseudo, help='')

        spec.output('pseudo', valid_type=SinglefileData, help='')

        spec.exit_code(300, 'ERROR_MISSING_OUTPUT_FILES', message='Calculation did not produce all expected output files.')

    def prepare_for_submission(self, folder):
        """
        Create input files.

        :param folder: an `aiida.common.folders.Folder` where the plugin should temporarily place all files
            needed by the calculation.
        :return: `aiida.common.datastructures.CalcInfo` instance
        """

        from ase.data import chemical_symbols
        from io import StringIO

        atoms = []
        with self.inputs.fort10.open() as fhandle:
            index = 0
            numat = 0
            for line in fhandle:
                if line.lstrip()[0] == "#":
                    continue
                if index == 0:
                    numat = int(line.split()[2])
                if index > 5:
                    atoms.append(int(float(line.split()[1])))
                index += 1
                if index > numat + 5:
                    break

        pseudo_string = StringIO()
        for index, element in enumerate(sorted(atoms)):
            self.inputs.pseudodata[chemical_symbols[element]].to_turborvb(pseudo_string, index = index + 1)
        pseudo_string.seek(0)
        pseudo_bytes = BytesIOWrapper(pseudo_string)

        pseudo = SinglefileData(pseudo_bytes, "pseudo.dat")
        pseudo.store()
        self.outputs["pseudo"] = pseudo

        calcinfo = CalcInfo()
        calcinfo.codes_info = []
        calcinfo.local_copy_list = []
        calcinfo.remote_copy_list = []
        calcinfo.retrieve_list = []

        return calcinfo

@calcfunction
def assemblingpseudoCalc(fort10, pseudodata):
    """

    """

    from ase.data import chemical_symbols
    from io import StringIO

    atoms = set()
    with fort10.open() as fhandle:
        index = 0
        numat = 0
        for line in fhandle:
            if line.lstrip()[0] == "#":
                continue
            if index == 0:
                numat = int(line.split()[2])
            if index > 5:
                atoms.add(int(float(line.split()[1])))
            index += 1
            if index > numat + 5:
                break

    pseudo_string = StringIO()
    for index, element in enumerate(sorted(atoms)):
        pseudodata[chemical_symbols[element]].to_turborvb(pseudo_string, index = index)
    pseudo_string.seek(0)
    pseudo_bytes = BytesIOWrapper(pseudo_string)

    pseudo = SinglefileData(pseudo_bytes, "pseudo.dat")
    return pseudo


