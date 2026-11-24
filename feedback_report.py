"""Summarise the 👍/👎 ratings visitors gave to answers (feedback/feedback.jsonl)."""

import json

from app import FEEDBACK_FILE


def main():
    if not FEEDBACK_FILE.exists():
        print("還沒有任何回饋。")
        return
    records = [json.loads(line) for line in FEEDBACK_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    up = sum(1 for item in records if item["rating"] == "up")
    down = len(records) - up
    print(f"共 {len(records)} 則回饋：👍 {up}、👎 {down}（有幫助比例 {up / len(records):.0%}）")
    if down:
        print("\n被按 👎 的問題：")
        for item in records:
            if item["rating"] == "down":
                print(f"- [{item['time'][:16].replace('T', ' ')}] {item['question']}")


if __name__ == "__main__":
    main()
