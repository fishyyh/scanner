import time
import threading
from app import utils
from .baseThread import BaseThread
logger = utils.get_logger()

SKIP_STATUS = {502, 504, 501, 422, 410}


class ProbeHTTP(BaseThread):
    def __init__(self, domains, concurrency=6):
        super().__init__(self._build_targets(domains), concurrency=concurrency)

        self.sites = []
        self._lock = threading.Lock()
        self.domains = domains
        self._fail_count = 0

    def _build_targets(self, domains):
        _targets = []
        for item in domains:
            domain = item
            if hasattr(item, 'domain'):
                domain = item.domain

            _targets.append("https://{}".format(domain))
            _targets.append("http://{}".format(domain))

        return _targets

    def work(self, target):
        # 带重试的探活，第二次加长超时
        conn = None
        for attempt, timeout in enumerate([(5, 10), (8, 15)]):
            try:
                conn = utils.http_req(target, 'get', timeout=timeout, no_content=True)
                break
            except Exception as e:
                if attempt == 0:
                    time.sleep(0.3)
                else:
                    with self._lock:
                        self._fail_count += 1
                    logger.debug("probe failed on {}: {}".format(target, e))
                    return

        if conn is None:
            return

        try:
            conn.close()
        except Exception:
            pass

        if conn.status_code in SKIP_STATUS:
            return

        with self._lock:
            self.sites.append(target)

    def run(self):
        t1 = time.time()
        logger.info("start ProbeHTTP targets:{}".format(len(self.targets)))
        self._run()

        # 去除 https 和 http 相同的
        sites_set = set(self.sites)
        alive_site = []
        for x in self.sites:
            if x.startswith("https://"):
                alive_site.append(x)
            elif x.startswith("http://"):
                x_temp = "https://" + x[7:]
                if x_temp not in sites_set:
                    alive_site.append(x)

        elapse = time.time() - t1
        logger.info("end ProbeHTTP alive:{} failed:{} elapse:{:.1f}s".format(
            len(alive_site), self._fail_count, elapse))

        return alive_site


def probe_http(domain, concurrency=15):
    p = ProbeHTTP(domain, concurrency=concurrency)
    return p.run()
