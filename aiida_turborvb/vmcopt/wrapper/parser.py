from aiida.engine import ExitCode
from aiida.parsers.parser import Parser
from aiida.plugins import CalculationFactory
from aiida.common import exceptions
from aiida.orm import Float, SinglefileData, FolderData
import numpy as np

class TurboRVBVmcoptParserWRP(Parser):
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
        output_filename = "vmcopt.output" #self.node.get_option('output_filename')

        files_retrieved = self.retrieved.list_object_names()
        with self.retrieved.open("fort.10_org", 'rb') as handle:
            output_10 = SinglefileData(file=handle)
        with self.retrieved.open("fort.11", 'rb') as handle:
            output_11 = SinglefileData(file=handle)
        with self.retrieved.open("fort.12", 'rb') as handle:
            output_12 = SinglefileData(file=handle)
        with self.retrieved.open("fort.10_averaged", 'rb') as handle:
            output_10_ave = SinglefileData(file=handle)
        with self.retrieved.open("forces.dat", 'rb') as handle:
            output_forces = SinglefileData(file=handle)
        with self.retrieved.open("story.d", 'rb') as handle:
            output_story = SinglefileData(file=handle)

        scratch = FolderData()
        #scratch.put_object_from_tree(self.retrieved)

        self.out('fort10', output_10)
        self.out('fort10_averaged', output_10_ave)
        self.out('fort11', output_11)
        self.out('fort12', output_12)
        self.out('forces', output_forces)
        self.out('story', output_story)

        return ExitCode(0)
