#!/bin/bash
set -e

cd /opt/

# 检查新版本目录是否存在
if [ ! -d "scanner" ]; then
    echo "错误: /opt/scanner 目录不存在，请先下载新版本"
    exit 1
fi

# 停止服务
systemctl stop arl-*

# 保留旧配置到新版本
cp ARL/app/config.yaml scanner/app/config.yaml

# 备份当前版本（删除上次备份）
rm -rf ARLbak
mv ARL ARLbak

# 部署新版本
mv scanner/ ARL

# 同步 nginx 配置并重载
cp /opt/ARL/misc/arl.conf /etc/nginx/conf.d/arl.conf
nginx -t && systemctl reload nginx

# 启动服务
systemctl restart arl-*

echo "更新完成，旧版本已备份到 /opt/ARLbak"