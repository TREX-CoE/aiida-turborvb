from aiida.engine import ExitCode
from aiida.parsers.parser import Parser
from aiida.plugins import CalculationFactory
from aiida.common import exceptions
from aiida.orm import Float, SinglefileData

class TurboRVBMakefort10ParserSA(Parser):
    """
    Parser class for parsing output of calculation.
    """
    def __init__(self, node):
        """
        Initialize Parser instance

        :param node: ProcessNode of calculation
        :param type node: :class:`aiida.orm.ProcessNode`
        """
        super().__init__(node)

    def parse(self, **kwargs):
        """
        Parse outputs, store results in database.

        :returns: an exit code, if parsing fails (or nothing if parsing succeeds)
        """

        files_retrieved = self.retrieved.list_object_names()
        with self.retrieved.open("fort.10_new", 'rb') as handle:
            output_10 = SinglefileData(file=handle)
        self.out('fort10', output_10)

        return ExitCode(0)
