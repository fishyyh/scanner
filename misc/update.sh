systemctl stop arl-*
cd /opt/
rm -rf ARLbak
mv ARL ARLbak
mv scaner/ ARL
cp ARLbak/app/config.yaml ARL/app/
systemctl restart arl-*