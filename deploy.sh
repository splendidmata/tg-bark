#!/bin/bash
set -e

# ============================================================
# tg-bark 一键部署脚本
# 用法：chmod +x deploy.sh && ./deploy.sh
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# -------------------- 配置 --------------------
APP_NAME="tg-bark"
GIT_REPO="https://github.com/splendidmata/tg-bark.git"
INSTALL_DIR="${HOME}/${APP_NAME}"
VENV_DIR="${INSTALL_DIR}/venv"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
LOGROTATE_FILE="/etc/logrotate.d/${APP_NAME}"
PYTHON_BIN="${VENV_DIR}/bin/python"
LOG_DIR="/var/log/${APP_NAME}"

# -------------------- 1. 环境检查 --------------------
log "检查 Python ..."
python3 --version >/dev/null 2>&1 || err "未安装 python3，请先 apt install python3 python3-venv"

log "检查 pip ..."
python3 -m pip --version >/dev/null 2>&1 || err "未安装 pip，请先 apt install python3-pip"

# -------------------- 2. 获取代码 --------------------
# 如果当前目录就是项目源码目录，用 rsync；否则从 GitHub 克隆
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "${SCRIPT_DIR}/main.py" ] && [ -f "${SCRIPT_DIR}/requirements.txt" ]; then
    log "从 ${SCRIPT_DIR} 同步项目文件 ..."
    rsync -a --exclude='venv' --exclude='__pycache__' --exclude='.env' \
          --exclude='state.json' --exclude='*.session' --exclude='.git' \
          "${SCRIPT_DIR}/" "${INSTALL_DIR}/"
else
    log "从 GitHub 克隆项目 ..."
    if [ -d "${INSTALL_DIR}/.git" ]; then
        log "已存在仓库，拉取最新代码 ..."
        cd "${INSTALL_DIR}" && git pull
    else
        git clone "${GIT_REPO}" "${INSTALL_DIR}"
    fi
fi

# -------------------- 3. 虚拟环境 --------------------
log "创建虚拟环境 ..."
python3 -m venv "${VENV_DIR}"

log "安装依赖 ..."
"${PYTHON_BIN}" -m pip install --upgrade pip -q
"${PYTHON_BIN}" -m pip install -r "${INSTALL_DIR}/requirements.txt" -q

# -------------------- 4. 交互式配置 --------------------
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  配置 .env（回车跳过使用默认值）${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# 如果已有 .env 则跳过
if [ -f "${INSTALL_DIR}/.env" ]; then
    warn ".env 已存在，跳过配置"
else
    # --- Telegram ---
    echo -e "${YELLOW}--- Telegram 配置 ---${NC}"
    read -p "TG_API_ID（从 https://my.telegram.org 获取）: " INPUT
    TG_API_ID="${INPUT:-你的api_id}"

    read -p "TG_API_HASH: " INPUT
    TG_API_HASH="${INPUT:-你的api_hash}"

    read -p "TG_SESSION [tg_bark]: " INPUT
    TG_SESSION="${INPUT:-tg_bark}"

    echo ""

    # --- Bark ---
    echo -e "${YELLOW}--- Bark 推送（iOS，可选，回车跳过）---${NC}"
    read -p "BARK_KEY（Bark App 里的 Key，留空跳过）: " INPUT
    BARK_KEY="${INPUT}"

    if [ -n "$BARK_KEY" ]; then
        BARK_ENABLED="true"
        read -p "BARK_SERVER [https://api.day.app]: " INPUT
        BARK_SERVER="${INPUT:-https://api.day.app}"
        read -p "BARK_ICON [https://cdn.nodeimage.com/i/zjy7G6Nv4ENdd927CAN8D0AY5WXDG2iw.webp]: " INPUT
        BARK_ICON="${INPUT:-https://cdn.nodeimage.com/i/zjy7G6Nv4ENdd927CAN8D0AY5WXDG2iw.webp}"
    else
        BARK_ENABLED="false"
        BARK_SERVER="https://api.day.app"
        BARK_ICON="https://cdn.nodeimage.com/i/zjy7G6Nv4ENdd927CAN8D0AY5WXDG2iw.webp"
    fi

    echo ""

    # --- Server酱³ ---
    echo -e "${YELLOW}--- Server酱³ 推送（Android/iOS，可选，回车跳过）---${NC}"
    read -p "SC3_SENDKEY（从 https://sc3.ft07.com/sendkey 获取，留空跳过）: " INPUT
    SC3_SENDKEY="${INPUT}"

    if [ -n "$SC3_SENDKEY" ]; then
        SC3_ENABLED="true"
    else
        SC3_ENABLED="false"
    fi

    echo ""

    # --- 其他 ---
    echo -e "${YELLOW}--- 其他配置 ---${NC}"
    read -p "MY_USERNAME（Telegram 用户名，不要带 @，留空跳过）: " INPUT
    MY_USERNAME="${INPUT}"

    read -p "MAX_BODY_LEN（推送消息最大字数）[500]: " INPUT
    MAX_BODY_LEN="${INPUT:-500}"

    # 至少配一个推送通道
    if [ -z "$BARK_KEY" ] && [ -z "$SC3_SENDKEY" ]; then
        err "BARK_KEY 和 SC3_SENDKEY 至少需要填一个！"
    fi

    # 写入 .env
    cat > "${INSTALL_DIR}/.env" << ENVEOF
TG_API_ID=${TG_API_ID}
TG_API_HASH=${TG_API_HASH}
TG_SESSION=${TG_SESSION}

BARK_ENABLED=${BARK_ENABLED}
BARK_KEY=${BARK_KEY}
BARK_SERVER=${BARK_SERVER}
BARK_ICON=${BARK_ICON}

SC3_ENABLED=${SC3_ENABLED}
SC3_SENDKEY=${SC3_SENDKEY}

MY_USERNAME=${MY_USERNAME}
MAX_BODY_LEN=${MAX_BODY_LEN}
ENVEOF

    echo ""
    log ".env 配置完成"
    echo ""
    cat "${INSTALL_DIR}/.env"
    echo ""
    read -p "确认以上配置无误？[Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        rm "${INSTALL_DIR}/.env"
        err "已取消，.env 已删除，请重新运行脚本"
    fi
fi

# -------------------- 5. 权限 --------------------
chmod 600 "${INSTALL_DIR}/.env"
log "已保护 .env（仅所有者可读写）"

# -------------------- 6. 系统服务 --------------------
log "创建 systemd 服务 ..."
sudo tee "${SERVICE_FILE}" > /dev/null << EOF
[Unit]
Description=${APP_NAME} - Telegram to Bark/ServerChan3 push notifier
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=${PYTHON_BIN} ${INSTALL_DIR}/main.py
Restart=always
RestartSec=10
StandardOutput=append:${LOG_DIR}/app.log
StandardError=append:${LOG_DIR}/app.log

# 安全加固
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${INSTALL_DIR} ${LOG_DIR}
ReadOnlyPaths=/

[Install]
WantedBy=multi-user.target
EOF

# -------------------- 7. 日志目录 --------------------
sudo mkdir -p "${LOG_DIR}"
sudo chown "${USER}:${USER}" "${LOG_DIR}"
log "日志目录: ${LOG_DIR}"

# -------------------- 8. 日志轮转 --------------------
log "配置日志轮转 ..."
sudo tee "${LOGROTATE_FILE}" > /dev/null << EOF
${LOG_DIR}/*.log {
    daily
    rotate 7
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
    dateext
    dateformat -%Y%m%d
    maxsize 50M
}
EOF

# -------------------- 9. 首次登录（处理二步验证） --------------------
log "重载 systemd ..."
sudo systemctl daemon-reload

log "启用开机自启 ..."
sudo systemctl enable "${APP_NAME}"

SESSION_FILE="${INSTALL_DIR}/${TG_SESSION}.session"

if [ -f "${SESSION_FILE}" ]; then
    log "已找到 session 文件，跳过登录"
else
    echo ""
    echo -e "${YELLOW}============================================${NC}"
    echo -e "${YELLOW}  需要首次登录 Telegram${NC}"
    echo -e "${YELLOW}============================================${NC}"
    echo ""
    echo "接下来会交互式运行 main.py 完成登录："
    echo "  1. 输入手机号（格式: +8613800138000）"
    echo "  2. 输入收到的验证码"
    echo "  3. 如果开启二步验证，输入二步验证密码"
    echo "  4. 看到 '已登录 Telegram' 后按 Ctrl+C 退出"
    echo ""
    read -p "按回车开始登录..." -r

    cd "${INSTALL_DIR}"
    source "${VENV_DIR}/bin/activate"
    python main.py &
    MAIN_PID=$!

    # 等待登录完成或超时（最长 120 秒）
    WAITED=0
    while [ $WAITED -lt 120 ]; do
        sleep 1
        WAITED=$((WAITED + 1))

        # 检查日志中是否出现登录成功
        if journalctl -u "${APP_NAME}" -n 5 2>/dev/null | grep -q "已登录 Telegram" 2>/dev/null; then
            :
        fi

        # 检查 session 文件是否生成
        if [ -f "${SESSION_FILE}" ]; then
            log "检测到 session 文件已生成，登录完成"
            sleep 1
            kill "${MAIN_PID}" 2>/dev/null || true
            wait "${MAIN_PID}" 2>/dev/null || true
            break
        fi

        if [ $((WAITED % 30)) -eq 0 ]; then
            echo "  等待中... (${WAITED}s，请完成登录)"
        fi
    done

    if [ ! -f "${SESSION_FILE}" ]; then
        kill "${MAIN_PID}" 2>/dev/null || true
        err "登录超时（120s），未检测到 session 文件。请确认凭证正确后重新运行脚本"
    fi

    echo ""
    log "登录成功！"
fi

# -------------------- 10. 启动服务 --------------------
log "启动服务 ..."
sudo systemctl start "${APP_NAME}"

sleep 2

# -------------------- 11. 检查状态 --------------------
if sudo systemctl is-active --quiet "${APP_NAME}"; then
    log "部署成功！"
    echo ""
    echo "  ┌─────────────────────────────────────────┐"
    echo "  │  状态        sudo systemctl status ${APP_NAME}"
    echo "  │  日志        tail -f ${LOG_DIR}/app.log"
    echo "  │  重启        sudo systemctl restart ${APP_NAME}"
    echo "  │  配置文件    ${INSTALL_DIR}/.env"
    echo "  └─────────────────────────────────────────┘"
    echo ""
    log "当前日志："
    echo "---"
    tail -20 "${LOG_DIR}/app.log" 2>/dev/null || echo "(暂无日志)"
else
    err "服务启动失败，查看日志: sudo journalctl -u ${APP_NAME} -n 30"
fi
