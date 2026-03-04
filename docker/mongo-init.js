// 此文件由 setup-arl.sh 部署时动态生成，请勿手动修改
// admin 密码和 salt 在部署时随机生成并写入
// 占位符会被 sed 替换
var salt = "ARL_PASSWORD_SALT_PLACEHOLDER";
var password = "ARL_ADMIN_PASS_PLACEHOLDER";

var hash = hex_md5(salt + password);
db.user.drop();
db.user.insert({ username: 'admin', password: hash });
