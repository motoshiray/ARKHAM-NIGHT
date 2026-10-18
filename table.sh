#!/usr/bin/env bash
# 命令行上桌：给不方便用网页的人（比如在终端里主持的守密人）。
#   ./table.sh <who> say "文字"            角色发言（守密人发的是旁白）
#   ./table.sh <who> ooc "文字"            场外
#   ./table.sh <who> check 侦查 60 [奖惩]   d100 检定，奖惩 = 1/2 或 -1/-2
#   ./table.sh <who> dice 1d6+1 [说明]      普通掷骰
#   ./table.sh keeper hidden 聆听 40        守密人暗骰（结果只进 keeper/）
#   ./table.sh keeper scene 标题 地点 画面   画面：office street library hall chapel house parlor corridor basement lamp harbor（插画）｜table dark（像素小画）
#   ./table.sh <who> san <player1|player2> 45   改理智当前值
#   ./table.sh <player1|player2> note "线索"     往调查札记里记一条
#   ./table.sh <player1|player2> unnote 3        删掉第 3 条札记
#   ./table.sh read [从第几条之后]           读记录（默认最近 20 条）
#   ./table.sh saves                        列出所有存档（* 是当前存档）
# who：player1 / player2 / keeper（显示名字在 players.json 里改）
# 默认操作「当前存档」（首页最后点开的那个）；要指定就设 ARKHAM_NIGHT_SAVE=<存档id>
set -euo pipefail
URL="${ARKHAM_NIGHT_URL:-http://127.0.0.1:8742}"
SAVE="${ARKHAM_NIGHT_SAVE:-}"
j() { python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"; }
p() {
  local body="$2"
  [ -n "$SAVE" ] && body="${body%\}},\"save\":\"$SAVE\"}"
  curl -s -X POST "$URL$1" -H 'Content-Type: application/json' -d "$body"; echo
}

if [ "${1:-}" = "read" ]; then
  since="${2:-}"
  curl -s "$URL/api/state?since=${since:-0}&save=$SAVE" | python3 "$(dirname "$0")/read.py" "$since"
  exit 0
fi
if [ "${1:-}" = "saves" ]; then
  curl -s "$URL/api/saves" | python3 "$(dirname "$0")/read.py" --saves
  exit 0
fi

who="$1"; cmd="$2"; shift 2
case "$cmd" in
  say)    kind=say; [ "$who" = keeper ] && kind=narrate
          p /api/say "{\"who\":\"$who\",\"kind\":\"$kind\",\"text\":$(j "$1")}" ;;
  ooc)    p /api/say "{\"who\":\"$who\",\"kind\":\"ooc\",\"text\":$(j "$1")}" ;;
  check)  p /api/roll "{\"who\":\"$who\",\"label\":$(j "$1"),\"target\":$2,\"bonus\":${3:-0}}" ;;
  hidden) p /api/roll "{\"who\":\"$who\",\"label\":$(j "$1"),\"target\":$2,\"hidden\":true}" ;;
  dice)   p /api/roll "{\"who\":\"$who\",\"expr\":$(j "$1"),\"label\":$(j "${2:-掷骰}")}" ;;
  scene)  p /api/scene "{\"who\":\"$who\",\"title\":$(j "$1"),\"place\":$(j "${2:-}"),\"art\":$(j "${3:-house}")}" ;;
  note)   p /api/note "{\"who\":\"$who\",\"text\":$(j "$1")}" >/dev/null && echo noted ;;
  unnote) p /api/note "{\"who\":\"$who\",\"delete\":$1}" >/dev/null && echo removed ;;
  san)    p /api/sheet "{\"who\":\"$who\",\"target\":\"$1\",\"patch\":{\"san\":[$2,99]}}" ;;
  *) echo "不认识：$cmd"; exit 1 ;;
esac
