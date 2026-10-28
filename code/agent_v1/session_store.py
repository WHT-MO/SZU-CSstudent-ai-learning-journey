import json
import re
from pathlib import Path

HISTORY_PATH = Path(__file__).resolve().parent / "session.json"
SESSION_DIR = Path(__file__).resolve().parent / "sessions"

#多会话选择路径
def get_session_path(session_id: str = "default") -> Path:
    match = re.fullmatch(r"[A-Za-z0-9_-]+", session_id) #检查名字

    if match is None:
        raise ValueError
    elif session_id == "default":
        return HISTORY_PATH
    else:
        return SESSION_DIR / f"session_{session_id}.json"

#保存会话历史
def save_session(messages, summary_cache, session_id="default"):
    history_path = get_session_path(session_id)

    text = json.dumps(
        {
            "messages": messages,
            "summary_cache": summary_cache,
        },
        ensure_ascii=False,
        indent=2,
    )

    temp_path = history_path.with_suffix(".tmp") #原子写入

    try:
        history_path.parent.mkdir(parents=True, exist_ok=True) #创建父目录
        temp_path.write_text(text,encoding="utf-8") #写入文件
        temp_path.replace(history_path)
    except OSError as error:
        print(f"会话历史保存失败，本轮内容不会被记忆：{error}")

#读取会话历史
def load_session(session_id="default"):
    history_path = get_session_path(session_id)

    if not history_path.exists():
        return [], {"summary": None, "next_message_index": 1}

    try:
        text = history_path.read_text(encoding="utf-8")
        history = json.loads(text)
        if isinstance(history, dict):
            messages = history.get("messages")
            summary_cache = history.get("summary_cache")

        elif isinstance(history, list): #兼容无缓存的旧会话
            messages = history
            summary_cache = {"summary": None, "next_message_index": 1}

    except (OSError, json.JSONDecodeError) as error:
        print(f"会话历史读取失败，将从新会话开始：{error}")
        return [],  {"summary": None, "next_message_index": 1}

    if not isinstance(messages, list):
        print("会话历史格式错误，将从新会话开始")
        return [], {"summary": None, "next_message_index": 1}

    return messages, summary_cache

#清除会话历史
def clear_session(session_id="default"):
    history_path = get_session_path(session_id)

    if history_path.exists():
        history_path.unlink()

    print("会话历史已清除")
