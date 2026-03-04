import requests.exceptions
from concurrent.futures import ThreadPoolExecutor, as_completed
from lxml import etree
from app import utils
from app.modules import DomainInfo
logger = utils.get_logger()


class BaseThread(object):
    def __init__(self, targets, concurrency=6):
        self.concurrency = concurrency
        self.targets = targets

    def work(self, site):
        raise NotImplementedError()

    def _work(self, url):
        try:
            self.work(url)
        except requests.exceptions.RequestException as e:
            pass

        except etree.Error as e:
            pass

        except Exception as e:
            logger.warning("error on {}".format(url))
            logger.exception(e)

        except BaseException as e:
            logger.warning("BaseException on {}".format(url))
            raise e

    def _run(self):
        targets = []
        for target in self.targets:
            if isinstance(target, str):
                target = target.strip()
            if not target:
                continue
            targets.append(target)

        total = len(targets)
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = {}
            for cnt, target in enumerate(targets, 1):
                logger.debug("[{}/{}] work on {}".format(cnt, total, target))
                future = executor.submit(self._work, target)
                futures[future] = target

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.warning("thread error: {}".format(e))


class ThreadMap(BaseThread):
    def __init__(self, fun, items, arg=None, concurrency=6):
        super(ThreadMap, self).__init__(targets=items, concurrency=concurrency)
        if not callable(fun):
            raise TypeError("fun must be callable.")

        self._arg = arg
        self._fun = fun
        self._result_map = {}

    def work(self, item):
        if self._arg:
            result = self._fun(item, self._arg)
        else:
            result = self._fun(item)

        if result:
            self._result_map[str(item)] = result

    def run(self):
        self._run()
        return self._result_map


def thread_map(fun, items, arg=None, concurrency=6):
    t = ThreadMap(fun=fun, items=items, arg=arg, concurrency=concurrency)
    return t.run()
