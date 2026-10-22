import json
from pathlib import Path

HISTORY_PATH = Path(__file__).resolve().parent / "session.json"

#保存会话历史
def save_session(messages, summary_cache):
    text = json.dumps(
        {
            "messages": messages,
            "summary_cache": summary_cache,
        },
        ensure_ascii=False,
        indent=2,
    )

    temp_path = HISTORY_PATH.with_suffix(".tmp") #原子写入

    try:
        temp_path.write_text(text,encoding="utf-8")
        temp_path.replace(HISTORY_PATH)
    except OSError as error:
        print(f"会话历史保存失败，本轮内容不会被记忆：{error}")

#读取会话历史
def load_session():
    if not HISTORY_PATH.exists():
        return [], {"summary": None, "next_message_index": 1}

    try:
        text = HISTORY_PATH.read_text(encoding="utf-8")
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
def clear_session():
    if HISTORY_PATH.exists():
        HISTORY_PATH.unlink()

    print("会话历史已清除")
