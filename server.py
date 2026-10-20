#!/usr/bin/env python3
"""Arkham Night：一张本地的 d100 调查跑团桌。

一张桌子，三个座位：两名调查员（player1、player2）和一名守密人（keeper）。
显示名字在 players.json 里改。
骰子由服务器掷（secrets），谁都改不了结果。

每个存档一个文件夹 data/saves/<id>/：
  meta.json     存档名、创建/更新时间
  log.jsonl     公开记录，一行一条
  sheets.json   角色卡
  scene.json    当前场景
  table.json    桌面状态（是否因安全暂停而停下）
  turn.json     行动确认铃（调查员确认后等守密人接手）
  notes.json    调查札记
data/current.txt 记着「当前存档」：请求没带 save 时就用它（table.sh 靠这个）。
keeper/ 是守密人的抽屉：暗骰按存档分在 keeper/<id>/ 下，不经任何接口返回。

没有登录、没有密码：只在你信任的本地环境里用。
"""
import json
import os
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(os.environ.get("ARKHAM_NIGHT_ROOT", Path(__file__).resolve().parent)).resolve()
DATA = ROOT / "data"
SAVES = DATA / "saves"
KEEPER = ROOT / "keeper"
PORT = int(os.environ.get("ARKHAM_NIGHT_PORT", "8742"))
# 默认只听本机。设成 0.0.0.0 会让同一网络里的任何人都能连上——没有任何认证。
HOST = os.environ.get("ARKHAM_NIGHT_HOST", "127.0.0.1")

INVESTIGATORS = ("player1", "player2")
KEEPER_ID = "keeper"
SAVE_RE = re.compile(r"^[a-z0-9-]{1,40}$")
LOCK = threading.RLock()

SAVES.mkdir(parents=True, exist_ok=True)
KEEPER.mkdir(exist_ok=True)


def load_players():
    """座位是固定的三个；players.json 只决定显示名字、颜色和（可选）头像。"""
    players = {
        "player1": {"name": "调查员 A", "role": "investigator", "color": "#f2a6c8", "avatar": "/assets/avatar-player1.png"},
        "player2": {"name": "调查员 B", "role": "investigator", "color": "#7fb8ff", "avatar": "/assets/avatar-player2.png"},
        "keeper": {"name": "守密人", "role": "keeper", "color": "#b9a3ff"},
    }
    try:
        custom = json.loads((ROOT / "players.json").read_text("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        custom = {}
    for k, v in players.items():
        c = custom.get(k) if isinstance(custom, dict) else None
        if isinstance(c, dict):
            if isinstance(c.get("name"), str) and c["name"].strip():
                v["name"] = c["name"].strip()[:30]
            if isinstance(c.get("color"), str) and re.fullmatch(r"#[0-9a-fA-F]{3,8}", c["color"]):
                v["color"] = c["color"]
            # 可选头像：放进 assets/ 的图片，比如 "/assets/avatar-player1.png"；找不到图时网页会直接不显示。
            if isinstance(c.get("avatar"), str) and re.fullmatch(r"/assets/[\w.-]+\.(png|webp|jpg)", c["avatar"]):
                v["avatar"] = c["avatar"]
            elif "avatar" in c and not c["avatar"]:   # "avatar": null 或 "" = 不要头像
                v.pop("avatar", None)
    return players


PLAYERS = load_players()


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def read_json(path, default):
    try:
        return json.loads(path.read_text("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), "utf-8")
    tmp.replace(path)


# ---------- 存档 ----------

def current_save():
    try:
        s = (DATA / "current.txt").read_text("utf-8").strip()
        if SAVE_RE.match(s) and (SAVES / s).is_dir():
            return s
    except FileNotFoundError:
        pass
    return None


def save_dir(save):
    save = save or current_save()
    if not save or not SAVE_RE.match(save) or not (SAVES / save).is_dir():
        raise ValueError("没有这个存档")
    return SAVES / save


def touch(sd):
    meta = read_json(sd / "meta.json", {})
    meta["updated"] = now()
    write_json(sd / "meta.json", meta)


def read_log(sd, since=0):
    out = []
    try:
        with (sd / "log.jsonl").open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("id", 0) > since:
                    out.append(e)
    except FileNotFoundError:
        pass
    return out


def append(sd, entry):
    """调用方要先拿 LOCK。"""
    entry.setdefault("at", now())
    log = read_log(sd)
    entry["id"] = (log[-1]["id"] + 1) if log else 1
    with (sd / "log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    touch(sd)
    return entry


def append_hidden(sd, entry):
    kd = KEEPER / sd.name
    kd.mkdir(exist_ok=True)
    entry.setdefault("at", now())
    with (kd / "hidden_rolls.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def turn_state(sd):
    """公开的行动确认铃：调查员确认后，等守密人接手这一轮。"""
    raw = read_json(sd / "turn.json", {"status": "idle"})
    return {k: raw[k] for k in ("status", "by", "at", "after", "eventId") if k in raw}


def clear_turn(sd):
    write_json(sd / "turn.json", {"status": "idle"})


def save_summary(sd):
    meta = read_json(sd / "meta.json", {})
    log = read_log(sd)
    scene = read_json(sd / "scene.json", {"title": "开场之前", "place": "桌边", "art": "table"})
    sheets = load_sheets(sd)
    last = next((e["text"] for e in reversed(log) if e.get("type") == "narrate"), "")
    return {
        "id": sd.name,
        "name": meta.get("name", sd.name),
        "cast": meta.get("cast", ""),
        "module": module_brief(meta.get("module", "")),
        "created": meta.get("created"),
        "updated": meta.get("updated"),
        "scene": scene,
        "entries": len(log),
        "notes": len(read_json(sd / "notes.json", [])),
        "investigators": [{"who": k, "name": sheets[k]["name"], "hp": sheets[k]["hp"], "san": sheets[k]["san"]}
                          for k in INVESTIGATORS],
        "last": last[:120],
        "current": sd.name == current_save(),
    }


def load_modules():
    """modules.json：可选的模组（剧本）目录。只放玩家可知的信息；剧本本身放 keeper/modules/<id>/ 给守密人。"""
    mods = read_json(ROOT / "modules.json", [])
    return [m for m in mods if isinstance(m, dict) and SAVE_RE.match(str(m.get("id", "")))]


def module_brief(mid):
    for m in load_modules():
        if m["id"] == mid:
            return {"id": m["id"], "name": m.get("name", m["id"]), "cover": m.get("cover", "")}
    return None


def list_saves():
    out = [save_summary(p) for p in SAVES.iterdir() if p.is_dir() and SAVE_RE.match(p.name)]
    out.sort(key=lambda s: s.get("updated") or "", reverse=True)
    return out


def handle_saves(body):
    action = body.get("action")
    with LOCK:
        if action == "create":
            name = str(body.get("name", "")).strip()[:40] or "新的调查"
            module = str(body.get("module", "")).strip()
            if module and not module_brief(module):
                raise ValueError("没有这个模组")
            sid = "s" + time.strftime("%Y%m%d-%H%M%S")
            sd = SAVES / sid
            sd.mkdir()
            write_json(sd / "meta.json", {"name": name, "created": now(), "updated": now(),
                                          "cast": str(body.get("cast", "")).strip()[:60],
                                          "module": module})
            (DATA / "current.txt").write_text(sid, "utf-8")
            return save_summary(sd)
        if action == "select":
            sd = save_dir(body.get("id"))
            (DATA / "current.txt").write_text(sd.name, "utf-8")
            return save_summary(sd)
        if action == "rename":
            sd = save_dir(body.get("id"))
            meta = read_json(sd / "meta.json", {})
            meta["name"] = str(body.get("name", "")).strip()[:40] or meta.get("name", sd.name)
            write_json(sd / "meta.json", meta)
            return save_summary(sd)
    raise ValueError("没有这个存档操作")


# ---------- 骰子 ----------

def d(n):
    return secrets.randbelow(n) + 1


def roll_d100(bonus=0):
    """bonus > 0 奖励骰，< 0 惩罚骰。返回 (结果, 明细)。"""
    ones = d(10) % 10
    tens = [d(10) % 10 for _ in range(1 + abs(bonus))]
    cands = []
    for t in tens:
        v = t * 10 + ones
        cands.append(100 if v == 0 else v)
    if bonus > 0:
        result = min(cands)
    elif bonus < 0:
        result = max(cands)
    else:
        result = cands[0]
    return result, {"tens": tens, "ones": ones, "candidates": cands}


def grade(result, target):
    if result == 1:
        return "critical", "大成功"
    fumble = 100 if target >= 50 else 96
    if result >= fumble:
        return "fumble", "大失败"
    if result <= target // 5:
        return "extreme", "极难成功"
    if result <= target // 2:
        return "hard", "困难成功"
    if result <= target:
        return "regular", "成功"
    return "fail", "失败"


DICE_RE = re.compile(r"^\s*(\d*)d(\d+)\s*(([+-])\s*(\d+))?\s*$", re.I)


def roll_expr(expr):
    """'1d6'、'2d6+1'、'1d10-1'、纯数字。"""
    expr = str(expr).strip()
    if expr.isdigit():
        return int(expr), [int(expr)]
    m = DICE_RE.match(expr)
    if not m:
        raise ValueError(f"看不懂的骰子：{expr}")
    n = int(m.group(1) or 1)
    faces = int(m.group(2))
    if not (1 <= n <= 20 and 2 <= faces <= 1000):
        raise ValueError("骰子太多或太大")
    rolls = [d(faces) for _ in range(n)]
    mod = int(m.group(5) or 0) * (-1 if m.group(4) == "-" else 1)
    return sum(rolls) + mod, rolls


# ---------- 角色卡 ----------

def default_sheet(who):
    return {
        "name": "",
        "occupation": "",
        "hp": [10, 10],
        "mp": [10, 10],
        "san": [50, 99],
        "luck": 50,
        "skills": {"侦查": 25, "聆听": 20, "图书馆使用": 20, "心理学": 10, "闪避": 20, "斗殴": 25},
        "notes": "",
    }


def load_sheets(sd):
    s = read_json(sd / "sheets.json", {})
    for k in INVESTIGATORS:
        s.setdefault(k, default_sheet(k))
    return s


# ---------- 处理 ----------

def handle(path, body):
    if path == "/api/saves":
        return handle_saves(body)

    sd = save_dir(body.get("save"))
    who = body.get("who")
    if path not in ("/api/table",) and who not in PLAYERS:
        raise ValueError("who 只能是 " + " / ".join(PLAYERS))

    if path == "/api/say":
        text = str(body.get("text", "")).strip()
        if not text:
            raise ValueError("说点什么")
        kind = body.get("kind", "say")
        if kind not in ("say", "ooc", "narrate"):
            kind = "say"
        if kind == "narrate" and who != KEEPER_ID:
            kind = "say"
        with LOCK:
            entry = append(sd, {"type": kind, "who": who, "text": text[:4000]})
            # 守密人公开回应后，说明这一轮已经接住；下一次确认可以重新响铃。
            if who == KEEPER_ID:
                clear_turn(sd)
            return entry

    if path == "/api/turn-ready":
        if who not in INVESTIGATORS:
            raise ValueError("只有调查员可以确认行动")
        with LOCK:
            if read_json(sd / "table.json", {"paused": False}).get("paused"):
                raise ValueError("桌子暂停中，先照顾好人；故事会在这里等着。")
            turn = turn_state(sd)
            if turn.get("status") == "ready":
                return turn
            latest = read_log(sd)
            entry = append(sd, {"type": "turn_ready", "who": who,
                                "text": "调查员行动已确认；等待守密人主持。"})
            turn = {
                "status": "ready",
                "by": who,
                "at": entry["at"],
                "after": latest[-1].get("id", 0) if latest else 0,
                "eventId": entry["id"],
            }
            write_json(sd / "turn.json", turn)
            return turn

    if path == "/api/roll":
        label = str(body.get("label", "")).strip()[:40] or "检定"
        hidden = bool(body.get("hidden")) and who == KEEPER_ID
        with LOCK:
            if body.get("expr"):
                total, rolls = roll_expr(body["expr"])
                entry = {"type": "dice", "who": who, "label": label,
                         "expr": body["expr"], "total": total, "rolls": rolls}
            else:
                target = int(body.get("target", 0))
                if not 1 <= target <= 99:
                    raise ValueError("目标值要在 1–99")
                bonus = max(-2, min(2, int(body.get("bonus", 0))))
                result, detail = roll_d100(bonus)
                g, gname = grade(result, target)
                entry = {"type": "check", "who": who, "label": label, "target": target,
                         "bonus": bonus, "result": result, "grade": g, "grade_name": gname,
                         "detail": detail}
            if hidden:
                append_hidden(sd, dict(entry))
                return append(sd, {"type": "hidden", "who": who, "text": "守密人在幕后掷了一次骰子……"})
            return append(sd, entry)

    if path == "/api/sheet":
        target = body.get("target", who)
        if target not in INVESTIGATORS:
            raise ValueError("只有调查员有角色卡")
        if who != KEEPER_ID and who != target:
            raise ValueError("只能改自己的卡（守密人除外）")
        patch = body.get("patch") or {}
        with LOCK:
            sheets = load_sheets(sd)
            sheet = sheets[target]
            before_san = sheet["san"][0]
            for k, v in patch.items():
                if k == "skills" and isinstance(v, dict):
                    for sk, sv in v.items():
                        if sv is None:
                            sheet["skills"].pop(sk, None)
                        else:
                            sheet["skills"][str(sk)[:20]] = max(0, min(99, int(sv)))
                elif k in ("hp", "mp", "san") and isinstance(v, list) and len(v) == 2:
                    sheet[k] = [max(0, int(v[0])), max(1, int(v[1]))]
                elif k == "luck":
                    sheet[k] = max(0, min(99, int(v)))
                elif k in ("name", "occupation", "notes"):
                    sheet[k] = str(v)[:2000]
            sheets[target] = sheet
            write_json(sd / "sheets.json", sheets)
            touch(sd)
            if sheet["san"][0] != before_san:
                append(sd, {"type": "san", "who": who, "target": target,
                            "from": before_san, "to": sheet["san"][0]})
            return sheet

    if path == "/api/scene":
        if who != KEEPER_ID:
            raise ValueError("场景只有守密人能换")
        scene = {
            "title": str(body.get("title", ""))[:60],
            "place": str(body.get("place", ""))[:60],
            "art": str(body.get("art", "house"))[:20],
            "mood": str(body.get("mood", "calm"))[:20],
            "at": now(),
        }
        with LOCK:
            write_json(sd / "scene.json", scene)
            append(sd, {"type": "scene", "who": who, "text": f"【{scene['title']}】{scene['place']}"})
            clear_turn(sd)
        return scene

    if path == "/api/note":
        # 调查札记：调查员记线索用。text 新增一条；delete 删掉一条
        if who not in INVESTIGATORS:
            raise ValueError("札记是调查员的本子")
        with LOCK:
            notes = read_json(sd / "notes.json", [])
            if body.get("delete"):
                notes = [n for n in notes if n["id"] != int(body["delete"])]
            else:
                text = str(body.get("text", "")).strip()
                if not text:
                    raise ValueError("写点什么")
                nid = max([n["id"] for n in notes], default=0) + 1
                notes.append({"id": nid, "who": who, "text": text[:600], "at": now()})
            write_json(sd / "notes.json", notes)
            touch(sd)
        return notes

    if path == "/api/table":
        # 安全暂停：任何人都能叫停，不问理由。
        action = body.get("action")
        by = who if who in PLAYERS else None
        with LOCK:
            t = read_json(sd / "table.json", {"paused": False})
            if action == "pause":
                t = {"paused": True, "by": by, "at": now()}
                append(sd, {"type": "pause", "who": by, "text": "有人叫停了。整桌停下。"})
            elif action == "resume":
                t = {"paused": False}
                append(sd, {"type": "resume", "who": by, "text": "桌子重新亮起来了。"})
            write_json(sd / "table.json", t)
        return t

    raise ValueError("没有这个接口")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, obj, ctype="application/json; charset=utf-8"):
        data = obj if isinstance(obj, bytes) else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_ranged(self, f, ctype):
        """音频要支持 Range，浏览器才能顺畅地循环和拖动。"""
        data = f.read_bytes()
        size = len(data)
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:
                start, end = size - int(m.group(2)), size - 1
            end = min(end, size - 1)
            chunk = data[start:end + 1]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            chunk = data
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "max-age=3600")
        self.send_header("Content-Length", str(len(chunk)))
        self.end_headers()
        self.wfile.write(chunk)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/home.html"):
            return self.send(200, (ROOT / "home.html").read_bytes(), "text/html; charset=utf-8")
        if u.path in ("/play", "/index.html"):
            return self.send(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
        if u.path.startswith("/assets/"):
            name = u.path[len("/assets/"):]
            f = (ROOT / "assets" / name).resolve()
            types = {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg",
                     ".js": "text/javascript; charset=utf-8", ".mp3": "audio/mpeg", ".ogg": "audio/ogg"}
            if f.parent == (ROOT / "assets").resolve() and f.suffix in types and f.is_file():
                if f.suffix in (".mp3", ".ogg"):
                    return self.send_ranged(f, types[f.suffix])
                return self.send(200, f.read_bytes(), types[f.suffix])
            return self.send(404, {"error": "not found"})
        if u.path == "/api/players":
            return self.send(200, {"players": PLAYERS})
        if u.path == "/api/modules":
            return self.send(200, {"modules": load_modules()})
        if u.path == "/api/saves":
            return self.send(200, {"saves": list_saves(), "current": current_save(), "players": PLAYERS})
        if u.path == "/api/state":
            try:
                sd = save_dir(q.get("save", [None])[0])
            except ValueError as e:
                return self.send(404, {"error": str(e)})
            since = int(q.get("since", ["0"])[0] or 0)
            return self.send(200, {
                "save": save_summary(sd),
                "players": PLAYERS,
                "log": read_log(sd, since),
                "sheets": load_sheets(sd),
                "scene": read_json(sd / "scene.json", {"title": "开场之前", "place": "桌边", "art": "table", "mood": "calm"}),
                "table": read_json(sd / "table.json", {"paused": False}),
                "turn": turn_state(sd),
                "notes": read_json(sd / "notes.json", []),
            })
        self.send(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            self.send(200, {"ok": True, "data": handle(u.path, body)})
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            self.send(400, {"ok": False, "error": str(e)})
        except OSError:
            self.send(503, {"ok": False, "error": "本地存储暂不可用。"})


if __name__ == "__main__":
    print(f"Arkham Night on http://{HOST}:{PORT}", flush=True)
    if HOST not in ("127.0.0.1", "localhost", "::1"):
        print("警告 / WARNING: listening beyond localhost with NO authentication. "
              "Anyone who can reach this port can read and change every save.", flush=True)
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
