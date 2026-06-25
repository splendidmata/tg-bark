import os
import re
import json
import asyncio
import logging
from typing import Optional

import aiohttp
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import User, Chat, Channel


load_dotenv()

TG_API_ID_STR = os.getenv("TG_API_ID", "0")
try:
    TG_API_ID = int(TG_API_ID_STR)
except ValueError:
    raise RuntimeError(f"TG_API_ID 必须为整数，当前值: {TG_API_ID_STR}")
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_SESSION = os.getenv("TG_SESSION", "tg_bark")

BARK_KEY = os.getenv("BARK_KEY", "")
BARK_SERVER = os.getenv("BARK_SERVER", "https://api.day.app").rstrip("/")
BARK_ENABLED = os.getenv("BARK_ENABLED", "true").lower() == "true"
BARK_ICON = os.getenv("BARK_ICON", "https://cdn.nodeimage.com/i/zjy7G6Nv4ENdd927CAN8D0AY5WXDG2iw.webp")

SC3_SENDKEY = os.getenv("SC3_SENDKEY", "")
SC3_ENABLED = os.getenv("SC3_ENABLED", "true").lower() == "true"

MY_USERNAME = os.getenv("MY_USERNAME", "").lstrip("@").lower()

MAX_BODY_LEN = int(os.getenv("MAX_BODY_LEN", "500"))
PUSH_SELF_MESSAGES = os.getenv("PUSH_SELF_MESSAGES", "false").lower() == "true"

STATE_FILE = os.getenv("STATE_FILE", "state.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

client = TelegramClient(TG_SESSION, TG_API_ID, TG_API_HASH)


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return _normalize_state({"push_enabled": True})

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logging.warning("读取状态文件失败，使用默认开启状态: %s", e)
        return _normalize_state({"push_enabled": True})

    return _normalize_state(data)


def _normalize_state(data: dict) -> dict:
    # 兼容旧格式 {push_enabled: true}
    if "bark_enabled" not in data and "sc3_enabled" not in data:
        old_val = data.get("push_enabled", True)
        return {"bark_enabled": old_val, "sc3_enabled": old_val}

    return {
        "bark_enabled": data.get("bark_enabled", True),
        "sc3_enabled": data.get("sc3_enabled", True),
    }


# 启动时一次性加载到内存，避免每次检查都读写文件
_state = load_state()


def save_state(state: dict):
    global _state
    _state = state
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def is_bark_enabled() -> bool:
    return bool(_state.get("bark_enabled", True))


def is_sc3_enabled() -> bool:
    return bool(_state.get("sc3_enabled", True))


def set_bark_enabled(enabled: bool):
    _state["bark_enabled"] = enabled
    save_state(_state)


def set_sc3_enabled(enabled: bool):
    _state["sc3_enabled"] = enabled
    save_state(_state)


def shorten(text: str, limit: int = MAX_BODY_LEN) -> str:
    text = (text or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def display_name(entity) -> str:
    if entity is None:
        return "未知"

    if isinstance(entity, User):
        name = " ".join(
            part for part in [
                getattr(entity, "first_name", None),
                getattr(entity, "last_name", None),
            ] if part
        ).strip()
        return name or getattr(entity, "username", None) or str(entity.id)

    if isinstance(entity, (Chat, Channel)):
        return getattr(entity, "title", None) or getattr(entity, "username", None) or str(entity.id)

    return getattr(entity, "title", None) or getattr(entity, "username", None) or "未知"


def message_summary(event) -> str:
    msg = event.message

    if event.raw_text:
        return shorten(event.raw_text)

    if msg.photo:
        return "[图片]"
    if msg.video:
        return "[视频]"
    if msg.voice:
        return "[语音]"
    if msg.audio:
        return "[音频]"
    if msg.document:
        return "[文件]"
    if msg.sticker:
        return "[贴纸]"

    return "[非文本消息]"


def has_username_mention(text: str) -> bool:
    if not MY_USERNAME or not text:
        return False

    pattern = rf"(?<!\w)@{re.escape(MY_USERNAME)}(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


async def is_reply_to_me(event) -> bool:
    if not event.is_reply:
        return False

    try:
        reply_msg = await event.get_reply_message()
        if not reply_msg:
            return False

        me = await client.get_me()
        return reply_msg.sender_id == me.id
    except Exception as e:
        logging.warning("检查回复消息失败: %s", e)
        return False


async def should_push(event) -> tuple[bool, str]:
    if event.out and not PUSH_SELF_MESSAGES:
        return False, "忽略自己发出的消息"

    if event.is_private:
        return True, "私聊"

    text = event.raw_text or ""

    if event.message.mentioned:
        return True, "被@"

    if has_username_mention(text):
        return True, "用户名@"

    if await is_reply_to_me(event):
        return True, "回复你"

    return False, "非私聊且未@你"


async def handle_saved_messages_command(event) -> bool:
    """
    只处理 Telegram 收藏夹 / Saved Messages 里的命令。
    支持：
    /on [bark|sc3]   — 开启指定通道（无参数则全部开启）
    /off [bark|sc3]  — 关闭指定通道（无参数则全部关闭）
    /status          — 查看各通道状态
    /help            — 查看帮助
    """

    if not event.out:
        return False

    if not event.is_private:
        return False

    me = await client.get_me()

    if event.chat_id != me.id:
        return False

    text = (event.raw_text or "").strip().lower()
    parts = text.split()
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "/on":
        if arg == "bark":
            set_bark_enabled(True)
            await event.reply("✅ Bark 推送已开启")
            logging.info("收到命令：开启 Bark 推送")
        elif arg == "sc3":
            set_sc3_enabled(True)
            await event.reply("✅ Server酱³ 推送已开启")
            logging.info("收到命令：开启 Server酱³ 推送")
        else:
            set_bark_enabled(True)
            set_sc3_enabled(True)
            await event.reply("✅ 所有推送通道已开启")
            logging.info("收到命令：开启所有推送")
        return True

    if cmd == "/off":
        if arg == "bark":
            set_bark_enabled(False)
            await event.reply("🔕 Bark 推送已关闭")
            logging.info("收到命令：关闭 Bark 推送")
        elif arg == "sc3":
            set_sc3_enabled(False)
            await event.reply("🔕 Server酱³ 推送已关闭")
            logging.info("收到命令：关闭 Server酱³ 推送")
        else:
            set_bark_enabled(False)
            set_sc3_enabled(False)
            await event.reply("🔕 所有推送通道已关闭")
            logging.info("收到命令：关闭所有推送")
        return True

    if cmd == "/status":
        bark = "开启 ✅" if is_bark_enabled() else "关闭 🔕"
        sc3 = "开启 ✅" if is_sc3_enabled() else "关闭 🔕"
        await event.reply(
            f"推送通道状态：\n\n"
            f"Bark: {bark}\n"
            f"Server酱³: {sc3}"
        )
        logging.info("收到命令：查看状态")
        return True

    if cmd == "/help":
        await event.reply(
            "Telegram 推送控制命令：\n\n"
            "/on 开启全部推送\n"
            "/on bark 开启 Bark\n"
            "/on sc3 开启 Server酱³\n"
            "/off 关闭全部推送\n"
            "/off bark 关闭 Bark\n"
            "/off sc3 关闭 Server酱³\n"
            "/status 查看当前状态\n"
            "/help 查看帮助\n\n"
            "说明：这些命令只在 Telegram 收藏夹 / Saved Messages 里生效。"
        )
        logging.info("收到命令：查看帮助")
        return True

    return False


async def push_bark(title: str, body: str, url: Optional[str] = None) -> bool:
    if not BARK_KEY or not BARK_ENABLED:
        return False

    api_url = f"{BARK_SERVER}/{BARK_KEY}"

    payload = {
        "title": title,
        "body": body,
        "group": "Telegram",
        "sound": "healthnotification",
        "icon": BARK_ICON,
    }

    if url:
        payload["url"] = url

    for i in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, timeout=10) as resp:
                    resp_text = await resp.text()
                    if resp.status == 200:
                        logging.info("Bark推送成功: %s", title)
                        return True

                    logging.warning(
                        "Bark推送失败，第%s次，HTTP=%s，返回=%s",
                        i + 1,
                        resp.status,
                        resp_text,
                    )
        except Exception as e:
            logging.warning("Bark请求异常，第%s次: %s", i + 1, e)

        await asyncio.sleep(2)

    return False


def build_sc3_url() -> Optional[str]:
    """从 SendKey 构建 Server酱³ API URL"""
    if not SC3_SENDKEY:
        return None

    match = re.match(r"^sctp(\d+)t", SC3_SENDKEY)
    if not match:
        logging.warning("SC3_SENDKEY 格式无效，应为 sctp{uid}t... 格式")
        return None

    uid = match.group(1)
    return f"https://{uid}.push.ft07.com/send/{SC3_SENDKEY}.send"


async def push_sc3(title: str, body: str, url: Optional[str] = None) -> bool:
    if not SC3_SENDKEY or not SC3_ENABLED:
        return False

    api_url = build_sc3_url()
    if not api_url:
        return False

    payload = {
        "title": title,
        "desp": body,
        "tags": "Telegram",
    }

    if url:
        payload["desp"] = f"[{body}]({url})"

    for i in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, timeout=10) as resp:
                    resp_text = await resp.text()
                    if resp.status == 200:
                        logging.info("Server酱³推送成功: %s", title)
                        return True

                    logging.warning(
                        "Server酱³推送失败，第%s次，HTTP=%s，返回=%s",
                        i + 1,
                        resp.status,
                        resp_text,
                    )
        except Exception as e:
            logging.warning("Server酱³请求异常，第%s次: %s", i + 1, e)

        await asyncio.sleep(2)

    return False


@client.on(events.NewMessage)
async def on_new_message(event):
    try:
        if await handle_saved_messages_command(event):
            return

        ok, reason = await should_push(event)
        if not ok:
            logging.debug("跳过消息: %s", reason)
            return

        chat = await event.get_chat()
        sender = await event.get_sender()

        chat_name = display_name(chat)
        sender_name = display_name(sender)

        summary = message_summary(event)

        title = f"Telegram｜{reason}"

        if event.is_private:
            body = f"{sender_name}: {summary}"
        else:
            body = f"{chat_name}\n{sender_name}: {summary}"

        logging.info("准备推送: %s | %s", title, body)

        tasks = []
        if is_bark_enabled():
            tasks.append(push_bark(title, body, "tg://"))
        if is_sc3_enabled():
            tasks.append(push_sc3(title, body, "tg://"))
        if tasks:
            await asyncio.gather(*tasks)

    except Exception as e:
        logging.exception("处理消息失败: %s", e)


async def main():
    if not TG_API_ID or not TG_API_HASH:
        raise RuntimeError("请先在 .env 里配置 TG_API_ID 和 TG_API_HASH")

    if not BARK_KEY and not SC3_SENDKEY:
        raise RuntimeError("请先在 .env 里配置 BARK_KEY 或 SC3_SENDKEY")

    logging.info("启动 Telegram -> 推送监听程序")
    logging.info("Bark 推送: %s (远程: %s)", "已配置" if BARK_KEY and BARK_ENABLED else "未配置",
                 "开启" if is_bark_enabled() else "关闭")
    logging.info("Server酱³ 推送: %s (远程: %s)", "已配置" if SC3_SENDKEY and SC3_ENABLED else "未配置",
                 "开启" if is_sc3_enabled() else "关闭")

    await client.start()

    me = await client.get_me()
    logging.info(
        "已登录 Telegram: id=%s username=%s",
        me.id,
        getattr(me, "username", None),
    )

    await client.run_until_disconnected()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
