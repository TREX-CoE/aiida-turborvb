from aiida.engine import ExitCode
from aiida.parsers.parser import Parser
from aiida.plugins import CalculationFactory
from aiida.common import exceptions
from aiida.orm import Float, SinglefileData, FolderData
from aiida_turborvb.auxiliary import copy_between_nodes
import numpy as np

class TurboRVBVmcParserWRP(Parser):
    """
    Parser class for parsing output of calculation.
    """
    def __init__(self, node):
        """
        Initialize Parser instance

        Checks that the ProcessNode being passed was produced by a DiffCalculation.

        :param node: ProcessNode of calculation
        :param type node: :class:`aiida.orm.ProcessNode`
        """
        super().__init__(node)

    def parse(self, **kwargs):
        """
        Parse outputs, store results in database.

        :returns: an exit code, if parsing fails (or nothing if parsing succeeds)
        """
        output_filename = "vmc.output" #self.node.get_option('output_filename')

        files_retrieved = self.retrieved.list_object_names()
        with self.retrieved.open("fort.11", 'rb') as handle:
            output_11 = SinglefileData(file=handle)
        with self.retrieved.open("fort.12", 'rb') as handle:
            output_12 = SinglefileData(file=handle)
        with self.retrieved.open("pip0.d", 'rb') as handle:
            output_energy = SinglefileData(file=handle)
        with self.retrieved.open("pip0.d", 'rb') as handle:
            for ii, line in enumerate(handle):
                if ii == 1:
                    line_split = line.split()
                    energy = Float(float(line_split[-2]))
                    energy_err = Float(float(line_split[-1]))
                if ii == 2:
                    line_split = line.split()
                    variance = Float(float(line_split[-2]))
                    variance_err = Float(float(line_split[-1]))

        scratch = FolderData()
        copy_between_nodes("turborvb.scratch", ".", self.retrieved, scratch)

        self.out('fort11', output_11)
        self.out('fort12', output_12)
        self.out('energydata', output_energy)
        self.out('energy', energy)
        self.out('energy_err', energy_err)
        self.out('variance_square', variance)
        self.out('variance_square_err', variance_err)
        self.out('scratch', scratch)

        return ExitCode(0)
