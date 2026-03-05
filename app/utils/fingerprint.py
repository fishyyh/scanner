import json
from app.config import Config
from app.utils import get_logger, conn_db, load_file
logger = get_logger()

# 解析规则，只有或，且条件不能出现=

'''
html
title
headers
favicon_hash
'''

# 这个函数已经不用了


def parse_human_rule(rule):
    rule_map = {
        "html": [],
        "title": [],
        "headers": [],
        "favicon_hash": []
    }
    key_map = {
        "body": "html",
        "title": "title",
        "header": "headers",
        "icon_hash": "favicon_hash"
    }
    split_result = rule.split("||")
    empty_flag = True

    for item in split_result:
        key_value = item.split("=")
        key = key_value[0]
        key = key.strip()
        if len(key_value) == 2:
            if key not in key_map:
                logger.info("{} 不在指定关键字中".format(key))
                continue

            value = key_value[1]
            value = value.strip()
            if len(value) <= 6:
                logger.info("{} 长度少于7".format(value))
                continue

            if value[0] != '"' or value[-1] != '"':
                logger.info("{} 没有在双引号内".format(value))
                continue

            empty_flag = False

            # 防御性转换成gbk
            value.encode("gbk")

            value = value[1:-1]
            if key == "icon_hash":
                value = int(value)

            rule_map[key_map[key]].append(value)

    if empty_flag:
        return None

    return rule_map


def transform_rule_map(rule):
    key_map = {
        "html": "body",
        "title": "title",
        "headers": "header",
        "favicon_hash": "icon_hash"
    }
    human_rule_list = []
    for key in rule:
        if key not in key_map:
            logger.info("{} 不在指定关键字中".format(key))
            continue

        for rule_item in rule[key]:
            human_rule_list.append('{}="{}"'.format(key_map[key], rule_item))

    return " || ".join(human_rule_list)


web_app_rules = json.loads("\n".join(load_file(Config.web_app_rule)))


# 这里只是加载本地指纹规则，预编码 html 关键词避免重复计算
def load_fingerprint():
    items = []
    for rule in web_app_rules:
        new_rule = dict()
        new_rule["name"] = rule
        raw_rule = web_app_rules[rule]

        # 预编码 html 关键词为 bytes，避免每次匹配都重复编码
        html_encoded = []
        for html in raw_rule.get("html", []):
            encoded_pair = [html.encode("utf-8")]
            try:
                gbk = html.encode("gbk")
                if gbk != encoded_pair[0]:
                    encoded_pair.append(gbk)
            except Exception:
                pass
            html_encoded.append(encoded_pair)

        new_rule["rule"] = raw_rule
        new_rule["html_encoded"] = html_encoded
        items.append(new_rule)
    return items


# 根据规则列表来获取应用名，单个规则字段是或的关系
def fetch_fingerprint(content, headers, title, favicon_hash, finger_list):
    finger_name_list = []

    for finger in finger_list:
        rule = finger["rule"]
        rule_name = finger["name"]
        match_flag = False

        # 使用预编码的 bytes 直接匹配，跳过重复 encode
        for encoded_pair in finger.get("html_encoded", []):
            for encoded_html in encoded_pair:
                if encoded_html in content:
                    finger_name_list.append(rule_name)
                    match_flag = True
                    break
            if match_flag:
                break

        if match_flag:
            continue
        for header in rule["headers"]:
            if header in headers:
                finger_name_list.append(rule_name)
                match_flag = True
                break

        if match_flag:
            continue
        for rule_title in rule["title"]:
            if rule_title in title:
                finger_name_list.append(rule_name)
                match_flag = True
                break

        if match_flag:
            continue
        if isinstance(rule.get("favicon_hash"), list):
            for rule_hash in rule["favicon_hash"]:
                if rule_hash == favicon_hash:
                    finger_name_list.append(rule_name)
                    break

    return finger_name_list
