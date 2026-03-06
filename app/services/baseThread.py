import threading
import collections
import time
import requests.exceptions
from lxml import etree
from app import utils
from app.modules import DomainInfo
logger = utils.get_logger()


class BaseThread(object):
    def __init__(self, targets, concurrency=6):
        self.concurrency = concurrency
        self.semaphore = threading.Semaphore(concurrency)
        self.targets = targets

    def work(self, site):
        raise NotImplementedError()

    def _work(self, url):
        try:
            self.work(url)
        except requests.exceptions.RequestException as e:
            logger.warning("request error on {}: {}".format(url, e))

        except etree.Error as e:
            logger.debug("etree error on {}: {}".format(url, e))

        except Exception as e:
            logger.warning("error on {}".format(url))
            logger.exception(e)

        except BaseException as e:
            logger.warning("BaseException on {}".format(url))
            raise e
        finally:
            self.semaphore.release()

    def _run(self):
        deque = collections.deque()
        cnt = 0

        for target in self.targets:
            if isinstance(target, str):
                target = target.strip()

            if not target:
                continue

            cnt += 1
            logger.debug("[{}/{}] work on {}".format(cnt, len(self.targets), target))

            self.semaphore.acquire()
            t1 = threading.Thread(target=self._work, args=(target,))
            t1.daemon = True
            t1.start()
            deque.append(t1)

        # 等待所有线程完成
        for t in deque:
            t.join(timeout=120)
            if t.is_alive():
                logger.warning("thread still alive after 120s")


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
