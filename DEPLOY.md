# tg-bark 部署教程

## 环境要求

- Ubuntu 22.04 / 20.04（或其他 Linux）
- Python 3.9+
- 一个 Telegram 账号

---

## 1. 准备凭证

### Telegram API

打开 https://my.telegram.org ，登录后进入 **API development tools**，创建一个应用，获得：

- `api_id`
- `api_hash`

### Bark（iOS 推送，可选）

iPhone 安装 Bark App，打开后获得 Key。  
或在 https://api.day.app 查看。

### Server酱³（Android/iOS 推送，可选）

打开 https://sc3.ft07.com/ ，登录后进入 SendKey 页面，复制 `SendKey`（格式 `sctp{uid}t...`）。

> Bark 和 Server酱³ 至少配一个。

---

## 2. 获取代码

**方式一：从 GitHub 克隆（推荐，服务器上直接执行）**

```bash
git clone https://github.com/splendidmata/tg-bark.git ~/tg-bark
cd ~/tg-bark
```

**方式二：手动上传**

```bash
# 在本地打包
cd tg-bark
tar -czf ../tg-bark.tar.gz .

# 上传
scp ../tg-bark.tar.gz ubuntu@你的服务器IP:~/
```

在服务器上解压：

```bash
mkdir -p ~/tg-bark
tar -xzf ~/tg-bark.tar.gz -C ~/tg-bark
cd ~/tg-bark
```

---

## 3. 一键部署

```bash
chmod +x deploy.sh
./deploy.sh
```

脚本会逐项询问配置，回车跳过使用默认值。执行流程：

1. 环境检查（Python、pip）
2. 交互式填写配置（见下方）
3. 创建虚拟环境 + 安装依赖
4. 保护敏感文件权限
5. 创建 systemd 服务（含安全加固）
6. 配置日志轮转（每天轮转，保留 7 天）
7. 启用开机自启并启动服务

### 交互式配置流程

运行后会逐项提问：

```
--- Telegram 配置 ---
TG_API_ID（从 https://my.telegram.org 获取）: 12345678
TG_API_HASH: abcdef1234567890
TG_SESSION [tg_bark]: （回车）

--- Bark 推送（iOS，可选，回车跳过）---
BARK_KEY（Bark App 里的 Key，留空跳过）: xxxxxxxxxxxx
BARK_SERVER [https://api.day.app]: （回车）
BARK_ICON [https://...]: （回车）

--- Server酱³ 推送（Android/iOS，可选，回车跳过）---
SC3_SENDKEY（从 https://sc3.ft07.com/sendkey 获取，留空跳过）: sctp123456t...

--- 其他配置 ---
MY_USERNAME（Telegram 用户名，不要带 @，留空跳过）: yourname
MAX_BODY_LEN（推送消息最大字数）[500]: （回车）
```

填写完毕后会展示完整配置让你确认，确认无误继续部署。

> 至少填一个推送通道（Bark 或 Server酱³），否则会报错退出。

---

## 4. 首次登录 Telegram

服务启动后，首次需要输入手机号验证码：

```bash
# 先停止服务
sudo systemctl stop tg-bark

# 手动运行一次完成登录
cd ~/tg-bark
source venv/bin/activate
python main.py
```

按提示输入手机号、验证码、二步验证密码（如果有），看到 "已登录 Telegram" 后 `Ctrl+C` 退出。

```bash
# 重新启动服务
sudo systemctl start tg-bark
```

---

## 5. 测试推送

1. 打开 Telegram，进入 **收藏夹（Saved Messages）**，发送 `/status`
2. 应该收到回复，显示两个通道的状态
3. 让朋友给你发一条私聊，手机应该收到推送

---

## 常用命令

| 操作 | 命令 |
|------|------|
| 查看状态 | `sudo systemctl status tg-bark` |
| 启动 | `sudo systemctl start tg-bark` |
| 停止 | `sudo systemctl stop tg-bark` |
| 重启 | `sudo systemctl restart tg-bark` |
| 实时日志 | `tail -f /var/log/tg-bark/app.log` |
| 查看最近日志 | `journalctl -u tg-bark -n 50` |
| 修改 .env 后生效 | `sudo systemctl restart tg-bark` |

日志文件每天自动轮转，保留 7 天，压缩存储。

---

## 远程控制（Telegram 收藏夹）

在 Telegram 收藏夹里发送命令，无需登录服务器：

| 命令 | 效果 |
|------|------|
| `/on` | 开启全部通道 |
| `/on bark` | 仅开启 Bark |
| `/on sc3` | 仅开启 Server酱³ |
| `/off` | 关闭全部通道 |
| `/off bark` | 仅关闭 Bark |
| `/off sc3` | 仅关闭 Server酱³ |
| `/status` | 查看各通道状态 |
| `/help` | 查看帮助 |

---

## 升级

```bash
cd ~/tg-bark
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart tg-bark
```

---

## 完全卸载

```bash
sudo systemctl stop tg-bark
sudo systemctl disable tg-bark
sudo rm /etc/systemd/system/tg-bark.service
sudo rm /etc/logrotate.d/tg-bark
sudo systemctl daemon-reload
rm -rf ~/tg-bark
sudo rm -rf /var/log/tg-bark
```

---

## 安全建议

```bash
chmod 600 ~/tg-bark/.env
chmod 600 ~/tg-bark/*.session
```

以下内容绝对不要泄露：

- `api_hash`
- `BARK_KEY` / `SC3_SENDKEY`
- `.session` 文件（可登录你的 Telegram）
