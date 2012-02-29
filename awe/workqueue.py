
import awe

import mdtools

import work_queue as WQ

import os, tarfile, tempfile, time, shutil


### A process can only support a single WorkQueue instance
_AWE_WORK_QUEUE = None


### workaround for now.
##+ These are the names of the input/output filess to be materialized on the worker

WORKER_PDB_NAME     = 'structure.pdb'
WORKER_WEIGHTS_NAME = 'weight.dat'
WORKER_COLOR_NAME   = 'color.dat'
WORKER_CELL_NAME    = 'cell.dat'
WORKER_RESULTS_NAME = 'results.tar'

RESULT_POSITIONS    = 'structure2.pdb'
RESULT_WEIGHTS      = 'weight.dat'
RESULT_COLOR        = 'color.dat'
RESULT_CELL         = 'cell2.dat'
RESULT_NAME         = 'results-%s.tar'


class WorkQueueException       (Exception): pass
class WorkQueueWorkerException (Exception): pass

class WQFile(object):

    @awe.typecheck(str, base=bool, cached=bool)
    def __init__(self, masterpath, base=True, cached=True):
        self._masterpath = masterpath
        self._base       = base
        self._cached     = cached

    @property
    def masterpath(self):
        return self._masterpath

    @property
    def remotepath(self):
        if self.isbase:
            return os.path.basename(self.masterpath)
        else:
            return self.masterpath

    @property
    def isbase(self):
        return self._base

    @property
    def cached(self):
        return self._cached

    def add_to_task(self, task):
        task.specify_file(self.masterpath, remote_name=self.remotepath, cache=self.cached)

    def __str__(self):
        return 'WQFile: masterpath=%s remotepath=%s cached=%s' % (self.masterpath, self.remotepath, self.cached)

    def __repr__(self):
        return 'WQFile(%r, base=%r, cached=%r' % (self._masterpath, self._base, self._cached)



class Config(object):
    """
    Class for configuring a WorkQueue instance
    """

    def __init__(self):

        self.name      = 'awe'
        self.port      = WQ.WORK_QUEUE_RANDOM_PORT
        self.schedule  = WQ.WORK_QUEUE_SCHEDULE_TIME
        self.exclusive = True
        self.catalog   = True
        self.debug     = ''
        self.shutdown  = False
        self.fastabort = 3
        self.restarts  = 3

        self.waittime  = 10 # in seconds


        self._executable = None
        self._cache = set()

    executable = property(lambda self: self._executable)
    getcache   = property(lambda self: self._cache)

    def execute(self, path):
        f = WQFile(path)
        self._executable = f
        self.cache(f.masterpath)

    def cache(self, *files, **kws):
        base = kws.get('base', True)
        for path in files:
            wqf = WQFile(path, base=base, cached=True)
            self._cache.add(wqf)

    def _mk_wq(self):
        global _AWE_WORK_QUEUE
        if _AWE_WORK_QUEUE is not None:
            ### warn
            awe.log('WARNING: using previously created WorkQueue instance')
            return _AWE_WORK_QUEUE
        else:
            WQ.set_debug_flag(self.debug)
            wq = WQ.WorkQueue(name      = self.name,
                              port      = self.port,
                              shutdown  = self.shutdown,
                              catalog   = self.catalog,
                              exclusive = self.exclusive)
            wq.specify_algorithm(self.schedule)

            typ = type(self.fastabort)
            if typ is float or typ is int:
                wq.activate_fast_abort(self.fastabort)

            _AWE_WORK_QUEUE = wq

            return wq


class WorkQueue(object):

    @awe.typecheck(Config)
    def __init__(self, cfg):

        self.cfg    = cfg
        self.wq     = self.cfg._mk_wq()

        self.stats  = awe.stats.WQStats()

        self.tmpdir = tempfile.mkdtemp(prefix='awe-tmp.')

        self.restarts = dict()


    empty = property(lambda self: self.wq.empty())

    def save_stats(self, dirname):
        if not os.path.exists(dirname):
            print 'Creating directory', dirname
            os.makedirs(dirname)

        wqstats   = os.path.join(dirname, 'wqstats.npy')
        taskstats = os.path.join(dirname, 'taskstats.npy')
        self.stats.save(wqstats, taskstats)

    def __del__(self):
        import shutil
        shutil.rmtree(self.tmpdir)


    def update_wq_stats(self):
        self.stats.wq(self.wq)

    @awe.typecheck(WQ.Task)
    def update_task_stats(self, task):
        self.stats.task(task)

    @awe.typecheck(dict)
    def new_task(self, params):
        cmd = self.cfg.executable.remotepath
        task = WQ.Task('./' + cmd)

        ### executable
        self.cfg.executable.add_to_task(task)

        ### cached files
        for wqf in self.cfg.getcache:
            wqf.add_to_task(task)

        ### convert the walker parameters for WQWorker
        task.specify_buffer(params['weight'] , WORKER_WEIGHTS_NAME , cache=False)
        task.specify_buffer(params['color']  , WORKER_COLOR_NAME   , cache=False)
        task.specify_buffer(params['cell']   , WORKER_CELL_NAME    , cache=False)
        task.specify_buffer(params['pdb']    , WORKER_PDB_NAME     , cache=False)
        task.specify_tag   (params['id'])

        ### result file:
        result = os.path.join(self.tmpdir, RESULT_NAME % task.tag)
        task.specify_output_file(result, remote_name = WORKER_RESULTS_NAME, cache=False)


        return task

    @awe.typecheck(WQ.Task)
    def submit(self, task):
        return self.wq.submit(task)

    @awe.typecheck(WQ.Task)
    def restart(self, task):
        if task.tag not in self.restarts:
            self.restarts[task.tag] = 0

        if self.restarts[task.tag] < self.cfg.restarts:
            print time.asctime(), 'restarting', task.tag
            self.submit(task)
            self.restarts[task.tag] += 1
            return True
        else:
            return False

    def wait(self, *args, **kws):
        return self.wq.wait(*args, **kws)

    @awe.typecheck(WQ.Task)
    def _load_result_file(self, task):

        path = os.path.join(self.tmpdir, RESULT_NAME % task.tag)
        with tarfile.open(path) as tar:

            pdbstring    = tar.extractfile(RESULT_POSITIONS ).read()
            weightstring = tar.extractfile(RESULT_WEIGHTS   ).read()
            colorstring  = tar.extractfile(RESULT_COLOR     ).read()
            cellstring   = tar.extractfile(RESULT_CELL      ).read()

            ss           = awe.io.StringStream(pdbstring)
            pdb          = mdtools.prody.parsePDBStream(ss)

            walker       = awe.aweclasses.Walker(
                end      = pdb.getCoords(),
                weight   = float(weightstring),
                color    = int(colorstring),
                cell     = int(cellstring),
                wid      = int(task.tag)
                )

        os.unlink(path)
        return walker


    def recv(self):

        # print time.asctime(), 'waiting for task'
        while True:

            task = self.wait(self.cfg.waittime)
            self.update_wq_stats()

            if task:

                # print time.asctime(), 'recived task', task.tag

                output = task.output or ''
                output = ('\n' + output).split('\n')
                output = '\n\t'.join(output)

                if not task.return_status == 0 and not self.restart(task):
                    raise WorkQueueWorkerException, \
                        output + '\n\nTask %s failed with %d' % (task.tag, task.return_status)

                self.update_task_stats(task)

                try:
                    walker = self._load_result_file(task)
                except Exception, ex:

                    ### sometimes a task fails, but still returns.
                    ##+ attempt to restart these
                    if not self.restart(task):
                        raise WorkQueueException, \
                            output + '\n\nMaster failed: could not load resultfile:\n %s' % ex
                    else:
                        continue

                return walker
