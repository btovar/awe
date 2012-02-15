

### workaround for now.
##+ These are the names of the input/output filess to be materialized on the worker

WORKER_PDB_NAME     = 'structure.pdb'
WORKER_WEIGHTS_NAME = 'weights.dat'
WORKER_COLOR_NAME   = 'color.dat'
WORKER_CELL_NAME    = 'cell.dat'
WORKER_RESULTS_NAME = 'results.tar'

RESULT_POSITIONS    = 'structure2.pdb'
RESULT_WEIGHTS      = 'weights2.dat'
RESULT_COLOR        = 'color2.dat'
RESULT_CELL         = 'cell2.dat'


class StringStream(object):

    """
    write strings to a representation in memory
    """

    def __init__(self, s=None):
        """
        Create the stream.
        Parameters:
          s: if *s* is a string, split the string by '\n', if a list, then use it
        """

        self.reset()

        if type(s) is str:
            self._buffer = s.split('\n')
        elif type(s) is list:
            self._buffer = s

    def write(self, s):
        self._read = False
        self._buffer.append(s)

    def reset(self):
        self._buffer = list()
        self._str    = str()
        self._read   = False

    def read(self):
        if not self._read:
            self._str  = ''.join(self._buffer)
            self._read = True

        return self._str

    def readlines(self):
        return self._buffer


def log(string):
    print string