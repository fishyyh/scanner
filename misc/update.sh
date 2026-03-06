systemctl stop arl-*
cd /opt/
rm -rf ARLbak
cp ARL/app/config.yaml  scanner/app/config.yaml
mv ARL ARLbak
mv scanner/ ARL
systemctl restart arl-*