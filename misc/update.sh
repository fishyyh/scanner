#!/bin/bash

cd /opt/

# 检查新版本目录是否存在
if [ ! -d "scanner" ]; then
    echo "错误: /opt/scanner 目录不存在，请先下载新版本"
    exit 1
fi

# 检查旧版本目录是否存在
if [ ! -d "ARL" ]; then
    echo "错误: /opt/ARL 目录不存在"
    exit 1
fi

# 停止服务（忽略未运行的服务）
systemctl stop arl-web arl-worker arl-scheduler arl-worker-github 2>/dev/null || true

# 保留旧配置到新版本
if [ -f ARL/app/config.yaml ]; then
    cp ARL/app/config.yaml scanner/app/config.yaml
else
    echo "警告: 旧版本 config.yaml 不存在，将使用新版本默认配置"
fi

# 备份当前版本（删除上次备份）
rm -rf ARLbak
mv ARL ARLbak

# 部署新版本
mv scanner/ ARL

# 同步 nginx 配置并重载
if [ -f /opt/ARL/misc/arl.conf ]; then
    cp /opt/ARL/misc/arl.conf /etc/nginx/conf.d/arl.conf
    nginx -t 2>/dev/null && systemctl reload nginx || echo "警告: nginx 配置检测失败，请手动检查"
fi

# 启动服务
systemctl restart arl-web arl-worker arl-scheduler 2>/dev/null
systemctl restart arl-worker-github 2>/dev/null || true

echo "更新完成，旧版本已备份到 /opt/ARLbak"