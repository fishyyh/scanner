import json
import os.path
import subprocess

from app.config import Config
from app import utils


logger = utils.get_logger()


class NucleiScan(object):
    def __init__(self, targets: list):
        self.targets = targets

        tmp_path = Config.TMP_PATH
        rand_str = utils.random_choices()

        self.nuclei_target_path = os.path.join(tmp_path,
                                               "nuclei_target_{}.txt".format(rand_str))

        self.nuclei_result_path = os.path.join(tmp_path,
                                               "nuclei_result_{}.json".format(rand_str))

        self.nuclei_bin_path = "nuclei"

        # 在nuclei 2.9.1 中 将-json 参数改成了 -jsonl 参数。
        self.nuclei_json_flag = None

        # 根据目标数量动态调整并发和速率
        target_count = len(targets)
        max_concurrency = getattr(Config, 'NUCLEI_MAX_CONCURRENCY', 300)
        max_rate = getattr(Config, 'NUCLEI_MAX_RATE', 1000)
        self.concurrency = min(max(target_count * 5, 50), max_concurrency)
        self.rate_limit = min(max(target_count * 10, 150), max_rate)
        self.timeout_per_target = 120  # 每个目标120秒

    def _check_json_flag(self):
        json_flag = ["-json", "-jsonl"]
        for x in json_flag:
            command = [self.nuclei_bin_path, "-duc", x, "-version"]
            pro = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if pro.returncode == 0:
                self.nuclei_json_flag = x
                return

        assert self.nuclei_json_flag

    def _delete_file(self):
        try:
            os.unlink(self.nuclei_target_path)
            # 删除结果临时文件
            if os.path.exists(self.nuclei_result_path):
                os.unlink(self.nuclei_result_path)
        except Exception as e:
            logger.warning(e)

    def check_have_nuclei(self) -> bool:
        command = [self.nuclei_bin_path, "-version"]
        try:
            pro = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if pro.returncode == 0:
                return True
        except Exception as e:
            logger.debug("{}".format(str(e)))

        return False

    def _gen_target_file(self):
        with open(self.nuclei_target_path, "w") as f:
            for domain in self.targets:
                domain = domain.strip()
                if not domain:
                    continue
                f.write(domain + "\n")

    def dump_result(self) -> list:
        results = []
        with open(self.nuclei_result_path, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    break

                data = json.loads(line)
                item = {
                    "template_url": data.get("template-url", ""),
                    "template_id": data.get("template-id", ""),
                    "vuln_name": data.get("info", {}).get("name", ""),
                    "vuln_severity": data.get("info", {}).get("severity", ""),
                    "vuln_url": data.get("matched-at", ""),
                    "curl_command": data.get("curl-command", ""),
                    "target": data.get("host", "")
                }
                results.append(item)

        return results

    def exec_nuclei(self):
        self._gen_target_file()

        # 动态计算超时时间：每个目标120秒，最少10分钟，最多24小时
        total_timeout = max(len(self.targets) * self.timeout_per_target, 600)
        total_timeout = min(total_timeout, 24 * 60 * 60)

        command = [self.nuclei_bin_path, "-duc",
                   "-timeout", "8",
                   "-c", str(self.concurrency),
                   "-rl", str(self.rate_limit),
                   "-bs", str(min(self.concurrency, 150)),  # bulk-size 批量请求
                   "-retries", "1",
                   "-s", "critical,high,medium,low",
                   "-etid",  "expired-ssl,self-signed-ssl",
                   "-l", self.nuclei_target_path,
                   self.nuclei_json_flag,  # 在nuclei 2.9.1 中 将 -json 参数改成了 -jsonl 参数
                   "-stats",
                   "-stats-interval", "60",
                   "-o", self.nuclei_result_path,
                   ]

        logger.info("nuclei concurrency:{} rate_limit:{} timeout:{}s targets:{}".format(
            self.concurrency, self.rate_limit, total_timeout, len(self.targets)))
        logger.info(" ".join(command))
        utils.exec_system(command, timeout=total_timeout)

    def run(self):
        if not self.check_have_nuclei():
            logger.warning("not found nuclei")
            return []

        self._check_json_flag()

        self.exec_nuclei()

        results = self.dump_result()

        # 删除临时文件
        self._delete_file()

        return results


def nuclei_scan(targets: list):
    if not targets:
        return []

    n = NucleiScan(targets=targets)
    return n.run()

