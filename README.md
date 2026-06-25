# Telegram → Bark / Server酱³ 通知系统 README

基于：

* Python
* Telethon
* Bark（iOS 推送）
* Server酱³（Android/iOS 推送）

实现：

* Telegram 私聊通知
* Telegram @你 通知
* Telegram 回复你 通知
* 通过 Bark / Server酱³ 双通道推送到手机
* 通知显示真实消息内容
* Telegram 收藏夹远程分别控制两个通道开关
* 点击通知直接打开 Telegram

适用于：

* Oracle Cloud ARM VPS
* Ubuntu 22.04
* 长期后台运行

---

# 一、项目目录

项目目录：

```bash
~/tg-bark
```

主要文件：

```text
~/tg-bark
├── main.py
├── .env
├── .env.example
├── requirements.txt
├── state.json
├── tg_bark.session
├── venv/
```

---

# 二、功能说明

## 当前支持

### 会推送

* Telegram 私聊
* 群组 @你
* 回复你的消息

---

### 不会推送

* 普通群消息
* 无关频道消息
* 你自己发出的消息

---

# 三、远程控制推送（重要）

现在支持：

```text
Telegram 收藏夹 / Saved Messages
```

远程控制推送开关。

你只需要：

## 在 Telegram 收藏夹里发送：

### 开启推送

```text
/on          — 开启全部通道
/on bark     — 仅开启 Bark
/on sc3      — 仅开启 Server酱³
```

---

### 关闭推送

```text
/off         — 关闭全部通道
/off bark    — 仅关闭 Bark
/off sc3     — 仅关闭 Server酱³
```

---

### 查看当前状态

```text
/status
```

---

### 查看帮助

```text
/help
```

---

## 特点

* 不需要登录 VPS
* 手机即可控制
* 两个通道可分别开关
* 状态永久保存
* VPS 重启后依然生效

状态保存在：

```text
state.json
```

---

# 四、安装 Python 环境

## 1. 创建目录

```bash
mkdir -p ~/tg-bark
cd ~/tg-bark
```

---

## 2. 创建虚拟环境

```bash
python3 -m venv venv
```

激活：

```bash
source venv/bin/activate
```

看到：

```text
(venv)
```

代表成功。

---

## 3. 安装依赖

```bash
pip install -r requirements.txt
```

---

# 五、获取 Telegram API

打开：

```text
https://my.telegram.org
```

登录 Telegram。

进入：

```text
API development tools
```

创建应用。

得到：

```text
api_id
api_hash
```

---

# 六、安装 Bark

iPhone 安装：

```text
Bark
```

打开 App 后会得到：

```text
https://api.day.app/你的KEY
```

其中：

```text
你的KEY
```

就是：

```env
BARK_KEY
```

---

# 七、获取 Server酱³ SendKey

打开：

```text
https://sc3.ft07.com/
```

登录后进入 SendKey 页面，复制 `SendKey`。

格式类似：

```text
sctp123456t...
```

---

# 八、配置 .env

创建：

```bash
vi .env
```

按：

```text
i
```

进入编辑模式。

填入：

```env
TG_API_ID=你的api_id
TG_API_HASH=你的api_hash
TG_SESSION=tg_bark

BARK_ENABLED=true
BARK_KEY=你的Bark_Key
BARK_SERVER=https://api.day.app
BARK_ICON=https://cdn.nodeimage.com/i/zjy7G6Nv4ENdd927CAN8D0AY5WXDG2iw.webp

SC3_ENABLED=true
SC3_SENDKEY=你的Server酱3_SendKey

MY_USERNAME=你的Telegram用户名
```

说明：

* `BARK_KEY` / `SC3_SENDKEY` — 至少填一个，可同时填
* `BARK_ENABLED` / `SC3_ENABLED` — 部署层总开关，设为 `false` 则该通道完全不工作
* `MY_USERNAME` 不要带 `@`

例如：

```env
MY_USERNAME=test123
```

---

## 保存退出 vi

按：

```text
ESC
```

输入：

```text
:wq
```

回车。

---

# 九、首次运行

进入目录：

```bash
cd ~/tg-bark
```

激活环境：

```bash
source venv/bin/activate
```

运行：

```bash
python main.py
```

---

# 九、首次登录 Telegram

第一次运行会要求：

```text
输入手机号
输入验证码
输入二步验证密码（如果开启）
```

成功后会生成：

```text
tg_bark.session
```

以后不需要重复登录。

---

# 十、Bark 推送效果

当前：

* Telegram 图标
* 自定义声音
* 点击通知打开 Telegram
* 不显示真实消息内容
* 保护隐私

通知内容：

```text
Telegram｜私聊
用户名: 点击查看
```

---

# 十一、后台永久运行

## 1. 创建 systemd 服务

```bash
sudo vi /etc/systemd/system/tg-bark.service
```

填入：

```ini
[Unit]
Description=Telegram Bark Notifier
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/tg-bark
ExecStart=/home/ubuntu/tg-bark/venv/bin/python /home/ubuntu/tg-bark/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

保存：

```text
ESC
:wq
```

---

## 2. 刷新 systemd

```bash
sudo systemctl daemon-reload
```

---

## 3. 开机自启

```bash
sudo systemctl enable tg-bark
```

---

## 4. 启动服务

```bash
sudo systemctl start tg-bark
```

---

# 十二、常用命令

## 查看状态

```bash
sudo systemctl status tg-bark
```

如果看到：

```text
active (running)
```

代表正常。

---

## 重启

```bash
sudo systemctl restart tg-bark
```

---

## 停止

```bash
sudo systemctl stop tg-bark
```

---

## 启动

```bash
sudo systemctl start tg-bark
```

---

## 开机自启

```bash
sudo systemctl enable tg-bark
```

---

## 关闭开机自启

```bash
sudo systemctl disable tg-bark
```

---

# 十三、查看日志（非常重要）

实时查看：

```bash
journalctl -u tg-bark -f
```

退出：

```text
CTRL + C
```

---

## 查看最近日志

```bash
journalctl -u tg-bark -n 100
```

---

## 查看今天日志

```bash
journalctl -u tg-bark --since today
```

---

# 十四、修改代码后如何生效

编辑：

```bash
vi main.py
```

修改完成后：

```bash
sudo systemctl restart tg-bark
```

查看日志确认：

```bash
journalctl -u tg-bark -f
```

---

# 十五、安全建议

## 1. 保护 .env

```bash
chmod 600 .env
```

---

## 2. 保护 session

```bash
chmod 600 *.session
```

---

## 3. 不要泄露

以下内容绝对不要泄露：

```text
api_hash
BARK_KEY
.session 文件
```

否则别人可能登录你的 Telegram。

---

# 十六、升级依赖

进入目录：

```bash
cd ~/tg-bark
source venv/bin/activate
```

升级：

```bash
pip install -U telethon aiohttp python-dotenv
```

---

# 十七、完全删除项目

停止服务：

```bash
sudo systemctl stop tg-bark
sudo systemctl disable tg-bark
```

删除服务：

```bash
sudo rm /etc/systemd/system/tg-bark.service
sudo systemctl daemon-reload
```

删除项目：

```bash
rm -rf ~/tg-bark
```

---

# 十八、故障排查

## 1. 服务启动失败

查看：

```bash
sudo systemctl status tg-bark
```

以及：

```bash
journalctl -u tg-bark -f
```

---

## 2. 收不到通知

检查：

* Bark 是否联网
* iPhone 是否允许通知
* BARK_KEY 是否正确
* VPS 是否能访问：

```text
https://api.day.app
```

---

## 3. Telegram 登录失效

删除：

```bash
rm *.session
```

重新运行：

```bash
python main.py
```

重新登录。

---

# 十九、当前实现特点

## 优点

* 极轻量
* ARM 兼容好
* 内存占用低
* 长期稳定
* 不依赖数据库
* 自动重连
* 后台守护
* 开机自启
* 手机远程控制推送

---

# 二十、推荐 VPS 配置

当前 Oracle ARM：

```text
1核
6GB RAM
Ubuntu 22.04
```

非常适合此项目。

实际占用通常：

```text
CPU：极低
内存：100~200MB
```

---

# 二十一、作者备注

这是一个：

```text
Telegram -> Bark -> iPhone
```

消息通知系统。

核心目标：

```text
绕过 Telegram 海外推送限制
```

实现：

* 关键消息实时通知
* iPhone 原生通知体验
* 长期后台稳定运行
* 手机远程控制开关
* 尽量保护隐私

```
```
