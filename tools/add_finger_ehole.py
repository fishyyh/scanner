import json
import os
import sys
import requests
import yaml
requests.packages.urllib3.disable_warnings()

def update_data(name,rule,token):
	payload = {
		"name": name,
		"human_rule": rule
	}
	headers = {
		"Content-Type": "application/json; charset=UTF-8",
		"Token": token,
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.160 Safari/537.36"
	}
	response = requests.post("https://127.0.0.1:5003/api/fingerprint/", json=payload, headers=headers,timeout=20, verify=False)
	if response.status_code==200:
		print(f"[+] 指纹:'{name}'\t规则:{rule}")
	else:
		print(f"[-] 指纹:'{name}'\t上传失败")

def get_admin_password():
	"""从环境变量或配置文件读取 admin 密码"""
	password = os.environ.get("ARL_ADMIN_PASSWORD")
	if password:
		return password

	config_paths = ["app/config.yaml", "/opt/ARL/app/config.yaml"]
	for path in config_paths:
		if os.path.isfile(path):
			try:
				with open(path) as f:
					y = yaml.safe_load(f)
				pwd = y.get("ARL", {}).get("ADMIN_PASSWORD")
				if pwd:
					return pwd
			except Exception:
				pass

	print("[-] 请设置环境变量 ARL_ADMIN_PASSWORD 或在 config.yaml 中配置 ARL.ADMIN_PASSWORD")
	sys.exit(1)

def do_login():
	password = get_admin_password()
	burp0_url = "https://127.0.0.1:5003/api/user/login"
	burp0_headers = {"Accept": "application/json, text/plain, */*", "Content-Type": "application/json; charset=UTF-8", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.160 Safari/537.36"}
	burp0_json={"password": password, "username": "admin"}
	res = requests.post(burp0_url, headers=burp0_headers, json=burp0_json,timeout=20, verify=False)
	if res.json()['code']==200:
		print("[+] login Success! ")
		token = res.json()['data']['token']
		get_rule(token)
	elif res.json()['code']==401:
		print("[-] login Failure! ")
	else:
		print("[-] login Error! ")
def get_rule(token):
	files = ['tools/finger.json','tools/finger2.json']
	for filename in files:
		file = open(filename, 'r',encoding='utf-8')
		data = json.load(file)
		for i in data['fingerprint']:
			for keyword in i['keyword']:
				if i['method']=='faviconhash'or i['method']=='icon_hash':
					name = i['cms']
					rule = 'icon_hash="'+keyword+'"'
				elif i['method']=='keyword':
					if i['location']=='title':
						name = i['cms']
						rule = 'title="'+keyword+'"'
					elif i['location']=='header':
						name = i['cms']
						rule = 'header="'+keyword+'"'
					elif i['location']=='body':
						name = i['cms']
						rule = 'body="'+keyword+'"'
				else:
					pass
				update_data(name,rule,token)
do_login()
