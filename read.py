#!/usr/bin/env python3
"""table.sh read 的格式化：把 /api/state 打印成人读的样子。"""
import json
import sys

s = json.load(sys.stdin)
N = {k: v["name"] for k, v in s.get("players", {}).items()}
if sys.argv[1:] == ["--saves"]:
    for v in s["saves"]:
        mark = "*" if v["current"] else " "
        print(f"{mark} {v['id']:<22} {v['name']} ｜ {v['scene'].get('title', '')} ｜ "
              f"{v['entries']} 条 ｜ {(v['updated'] or '')[:16]}")
    sys.exit(0)
if "error" in s:
    sys.exit(s["error"])
log = s["log"]
if len(sys.argv) < 2 or not sys.argv[1]:
    log = log[-20:]
for e in log:
    w = N.get(e.get("who"), "")
    t = e["type"]
    if t == "check":
        line = f"🎲 {e['label']}({e['target']}) → {e['result']} {e['grade_name']}"
    elif t == "dice":
        line = f"🎲 {e['label']} {e['expr']} → {e['total']} {e['rolls']}"
    elif t == "san":
        line = f"🧠 {N.get(e['target'], e['target'])} 理智 {e['from']}→{e['to']}"
    else:
        line = e.get("text", "")
    print(f"#{e['id']} [{t}] {w}: {line}")
print("---")
paused = " | 暂停中" if s["table"].get("paused") else ""
print(f"场景: {s['scene'].get('title')} | {s['scene'].get('place')}{paused}")
turn = s.get("turn", {})
if turn.get("status") == "ready":
    print(f"🔔 等待守密人：调查员已确认行动（{N.get(turn.get('by'), turn.get('by', ''))} 按铃）")
for k in ("player1", "player2"):
    c = s["sheets"][k]
    print(f"{N.get(k, k)}: {c['name'] or '(未命名)'} HP {c['hp'][0]}/{c['hp'][1]} SAN {c['san'][0]} 幸运 {c['luck']}")
