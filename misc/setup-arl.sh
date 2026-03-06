set -e

cd /etc/yum.repos.d/
sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-*
sed -i 's|baseurl=http://.*centos.org|baseurl=https://mirrors.adysec.com/system/centos|g' /etc/yum.repos.d/CentOS-*
sed -i 's|#baseurl=https://mirrors.adysec.com/system/centos|baseurl=https://mirrors.adysec.com/system/centos|g' /etc/yum.repos.d/CentOS-*

echo "cd /opt/"

mkdir -p /opt/
cd /opt/

tee /etc/resolv.conf <<"EOF"
nameserver 180.76.76.76
nameserver 4.2.2.1
nameserver 1.1.1.1
EOF


tee /etc/yum.repos.d/mongodb-org-4.0.repo <<"EOF"
[mongodb-org-4.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/$releasever/mongodb-org/4.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-4.0.asc
EOF

tee //etc/yum.repos.d/rabbitmq.repo <<"EOF"
[rabbitmq_erlang]
name=rabbitmq_erlang
baseurl=https://packagecloud.io/rabbitmq/erlang/el/8/$basearch
repo_gpgcheck=1
gpgcheck=1
enabled=1
# PackageCloud's repository key and RabbitMQ package signing key
gpgkey=https://packagecloud.io/rabbitmq/erlang/gpgkey
       https://github.com/rabbitmq/signing-keys/releases/download/2.0/rabbitmq-release-signing-key.asc
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300

[rabbitmq_erlang-source]
name=rabbitmq_erlang-source
baseurl=https://packagecloud.io/rabbitmq/erlang/el/8/SRPMS
repo_gpgcheck=1
gpgcheck=0
enabled=1
gpgkey=https://packagecloud.io/rabbitmq/erlang/gpgkey
       https://github.com/rabbitmq/signing-keys/releases/download/2.0/rabbitmq-release-signing-key.asc
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300

[rabbitmq_server]
name=rabbitmq_server
baseurl=https://packagecloud.io/rabbitmq/rabbitmq-server/el/8/$basearch
repo_gpgcheck=1
gpgcheck=0
enabled=1
gpgkey=https://packagecloud.io/rabbitmq/rabbitmq-server/gpgkey
       https://github.com/rabbitmq/signing-keys/releases/download/2.0/rabbitmq-release-signing-key.asc
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300

[rabbitmq_server-source]
name=rabbitmq_server-source
baseurl=https://packagecloud.io/rabbitmq/rabbitmq-server/el/8/SRPMS
repo_gpgcheck=1
gpgcheck=0
enabled=1
gpgkey=https://packagecloud.io/rabbitmq/rabbitmq-server/gpgkey
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300
EOF

echo "install dependencies ..."
cd /opt/
yum update -y

# sync system time by installing and starting chrony
# Ensures system clock is accurate before proceeding
if ! command -v chronyd &> /dev/null; then
    yum install -y chrony
fi
systemctl enable chronyd
systemctl restart chronyd
# make an initial time step
chronyc makestep || ntpdate -u pool.ntp.org || true

# set timezone to Asia/Shanghai (UTC+8)
if [ -f /usr/share/zoneinfo/Asia/Shanghai ]; then
    timedatectl set-timezone Asia/Shanghai
fi

yum install epel-release -y
yum install systemd -y
yum install rabbitmq-server --nobest -y
yum install python36 mongodb-org-server mongodb-org-shell python36-devel gcc-c++ git nginx fontconfig wqy-microhei-fonts unzip wget -y

if [ ! -f /usr/bin/python3.6 ]; then
  echo "link python3.6"
  ln -s /usr/bin/python36 /usr/bin/python3.6
fi

if [ ! -f /usr/local/bin/pip3.6 ]; then
  echo "install  pip3.6"
  python3.6 -m ensurepip --default-pip
  python3.6 -m pip install --upgrade pip
  pip3.6 config --global set global.index-url https://pypi.org/simple
  pip3.6 --version
fi

if ! command -v nmap &> /dev/null
then
    echo "install nmap ..."
    yum install nmap -y
fi


if ! command -v nuclei &> /dev/null
then
  echo "install nuclei"
  wget -c https://github.com/adysec/ARL/raw/master/tools/nuclei.zip -O nuclei.zip
  unzip nuclei.zip && mv nuclei /usr/bin/ && rm -f nuclei.zip
  nuclei -ut
fi

if ! command -v wih &> /dev/null
then
  echo "install wih ..."
  ## 安装 WIH
  wget -c https://github.com/adysec/ARL/raw/master/tools/wih/wih_linux_amd64 -O /usr/bin/wih && chmod +x /usr/bin/wih
  wih --version
fi


echo "start services ..."
systemctl enable mongod
systemctl restart mongod
systemctl enable rabbitmq-server
systemctl restart rabbitmq-server

cd /opt
if [ ! -d ARL ]; then
  echo "git clone ARL proj"
  git clone https://github.com/adysec/ARL
fi

if [ ! -d "ARL-NPoC" ]; then
  echo "mv ARL-NPoC proj"
 mv ARL/tools/ARL-NPoC ARL-NPoC
fi

cd /opt/ARL-NPoC
echo "install poc requirements ..."
pip3.6 install -r requirements.txt
pip3.6 install -e .
cd ../

if [ ! -f /usr/local/bin/ncrack ]; then
  echo "Download ncrack ..."
  wget -c https://github.com/adysec/ARL/raw/master/tools/ncrack -O /usr/local/bin/ncrack
  chmod +x /usr/local/bin/ncrack
fi

mkdir -p /usr/local/share/ncrack
if [ ! -f /usr/local/share/ncrack/ncrack-services ]; then
  echo "Download ncrack-services ..."
  wget -c https://github.com/adysec/ARL/raw/master/tools/ncrack-services -O /usr/local/share/ncrack/ncrack-services
fi

mkdir -p /data/GeoLite2
if [ ! -f /data/GeoLite2/GeoLite2-ASN.mmdb ]; then
  echo "download GeoLite2-ASN.mmdb ..."
  wget -c https://github.com/adysec/ARL/raw/master/tools/GeoLite2-ASN.mmdb -O /data/GeoLite2/GeoLite2-ASN.mmdb
fi

if [ ! -f /data/GeoLite2/GeoLite2-City.mmdb ]; then
  echo "download GeoLite2-City.mmdb ..."
  wget -c https://github.com/adysec/ARL/raw/master/tools/GeoLite2-City.mmdb -O /data/GeoLite2/GeoLite2-City.mmdb
fi

cd /opt/ARL

##########################################################
# 生成随机密码（部署时一次性生成，保存到密码文件中）
##########################################################
ARL_CREDENTIALS_FILE="/opt/ARL/.arl_credentials"

gen_random_password() {
  # 生成20位随机字母数字密码
  cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1
}

if [ -f app/config.yaml ]; then
  echo "=== config.yaml 已存在，保留所有现有密钥 ==="
  if [ -f "$ARL_CREDENTIALS_FILE" ]; then
    source "$ARL_CREDENTIALS_FILE"
  fi
else
  if [ ! -f "$ARL_CREDENTIALS_FILE" ]; then
    echo "=== 首次部署，生成随机密码 ==="

    ARL_MQ_PASSWORD=$(gen_random_password)
    ARL_ADMIN_PASSWORD=$(gen_random_password)
    ARL_PASSWORD_SALT=$(gen_random_password)
    ARL_API_KEY=$(gen_random_password)

    # 保存到凭证文件（仅 root 可读）
    cat > "$ARL_CREDENTIALS_FILE" <<CRED_EOF
# ARL 自动生成的凭证，请妥善保管
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')
ARL_MQ_PASSWORD=${ARL_MQ_PASSWORD}
ARL_ADMIN_PASSWORD=${ARL_ADMIN_PASSWORD}
ARL_PASSWORD_SALT=${ARL_PASSWORD_SALT}
ARL_API_KEY=${ARL_API_KEY}
CRED_EOF
    chmod 600 "$ARL_CREDENTIALS_FILE"
    echo "凭证已保存到 $ARL_CREDENTIALS_FILE"
  else
    echo "=== 读取已有凭证 ==="
  fi

  # 加载凭证
  source "$ARL_CREDENTIALS_FILE"
fi

##########################################################
# 配置 RabbitMQ 和 MongoDB 用户
##########################################################
if [ ! -f rabbitmq_user ]; then
  echo "add rabbitmq user"
  rabbitmqctl add_user arl "$ARL_MQ_PASSWORD"
  rabbitmqctl add_vhost arlv2host
  rabbitmqctl set_user_tags arl arltag
  rabbitmqctl set_permissions -p arlv2host arl ".*" ".*" ".*"

  echo "init arl admin user"
  # 动态替换 mongo-init.js 中的占位符
  sed -e "s|ARL_PASSWORD_SALT_PLACEHOLDER|${ARL_PASSWORD_SALT}|g" \
      -e "s|ARL_ADMIN_PASS_PLACEHOLDER|${ARL_ADMIN_PASSWORD}|g" \
      docker/mongo-init.js > /tmp/arl_mongo_init.js
  mongo 127.0.0.1:27017/arl /tmp/arl_mongo_init.js
  rm -f /tmp/arl_mongo_init.js

  touch rabbitmq_user
fi

##########################################################
# 生成配置文件（注入密码）
##########################################################
echo "install arl requirements ..."
pip3.6 install -r requirements.txt

if [ ! -f app/config.yaml ]; then
  echo "create config.yaml with generated credentials"
  cp app/config.yaml.example app/config.yaml

  # 替换配置文件中的占位符
  sed -i "s|BROKER_URL : \"amqp://arl:CHANGE_ME@|BROKER_URL : \"amqp://arl:${ARL_MQ_PASSWORD}@|g" app/config.yaml
  sed -i "s|PASSWORD_SALT: \"CHANGE_ME\"|PASSWORD_SALT: \"${ARL_PASSWORD_SALT}\"|g" app/config.yaml
  sed -i "s|API_KEY: \"\"|API_KEY: \"${ARL_API_KEY}\"|g" app/config.yaml
fi

if [ ! -f /usr/bin/phantomjs ]; then
  echo "install phantomjs"
  ln -s `pwd`/app/tools/phantomjs  /usr/bin/phantomjs
fi

if [ ! -f /etc/nginx/conf.d/arl.conf ]; then
  echo "copy arl.conf"
  cp misc/arl.conf /etc/nginx/conf.d
fi



if [ ! -f /etc/ssl/certs/dhparam.pem ]; then
  echo "download dhparam.pem"
  curl https://ssl-config.mozilla.org/ffdhe2048.txt > /etc/ssl/certs/dhparam.pem
fi


echo "gen cert ..."
chmod +x docker/worker/gen_crt.sh
./docker/worker/gen_crt.sh


cd /opt/ARL/


if [ ! -f /etc/systemd/system/arl-web.service ]; then
  echo  "copy arl-web.service"
  cp misc/arl-web.service /etc/systemd/system/
fi

if [ ! -f /etc/systemd/system/arl-worker.service ]; then
  echo  "copy arl-worker.service"
  cp misc/arl-worker.service /etc/systemd/system/
fi


if [ ! -f /etc/systemd/system/arl-worker-github.service ]; then
  echo  "copy arl-worker-github.service"
  cp misc/arl-worker-github.service /etc/systemd/system/
fi

if [ ! -f /etc/systemd/system/arl-scheduler.service ]; then
  echo  "copy arl-scheduler.service"
  cp misc/arl-scheduler.service /etc/systemd/system/
fi

chmod +x /opt/ARL/app/tools/*

echo "start arl services ..."

systemctl enable arl-web
systemctl restart arl-web
systemctl enable arl-worker
systemctl restart arl-worker
systemctl enable arl-worker-github
systemctl restart arl-worker-github
systemctl enable arl-scheduler
systemctl restart arl-scheduler
systemctl enable nginx
systemctl restart nginx

export ARL_ADMIN_PASSWORD

echo ""
echo "=========================================="
echo "  ARL 安装完成！"
echo "=========================================="
echo "  管理员账号: admin"
echo "  管理员密码: ${ARL_ADMIN_PASSWORD}"
echo "  API Key:    ${ARL_API_KEY}"
echo ""
echo "  凭证文件:   ${ARL_CREDENTIALS_FILE}"
echo "  请妥善保管以上信息！"
echo "=========================================="
