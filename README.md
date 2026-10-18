# Arkham Night · 阿卡姆夜桌

一张放在自己电脑上的 d100 调查跑团桌，适合 1920 年代那种恐怖调查风格的故事。
骰子由服务器来掷，谁都改不了；记录、角色卡、线索札记都按存档分开保存。

做它的初衷，是**跟 AI 一起跑团**：AI 当守密人，AI 当你的队友，或者两样都是 AI。
真人和真人一起玩当然也可以。

> 非官方同人作品，与 Chaosium Inc. 无关。说明见文末「版权与声明」。

---

## 能做什么

- **首页**：开始新游戏、读取存档（每格显示场景小图、调查员状态、最后一段旁白）、规则说明、设置
- **桌子**
  - 剧情记录，分角色发言、场外和守密人旁白
  - d100 检定会自动判定等级：大成功、极难、困难、成功、失败、大失败；支持奖励骰和惩罚骰
  - 自由掷骰，比如 `1d6+1`
  - 守密人可以掷暗骰：结果只写进守密人的抽屉，公开记录里只显示「守密人掷了一次骰子」
  - 角色卡：HP、MP、SAN 的格子条，技能点一下就是一次检定
  - 📓 调查札记，记重要线索用
  - 🔔 行动确认：调查员都说完了就按一下，告诉守密人可以推进了
  - 📋 复制给守密人：守密人在聊天窗口里、碰不到这个页面时，用它把新进展复制过去
  - 🛟 叫停：任何人按下去，整桌立刻停下，不问理由
- **背景音乐和雨声**：默认关着，在设置里开
- **手机**：同一个 Wi-Fi 下可以用手机玩（见「安全」一节）

只需要 Python 3，不用装任何依赖。

---

## 快速开始

```sh
python3 server.py
```

浏览器打开 <http://127.0.0.1:8742>，点 **开始新游戏**，给存档起个名字，就进到桌子里了。

右上角「我是」选你坐的位置：`调查员 A`、`调查员 B` 或者 `守密人`。
（这只是选座位，不是登录，谁都能选任何位置。）

---

## 怎么跟 AI 一起玩

桌上有三个座位：两个调查员（`player1`、`player2`），一个守密人（`keeper`）。下面是几种常见的坐法：

### 玩法一：同一个 AI，开两个窗口

- **窗口 1 当守密人**：负责剧本、NPC、怪物、要不要掷骰、讲结果
- **窗口 2 当你的队友**：作为另一个调查员，跟你一起行动
- **你**：坐 `player1`

两个窗口各管各的，互不知道对方脑子里想什么，守密人的秘密就藏得住。

### 玩法二：两个不同的 AI

比如一个 Claude 当队友、一个 GPT 当守密人，或者反过来。
不同的 AI 讲故事的味道不一样，组合起来会很好玩。

### 玩法三：AI 只当守密人

你和朋友两个人当调查员，AI 主持。

### AI 怎么上桌

**能在你电脑上跑命令的 AI**（Claude Code、Codex 这类）可以直接用 `table.sh` 读记录、发言、掷骰，跟你在网页上看到的是同一张桌子。

**只能聊天的 AI**（网页版聊天这类）碰不到这个页面，那就由你来传话：

1. 轮到守密人的时候，点 **📋 复制给守密人**，把内容贴给它
2. 它回了旁白以后，把右上角「我是」切到「守密人」，把它的话贴进来发送，再切回自己

### 轮次怎么走

AI 不会自己醒，**每一轮都要有人叫它**。一般是这样：

1. 守密人发一段旁白
2. 两个调查员各说各的行动。AI 队友那边，你跟它说一声「到你了」
3. 都说完了，按一下 🔔
4. 去叫守密人：「到你了」。它读完新记录，推进剧情

🔔 只是在页面上亮一下，告诉大家「可以推进了」，**不会**自动去通知任何人。

### 可以直接贴给 AI 的开场说明

给 **守密人**：

> 我们在玩一场 d100 调查跑团，你当守密人。桌子在我电脑上：`<项目路径>`，用 `./table.sh` 上桌，用法写在这个文件开头。你的座位是 `keeper`。
> 每次我说「到你了」，你先 `./table.sh read <上次读到的编号>`，只读新的记录，然后用 `./table.sh keeper say "…"` 写旁白；需要调查员掷骰时，说清楚掷什么技能、有没有奖励骰。
> 剧本和笔记放在 `keeper/` 里，那是你的抽屉，调查员不看。暗骰用 `./table.sh keeper hidden 技能 目标值`。
> 恐怖程度：（自己填，比如「中，血腥细节一笔带过」）。任何人按下 🛟 叫停，就先停下来顾人。

给 **AI 队友**：

> 我们在玩一场 d100 调查跑团，你是调查员 B（座位 `player2`），我是调查员 A。桌子在 `<项目路径>`，用 `./table.sh` 上桌。
> 每次我说「到你了」，你先 `./table.sh read <上次读到的编号>`，只读新的记录，然后用 `./table.sh player2 say "…"` 说你的角色要做什么。守密人让你掷骰时，用 `./table.sh player2 check 技能 目标值`。
> 重要线索可以用 `./table.sh player2 note "…"` 记进札记。
> 🔴 不要读 `keeper/` 文件夹，也不要去找剧本原文，那等于偷看答案。

只能聊天的 AI，把命令那几句换成「我会把桌上的新进展贴给你」就行。

### 防剧透

- `keeper/` 是守密人的抽屉，调查员（包括 AI 队友）说好不看。
- 不同的桌子用不同的存档。命令行默认操作的是「当前存档」，也就是首页最后点开的那个；要指定，就设 `ARKHAM_NIGHT_SAVE=<存档id>`。`./table.sh saves` 可以列出全部存档。
- 同一个守密人窗口最好别同时带两桌，剧情容易串。

---

## 捏角色

新存档里的角色卡是空的。属性可以这样掷：

| 属性 | 怎么掷 |
|---|---|
| 力量、体质、敏捷、外貌、意志 | `3d6` × 5 |
| 体型、智力、教育 | `2d6+6` × 5 |
| 幸运 | `3d6` × 5 |

- HP = (体质 + 体型) ÷ 10
- MP = 意志 ÷ 5
- 理智 = 意志

卡上有 `3d6`、`2d6+6` 两个快捷骰子。数值填好后，点角色卡右上角的 **改**，按文本格式改名字、职业和技能。也可以直接让 AI 队友帮你填，它用 `table.sh` 改起来更顺手。

---

## 换成你自己的样子

### 名字和颜色

改项目根目录下的 `players.json`，改完重启服务器：

```json
{
  "player1": { "name": "调查员 A", "color": "#f2a6c8", "avatar": "/assets/avatar-player1.png" },
  "player2": { "name": "调查员 B", "color": "#7fb8ff", "avatar": "/assets/avatar-player2.png" },
  "keeper":  { "name": "守密人",   "color": "#b9a3ff" }
}
```

`avatar` 写 `null` 就不显示头像。

### 图

`assets/` 里的图都是**默认图**，想换就用同名文件替换：

| 文件 | 用在哪 |
|---|---|
| `home.png` | 首页整张图，按钮是画在图上的 |
| `backdrop-mansion.webp` | 桌子页面的背景 |
| `scene-*.webp`、`scene-harbor.png` | 守密人切换的场景图，也用作存档缩略图（见下表） |
| `avatar-player1.png`、`avatar-player2.png` | 两位调查员的默认头像 |

⚠ 首页的按钮是在 `home.png` 上盖了一层看不见的真按钮，位置写在 `home.html` 里（`#bNew` 等，用百分比定位）。换了首页图，要跟着挪这几个百分比，不然点不准。

守密人可以选的场景（命令行里写英文名，网页上是下拉框）：

| 名字 | 画面 | 文件 |
|---|---|---|
| `office` | 侦探事务所 | `scene-office.webp` |
| `street` | 雨夜街道 | `scene-street.webp` |
| `library` | 图书馆 / 档案室 | `scene-library.webp` |
| `hall` | 市政厅 | `scene-hall.webp` |
| `chapel` | 教堂废墟 | `scene-chapel.webp` |
| `house` | 老宅外观 | `scene-house.webp` |
| `parlor` | 老宅客厅 | `scene-parlor.webp` |
| `corridor` | 二楼走廊 | `scene-corridor.webp` |
| `basement` | 地下室 | `scene-basement.webp` |
| `lamp` | 黑暗中的一盏灯 | `scene-lamp.webp` |
| `harbor` | 港口 | `scene-harbor.png` |
| `table` | 桌边烛光 | 代码现画的像素画 |
| `dark` | 黑暗中的红眼 | 代码现画的像素画 |

想加新场景：把图放进 `assets/`，再在 `index.html` 的 `SCENE_IMG`、`home.html` 的 `ART` 和守密人下拉框里各加一行。

### 音乐

在 `assets/` 里，替换同名文件就行。默认的四首都是 CC0，见文末。

---

## 安全

- **没有密码，也没有登录。**默认只开在 `127.0.0.1`，只有你自己这台电脑能打开。
- 想用手机玩，可以用 `ARKHAM_NIGHT_HOST=0.0.0.0 python3 server.py` 开到局域网上。这时候**同一个网络里的任何人**都能打开、能选守密人座位、能看到除暗骰以外的全部内容。只在信得过的家庭网络里这么做，**绝对不要开到公网上**。
- 🛟 叫停是给人用的：玩着不舒服了，就按。开局前最好也约一个口头的安全词。

### 环境变量

| 变量 | 默认值 | 作用 |
|---|---|---|
| `ARKHAM_NIGHT_PORT` | `8742` | 端口 |
| `ARKHAM_NIGHT_HOST` | `127.0.0.1` | 监听地址 |
| `ARKHAM_NIGHT_ROOT` | 脚本所在目录 | 数据和页面从哪里读 |
| `ARKHAM_NIGHT_URL` | `http://127.0.0.1:8742` | `table.sh` 连哪个服务器 |
| `ARKHAM_NIGHT_SAVE` | （当前存档） | `table.sh` 操作哪个存档 |

存档在 `data/saves/` 里，都是普通的 JSON 文件。要删存档，删掉对应的文件夹就行。

---

## 版权与声明

**本项目是独立的非商业同人作品，与 Chaosium Inc. 无关，未经其出版、认可或批准。** *Call of Cthulhu*（克苏鲁的呼唤）是 Chaosium Inc. 的注册商标。本项目不含 Chaosium 的规则原文、模组、美术或标志；骰子判定是我们自己写的，规则说明也是用自己的话写的。想了解 Chaosium 的产品，请访问 [chaosium.com](https://www.chaosium.com)。想玩完整的游戏，请支持正版规则书。

- **代码**：MIT，见 [LICENSE](LICENSE)
- **音乐**：全部是 [OpenGameArt.org](https://opengameart.org) 上的 CC0 作品
  - *Moil*：Ruskerdax（首页）
  - *8-bit Curious Theme*：emanresU（桌子默认曲）
  - *Contemplation*：Joth（桌子可选曲）
  - *Dark Rainy Night (ambience)*：kindland（雨声）
- **字体**：Cinzel、Noto Serif SC、DotGothic16、Silkscreen，都通过 Google Fonts 加载，都是 SIL OFL 授权
- **默认美术**：为本项目制作（AI 生成），跟代码一起提供，随便用，也随便换

---

## English

**Arkham Night** is a small, self-hosted table for d100 investigation-horror tabletop games, built for playing *with AI*: an AI keeper, an AI teammate, or both. Humans work fine too.

- Run `python3 server.py` (Python 3 only, no dependencies), then open <http://127.0.0.1:8742>.
- Three seats: `player1`, `player2` (investigators) and `keeper`. AIs that can run shell commands (Claude Code, Codex…) join through `./table.sh`. For chat-only AIs, use the 📋 copy button and paste their replies back.
- Server-side dice (Python `secrets`). Graded d100 checks with bonus/penalty dice, hidden keeper rolls, character sheets, a clue notebook, a turn-ready bell, a safety-pause button, and save slots.
- **No authentication.** It binds to `127.0.0.1` by default. Only use `ARKHAM_NIGHT_HOST=0.0.0.0` on a network you trust, and never on the internet.
- Names, colours and avatars live in `players.json`. All art in `assets/` is a default you can swap out.

*Unofficial fan project. Not affiliated with, published, endorsed, or specifically approved by Chaosium Inc. Call of Cthulhu is a registered trademark of Chaosium Inc. No Chaosium rules text, scenarios, art or logos are included.* Code: MIT. Music: CC0 from OpenGameArt.org (Ruskerdax, emanresU, Joth, kindland). Default art: made for this project (AI-generated), offered alongside the code.
