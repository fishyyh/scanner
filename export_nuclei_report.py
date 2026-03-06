#!/usr/bin/env python3
# coding: utf-8
"""
Nuclei 报告导出脚本
用法:
    python export_nuclei_report.py <task_id>
    python export_nuclei_report.py <task_id> --severity high
    python export_nuclei_report.py <task_id> --mongo mongodb://127.0.0.1:27017/ --db ARLV2
    python export_nuclei_report.py <task_id> --csv          # 导出 CSV
    python export_nuclei_report.py <task_id> -o report.html # 自定义输出文件名
"""

import argparse
import csv
import os
import sys

try:
    from pymongo import MongoClient
except ImportError:
    print("错误: 缺少 pymongo，请执行 pip install pymongo")
    sys.exit(1)

SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info']
SEVERITY_STYLE = {
    'critical': ('color:white;background:#f5222d;border-color:#f5222d', '#f5222d'),
    'high':     ('color:white;background:#fa8c16;border-color:#fa8c16', '#fa8c16'),
    'medium':   ('color:#333;background:#fadb14;border-color:#d4b106', '#d4b106'),
    'low':      ('color:white;background:#52c41a;border-color:#52c41a', '#52c41a'),
    'info':     ('color:white;background:#1890ff;border-color:#1890ff', '#1890ff'),
}


def _escape(s):
    if not s:
        return ''
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def _severity_badge(severity):
    s = (severity or 'info').lower()
    _, color = SEVERITY_STYLE.get(s, ('', '#666'))
    bg = SEVERITY_STYLE.get(s, ('', '#666'))[1]
    text_color = '#333' if s == 'medium' else 'white'
    styles = (f'padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;'
              f'display:inline-block;background:{bg};color:{text_color};border:1px solid {color}')
    return f'<span style="{styles}">{_escape(severity)}</span>'


def get_mongo_url():
    """从 config.yaml 读取 MongoDB 连接信息，失败时返回默认值"""
    config_path = os.path.join(os.path.dirname(__file__), 'app', 'config.yaml')
    try:
        import yaml
        with open(config_path) as f:
            y = yaml.safe_load(f)
        return y['MONGO']['URI'], y['MONGO']['DB']
    except Exception:
        return 'mongodb://127.0.0.1:27017/', 'ARLV2'


def export_html(results, task_id, sev_counts, total_all, severity_filter, output_file):
    rows_html = ''
    for item in results:
        curl = _escape(item.get('curl_command', ''))
        vuln_url = _escape(item.get('vuln_url', ''))
        rows_html += (
            f'<tr>'
            f'<td>{_escape(item.get("template_id", ""))}</td>'
            f'<td>{_escape(item.get("vuln_name", ""))}</td>'
            f'<td>{_severity_badge(item.get("vuln_severity", ""))}</td>'
            f'<td><a href="{vuln_url}" target="_blank" style="word-break:break-all">{vuln_url}</a></td>'
            f'<td style="word-break:break-all">{_escape(item.get("target", ""))}</td>'
            f'<td><code style="font-size:11px;background:#f5f5f5;padding:2px 5px;border-radius:3px;'
            f'word-break:break-all;display:block;max-width:320px">{curl}</code></td>'
            f'<td style="white-space:nowrap">{_escape(item.get("save_date", ""))}</td>'
            f'</tr>'
        )

    if not rows_html:
        rows_html = ('<tr><td colspan="7" style="text-align:center;padding:48px;color:#aaa;font-size:15px">'
                     '暂无数据</td></tr>')

    filter_btns = f'<span class="fbtn" style="color:white;background:#1890ff;border-color:#1890ff">全部({total_all})</span>'
    for sv in SEVERITY_ORDER:
        cnt = sev_counts.get(sv, 0)
        _, color = SEVERITY_STYLE.get(sv, ('', '#888'))
        filter_btns += (
            f'<span class="fbtn" style="color:{color};border-color:{color}">'
            f'{sv.upper()}({cnt})</span>'
        )

    sev_label = f' [{severity_filter.upper()}]' if severity_filter else ''
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Nuclei 扫描报告 - {task_id}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,Helvetica,sans-serif;background:#f0f2f5;padding:20px;color:#333;font-size:14px}}
.header{{background:linear-gradient(135deg,#1e2a3a,#2d4060);color:white;padding:22px 24px;border-radius:8px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,.18)}}
.header h1{{font-size:20px;font-weight:600;letter-spacing:.5px}}
.header p{{margin-top:6px;color:#a8c4e0;font-size:13px}}
.toolbar{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;align-items:center}}
.fbtn{{padding:4px 14px;border:1px solid #ddd;background:white;border-radius:20px;font-size:13px;color:#555}}
.card{{background:white;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden}}
table{{width:100%;border-collapse:collapse}}
th{{background:#fafafa;padding:12px 10px;text-align:left;font-weight:600;border-bottom:2px solid #f0f0f0;font-size:13px;white-space:nowrap}}
td{{padding:10px;border-bottom:1px solid #f5f5f5;font-size:13px;vertical-align:top}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:#f9fffe}}
a{{color:#1890ff}}
@media print{{
  .toolbar{{display:none}}
  body{{background:white;padding:0}}
  .header{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
  .card{{box-shadow:none}}
}}
</style>
</head>
<body>
<div class="header">
  <h1>Nuclei 扫描报告{sev_label}</h1>
  <p>任务 ID: {task_id} &nbsp;|&nbsp; 共 {total_all} 条记录</p>
</div>
<div class="toolbar">{filter_btns}</div>
<div class="card">
<table>
<thead>
<tr>
  <th>模版 ID</th><th>漏洞名称</th><th>等级</th><th>漏洞 URL</th><th>目标</th><th>curl 命令</th><th>发现时间</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>
</body>
</html>'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"HTML 报告已保存: {output_file}  ({len(results)} 条)")


def export_csv(results, output_file):
    fields = ['template_id', 'vuln_name', 'vuln_severity', 'vuln_url', 'target', 'curl_command', 'save_date']
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for item in results:
            writer.writerow({k: item.get(k, '') for k in fields})
    print(f"CSV 已保存: {output_file}  ({len(results)} 条)")


def main():
    parser = argparse.ArgumentParser(description='导出 Nuclei 扫描报告')
    parser.add_argument('task_id', help='任务 ID')
    parser.add_argument('--severity', default='', help='按等级过滤: critical/high/medium/low/info')
    parser.add_argument('--mongo', default='', help='MongoDB URI，默认读取 config.yaml')
    parser.add_argument('--db', default='', help='MongoDB 数据库名，默认读取 config.yaml')
    parser.add_argument('-o', '--output', default='', help='输出文件名（默认自动生成）')
    parser.add_argument('--csv', action='store_true', help='导出 CSV 格式')
    args = parser.parse_args()

    default_uri, default_db = get_mongo_url()
    mongo_uri = args.mongo or default_uri
    mongo_db  = args.db   or default_db

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.server_info()
        col = client[mongo_db]['nuclei_result']
    except Exception as e:
        print(f"MongoDB 连接失败: {e}")
        sys.exit(1)

    task_id = args.task_id
    severity_filter = args.severity.strip().lower()

    query = {'task_id': task_id}
    if severity_filter:
        query['vuln_severity'] = severity_filter

    results = list(col.find(query).sort('_id', -1))
    total_all = col.count_documents({'task_id': task_id})

    if total_all == 0:
        print(f"任务 {task_id} 没有 nuclei 结果，请确认 task_id 是否正确")
        sys.exit(0)

    # severity 统计
    pipeline = [
        {'$match': {'task_id': task_id}},
        {'$group': {'_id': '$vuln_severity', 'count': {'$sum': 1}}}
    ]
    sev_counts = {doc['_id']: doc['count'] for doc in col.aggregate(pipeline)}

    # 确定输出文件名
    sev_suffix = f'_{severity_filter}' if severity_filter else ''
    if args.csv:
        out = args.output or f'nuclei_{task_id}{sev_suffix}.csv'
        export_csv(results, out)
    else:
        out = args.output or f'nuclei_{task_id}{sev_suffix}.html'
        export_html(results, task_id, sev_counts, total_all, severity_filter, out)


if __name__ == '__main__':
    main()
