import json
from pathlib import Path

RUN_LOG_PATH = Path(__file__).resolve().parent / "runs.jsonl"

def append_run_record(record: dict) -> None:
    try:
        run_record = json.dumps(record, ensure_ascii=False)
        with RUN_LOG_PATH.open("a", encoding="utf-8") as file:
            file.write(run_record + "\n")

    except OSError as error:
        print(f"运行记录保存失败：{error}")