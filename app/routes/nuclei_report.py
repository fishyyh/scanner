# coding: utf-8
from flask import Blueprint, make_response, request
from app.utils import conn_db

nuclei_report_bp = Blueprint('nuclei_report', __name__)

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
    _, color = SEVERITY_STYLE.get(s, ('color:#666;background:#f0f0f0;border-color:#ddd', '#666'))
    styles = (f'padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;'
              f'display:inline-block;background:{SEVERITY_STYLE.get(s, ("","#666"))[1]};'
              f'color:white;border:1px solid {color}')
    if s == 'medium':
        styles = styles.replace('color:white', 'color:#333')
    return f'<span style="{styles}">{_escape(severity)}</span>'


@nuclei_report_bp.route('/nuclei_report/<task_id>')
def nuclei_report(task_id):
    severity_filter = request.args.get('severity', '').strip().lower()

    query = {'task_id': task_id}
    if severity_filter:
        query['vuln_severity'] = severity_filter

    results = list(conn_db('nuclei_result').find(query).sort('_id', -1))
    total_all = conn_db('nuclei_result').count({'task_id': task_id})

    # severity counts
    pipeline = [
        {'$match': {'task_id': task_id}},
        {'$group': {'_id': '$vuln_severity', 'count': {'$sum': 1}}}
    ]
    sev_counts = {
        doc['_id']: doc['count']
        for doc in conn_db('nuclei_result').aggregate(pipeline)
    }

    # build table rows
    rows_html = ''
    for item in results:
        curl = _escape(item.get('curl_command', ''))
        vuln_url = _escape(item.get('vuln_url', ''))
        rows_html += (
            f'<tr>'
            f'<td>{_escape(item.get("template_id",""))}</td>'
            f'<td>{_escape(item.get("vuln_name",""))}</td>'
            f'<td>{_severity_badge(item.get("vuln_severity",""))}</td>'
            f'<td><a href="{vuln_url}" target="_blank" style="word-break:break-all">{vuln_url}</a></td>'
            f'<td style="word-break:break-all">{_escape(item.get("target",""))}</td>'
            f'<td><code style="font-size:11px;background:#f5f5f5;padding:2px 5px;border-radius:3px;'
            f'word-break:break-all;display:block;max-width:320px">{curl}</code></td>'
            f'<td style="white-space:nowrap">{_escape(item.get("save_date",""))}</td>'
            f'</tr>'
        )

    if not rows_html:
        rows_html = ('<tr><td colspan="7" style="text-align:center;padding:48px;color:#aaa;font-size:15px">'
                     '暂无数据</td></tr>')

    # filter buttons
    all_active = 'style="color:white;background:#1890ff;border-color:#1890ff"' if not severity_filter else ''
    filter_btns = f'<a href="/nuclei_report/{task_id}" class="fbtn" {all_active}>全部({total_all})</a>'
    for sv in SEVERITY_ORDER:
        cnt = sev_counts.get(sv, 0)
        active_style, color = SEVERITY_STYLE.get(sv, ('', '#888'))
        btn_style = active_style if severity_filter == sv else f'color:{color};border-color:{color}'
        filter_btns += (
            f'<a href="/nuclei_report/{task_id}?severity={sv}" class="fbtn" '
            f'style="{btn_style}">{sv.upper()}({cnt})</a>'
        )

    csv_url = f'/api/vuln_export/csv/?task_id={task_id}'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Nuclei 扫描报告</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,Helvetica,sans-serif;background:#f0f2f5;padding:20px;color:#333;font-size:14px}}
.header{{background:linear-gradient(135deg,#1e2a3a,#2d4060);color:white;padding:22px 24px;border-radius:8px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,.18)}}
.header h1{{font-size:20px;font-weight:600;letter-spacing:.5px}}
.header p{{margin-top:6px;color:#a8c4e0;font-size:13px}}
.toolbar{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;align-items:center}}
.fbtn{{padding:4px 14px;border:1px solid #ddd;background:white;border-radius:20px;cursor:pointer;
       text-decoration:none;font-size:13px;color:#555;transition:all .15s}}
.fbtn:hover{{opacity:.85;text-decoration:none}}
.actions{{margin-left:auto;display:flex;gap:8px}}
.btn{{padding:6px 16px;border-radius:4px;cursor:pointer;text-decoration:none;font-size:13px;
      border:1px solid #ddd;background:white;color:#333;display:inline-block}}
.btn-primary{{background:#1890ff;color:white;border-color:#1890ff}}
.btn-primary:hover{{background:#40a9ff;text-decoration:none;color:white}}
.card{{background:white;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden}}
table{{width:100%;border-collapse:collapse}}
th{{background:#fafafa;padding:12px 10px;text-align:left;font-weight:600;
    border-bottom:2px solid #f0f0f0;font-size:13px;white-space:nowrap}}
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
  <h1>Nuclei 扫描报告</h1>
  <p>任务 ID: {task_id} &nbsp;|&nbsp; 共 {total_all} 条记录</p>
</div>
<div class="toolbar">
  {filter_btns}
  <div class="actions">
    <a href="{csv_url}" class="btn btn-primary">导出 CSV</a>
    <button class="btn" onclick="window.print()">打印报告</button>
  </div>
</div>
<div class="card">
<table>
<thead>
<tr>
  <th>模版 ID</th>
  <th>漏洞名称</th>
  <th>等级</th>
  <th>漏洞 URL</th>
  <th>目标</th>
  <th>curl 命令</th>
  <th>发现时间</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>
</body>
</html>'''

    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response
