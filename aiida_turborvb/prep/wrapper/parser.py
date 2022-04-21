from aiida.engine import ExitCode
from aiida.parsers.parser import Parser
from aiida.plugins import CalculationFactory
from aiida.common import exceptions
from aiida.orm import Float, SinglefileData, List
import numpy as np

class TurboRVBPrepParserWRP(Parser):
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
        output_filename = "prep.output" #self.node.get_option('output_filename')

        files_retrieved = self.retrieved.list_object_names()
        with self.retrieved.open("fort.10_new", 'rb') as handle:
            output_10 = SinglefileData(file=handle)
        with self.retrieved.open("occupationlevels.dat", 'rb') as handle:
            occfile = SinglefileData(file=handle)

        energy = 0.0
        convergance = []
        with self.retrieved.open(output_filename, 'r') as handle:
            for line in handle:
                if "Iter" in line:
                    try:
                        convergance.append(float(line.split()[5]))
                    except IndexError:
                        pass
                if "inal self c" in line:
                    energy = line.split()[6]

        energy = Float(energy)
        convergance = List(list=convergance)

        self.out('fort10', output_10)
        self.out('occfile', occfile)
        self.out('energy', energy)
        self.out('convergance', convergance)

        return ExitCode(0)
