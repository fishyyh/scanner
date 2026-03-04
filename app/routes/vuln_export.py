# coding: utf-8

import csv
import io
import time
from flask import make_response
from flask_restx import Resource, Namespace, fields, reqparse
from urllib.parse import quote
from app.utils import get_logger, auth, conn_db

ns = Namespace('vuln_export', description="漏洞报告导出接口")

logger = get_logger()


@ns.route('/csv/')
class VulnExportCSV(Resource):
    parser = reqparse.RequestParser(bundle_errors=True)
    parser.add_argument('task_id', type=str, help="任务ID（可选，不传则导出全部）", location='args')
    parser.add_argument('vuln_severity', type=str, help="漏洞等级筛选 (critical/high/medium/low)", location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        导出漏洞报告为 CSV 格式
        """
        args = self.parser.parse_args()
        query = {}
        if args.get('task_id'):
            query['task_id'] = args['task_id']
        if args.get('vuln_severity'):
            query['vuln_severity'] = args['vuln_severity']

        # 查询 nuclei 扫描结果
        nuclei_items = list(conn_db('nuclei_result').find(query).sort('_id', -1))

        # 查询 PoC 漏洞结果
        vuln_items = list(conn_db('vuln').find(query).sort('_id', -1))

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入 nuclei 结果
        writer.writerow([
            '来源', '漏洞名称', '漏洞等级', '漏洞URL', '目标',
            '模版ID', '模版URL', 'curl命令', '任务ID', '发现时间'
        ])

        for item in nuclei_items:
            writer.writerow([
                'nuclei',
                item.get('vuln_name', ''),
                item.get('vuln_severity', ''),
                item.get('vuln_url', ''),
                item.get('target', ''),
                item.get('template_id', ''),
                item.get('template_url', ''),
                item.get('curl_command', ''),
                item.get('task_id', ''),
                item.get('save_date', ''),
            ])

        for item in vuln_items:
            writer.writerow([
                'poc',
                item.get('vul_name', '') or item.get('plg_name', ''),
                item.get('plg_type', ''),
                item.get('target', ''),
                item.get('target', ''),
                item.get('app_name', ''),
                '',
                '',
                item.get('task_id', ''),
                item.get('save_date', ''),
            ])

        csv_data = output.getvalue()
        output.close()

        # 添加 UTF-8 BOM 以便 Excel 正确识别中文
        csv_bytes = b'\xef\xbb\xbf' + csv_data.encode('utf-8')

        filename = "漏洞报告_{}.csv".format(int(time.time()))
        response = make_response(csv_bytes)
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
        response.headers["Content-Disposition"] = "attachment; filename={}".format(quote(filename))

        return response
