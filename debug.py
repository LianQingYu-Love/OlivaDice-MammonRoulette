# -*- encoding: utf-8 -*-
"""
@File      :    debug_ai.py
@Desc      :    恶魔轮盘(MammonRoulette)本地调试脚本.

                无需真实 OlivOS 环境: 通过桩模块模拟机器人与消息事件,
                可直接向插件发送模拟指令, 自由测试插件与AI代码.

用法:
    python debug_ai.py                    # 进入交互式 REPL
    python debug_ai.py --demo             # 演示: 真人对局 + AI自对弈
    python debug_ai.py --train 10         # AI自对弈训练10局
    python debug_ai.py --script demo.txt  # 按脚本文件逐行执行指令
    echo "10001 经典匹配2p" | python debug_ai.py   # 从管道读取指令

REPL 指令:
    <用户ID> <消息内容>           模拟群消息(自动路由到插件), 例: 10001 经典匹配2p
    p <用户ID> <消息内容>         模拟私聊消息
    state [群号]                 查看对局数据(留空列出全部群)
    aiadd [类型] [群号]          向匹配中的对局添加AI(默认类型: 斯蒂芬)
    aigame [类型] [群号]         群内有匹配对局则补满AI开局(人机对战), 否则AI自对弈
    watch [类型] [群号]          同aigame, 并打印AI行动轨迹
    train N                      连续自对弈N局
    model                        查看AI模型状态(局数/ε/回放/模型文件)
    fresh                        删除已训练的AI模型
    py <代码>                    自由执行Python代码(环境已预置常用对象)
    reset                        清空全部对局数据
    help                         查看帮助
    exit / quit                  退出
"""

import argparse
import json
import os
import re
import shutil
import sys
import traceback
import types

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
except Exception:
    pass

# ======================== 全局环境 ========================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
AMORLIB_DIR = os.path.join(PROJECT_ROOT, "OlivOS-AmorLib")
os.chdir(PROJECT_ROOT)

# 本地调试环境专用: comp.py/work.py 使用 "import Core" 绝对导入,
# 真实OlivOS运行时由插件目录路径解析; 此处将 "Core" 代理到
# "MammonRoulette.Core", 避免双重加载导致的组件注册表分裂.
import types as _types  # noqa: E402


class _CoreAlias(_types.ModuleType):
    def __getattr__(self, name):
        import MammonRoulette.Core as _real_core

        return getattr(_real_core, name)


sys.modules.setdefault("Core", _CoreAlias("Core"))

MR = None  # MammonRoulette 模块
PROC = None  # 模拟的 OlivOS Proc
MsgManager = None  # AmorLib.MsgManager

DEFAULT_BOT_HASH = "unity"
DEFAULT_GROUP_ID = "123456789"
DEFAULT_SELF_ID = "10001"


# ======================== 桩模块 ========================
class _MsgPara:
    """模拟 OlivOS 消息段落 (at/text)."""

    def __init__(self, type_, data=None):
        self.type = type_
        self.data = data or {}

    def CQ(self):
        if self.type == "at":
            return "[CQ:at,id={}]".format(self.data.get("id", ""))
        return self.data.get("text", "")


class _MessageTemplet:
    """模拟 OlivOS.messageAPI.Message_templet: 将消息切分为段落列表."""

    def __init__(self, mode, msg):
        self.data = []
        for piece in re.split(r"(\[CQ:at,id=\d+\])", str(msg or "")):
            if not piece:
                continue
            m = re.match(r"\[CQ:at,id=(\d+)\]", piece)
            if m:
                self.data.append(_MsgPara("at", {"id": m.group(1)}))
            else:
                self.data.append(_MsgPara("text", {"text": piece}))
        if not self.data:
            self.data.append(_MsgPara("text", {"text": ""}))


def _format_reply_str(template, t_value, flag_cross=True, flag_split=False):
    """模拟回复词格式化: 将 {tKey} 替换为 t_value 中的值."""
    if template is None:
        return None

    def _repl(m):
        key = m.group(1)
        return str(t_value.get(key, m.group(0)))

    return re.sub(r"\{(\w+)\}", _repl, str(template))


def _install_stubs():
    """将 OlivOS / OlivaDiceCore / OlivaDiceNativeGUI / PIL 桩模块注册到 sys.modules.

    幂等: 已注册过则直接返回.
    """
    if "OlivOS" in sys.modules and getattr(sys.modules["OlivOS"], "_debug_stub", False):
        return

    # region OlivOS
    olivos = types.ModuleType("OlivOS")
    olivos._debug_stub = True
    olivos_messageAPI = types.ModuleType("OlivOS.messageAPI")
    olivos_messageAPI.Message_templet = _MessageTemplet
    olivos.messageAPI = olivos_messageAPI
    sys.modules["OlivOS"] = olivos
    sys.modules["OlivOS.messageAPI"] = olivos_messageAPI
    # endregion

    # region OlivaDiceCore
    core = types.ModuleType("OlivaDiceCore")
    msgCustom = types.ModuleType("OlivaDiceCore.msgCustom")
    msgCustom.dictStrCustomDict = {}
    msgCustom.dictHelpDoc = {}
    msgCustom.dictStrConst = {}
    msgCustom.dictGValue = {}
    msgCustom.dictTValue = {}
    console = types.ModuleType("OlivaDiceCore.console")
    console.dictConsoleSwitch = {"unity": {}}
    console.dictConsoleSwitchTemplate = {"default": {}}
    console.getConsoleSwitchByHash = lambda key, hash_="unity": 1
    console.setConsoleSwitchByHash = lambda key, value, hash_="unity": None
    helpDocData = types.ModuleType("OlivaDiceCore.helpDocData")
    helpDocData.dictHelpDoc = {}
    msgCustomManager = types.ModuleType("OlivaDiceCore.msgCustomManager")
    msgCustomManager.dictTValueInit = lambda event, d: d
    msgCustomManager.formatReplySTR = _format_reply_str
    msgReply = types.ModuleType("OlivaDiceCore.msgReply")
    msgReply.msgIsCommand = lambda msg, prefix: (msg, True)
    crossHook = types.ModuleType("OlivaDiceCore.crossHook")
    crossHook.dictHookList = {"prefix": [".", "/", "#"]}
    ordinaryInviteManager = types.ModuleType("OlivaDiceCore.ordinaryInviteManager")
    ordinaryInviteManager.isInMasterList = lambda *args: False
    userConfig = types.ModuleType("OlivaDiceCore.userConfig")
    userConfig.getUserConfigByKey = lambda **kwargs: True
    userConfig.getUserHash = lambda uid, user_type, platform: uid
    data_mod = types.ModuleType("OlivaDiceCore.data")
    data_mod.bot_info = {}

    for name, sub in (
        ("msgCustom", msgCustom),
        ("console", console),
        ("helpDocData", helpDocData),
        ("msgCustomManager", msgCustomManager),
        ("msgReply", msgReply),
        ("crossHook", crossHook),
        ("ordinaryInviteManager", ordinaryInviteManager),
        ("userConfig", userConfig),
        ("data", data_mod),
    ):
        setattr(core, name, sub)
        sys.modules["OlivaDiceCore.{}".format(name)] = sub
    sys.modules["OlivaDiceCore"] = core
    # endregion

    # region OlivaDiceNativeGUI
    nativeGUI = types.ModuleType("OlivaDiceNativeGUI")
    nativeGUI_msgCustom = types.ModuleType("OlivaDiceNativeGUI.msgCustom")
    nativeGUI_msgCustom.dictStrCustomNote = {}
    nativeGUI_msgCustom.dictConsoleSwitchNote = {}
    nativeGUI.msgCustom = nativeGUI_msgCustom
    sys.modules["OlivaDiceNativeGUI"] = nativeGUI
    sys.modules["OlivaDiceNativeGUI.msgCustom"] = nativeGUI_msgCustom
    # endregion

    # region PIL
    pil = types.ModuleType("PIL")
    pil_image = types.ModuleType("PIL.Image")
    pil_imagetk = types.ModuleType("PIL.ImageTk")
    pil.Image = pil_image
    pil.ImageTk = pil_imagetk
    sys.modules["PIL"] = pil
    sys.modules["PIL.Image"] = pil_image
    sys.modules["PIL.ImageTk"] = pil_imagetk
    # endregion


# ======================== 模拟环境 ========================
class FakeLoggerProc:
    def log(self, level, msg):
        print(msg)


class FakeProc:
    """模拟 OlivOS 的 Proc 对象 (插件主进程)."""

    def __init__(self, bot_hashes=(DEFAULT_BOT_HASH,)):
        self.Proc_data = {"bot_info_dict": {h: {} for h in bot_hashes}}
        self.Proc_info = types.SimpleNamespace(logger_proc=FakeLoggerProc())

    def log(self, level, msg):
        print("[Proc:{}] {}".format(level, msg))


class FakeData:
    """模拟 OlivOS 事件数据."""

    def __init__(self, message, user_id, group_id=None, sender_name="测试员"):
        self.message = message
        self.user_id = user_id
        self.group_id = group_id
        self.host_id = None
        self.sender = {"name": sender_name, "id": user_id}
        self.extend = {}
        self.target_id = None
        self.namespace = "MammonRoulette"
        self.event = ""


class FakeEvent:
    """模拟 OlivOS 的 plugin_event 对象, reply() 收集机器人回复."""

    def __init__(self, message, user_id, group_id=None, sender_name="测试员"):
        self.data = FakeData(message, user_id, group_id, sender_name)
        self.bot_info = types.SimpleNamespace(hash=DEFAULT_BOT_HASH)
        self.base_info = {"self_id": DEFAULT_SELF_ID}
        self.platform = {"platform": "qq"}
        self.plugin_info = {"func_type": "group_message" if group_id else "private_message"}
        self.replies = []

    def reply(self, msg):
        if msg:
            self.replies.append(str(msg))


# ======================== 环境初始化 ========================
def _prepare_paths():
    for p in (PROJECT_ROOT, AMORLIB_DIR):
        if p not in sys.path:
            sys.path.insert(0, p)
    os.chdir(PROJECT_ROOT)


def _ensure_data_dirs():
    """按插件相对路径准备数据目录与默认配置文件 (与 OlivOS 运行时一致)."""
    for rel in (
        os.path.join("plugin", "data", "MammonRoulette", "data"),
        os.path.join("plugin", "data", "MammonRoulette", "data", "ai_model"),
        os.path.join("plugin", "tmp"),
    ):
        os.makedirs(rel, exist_ok=True)
    cfg_path = os.path.join("plugin", "data", "MammonRoulette", "data", "config.ini")
    if not os.path.exists(cfg_path):
        src = os.path.join("MammonRoulette", "data", "config.ini")
        if os.path.exists(src):
            shutil.copyfile(src, cfg_path)
        else:
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write(
                    "[dir]\n"
                    "ai_model_dir = plugin/data/MammonRoulette/data/ai_model/\n"
                    "\n"
                    "[path]\n"
                    "db_path = plugin/data/MammonRoulette/Roulette.db\n"
                    "tmp_game_path = plugin/tmp/MammonRoulette_data.json\n"
                    "\n"
                    "[flags]\n"
                    "debug_flag = 0\n"
                )
        print("[调试] 已生成默认配置文件: {}".format(cfg_path))


def init_env(bot_hashes=(DEFAULT_BOT_HASH,)):
    """安装桩模块并完成插件初始化 (等价于 OlivOS 加载插件的 init_after 流程).

    幂等: 重复调用直接返回已初始化的环境.
    """
    global MR, PROC, MsgManager
    if MR is not None:
        return MR, PROC

    _prepare_paths()
    _ensure_data_dirs()
    _install_stubs()

    import OlivaDiceCore  # noqa: F401
    import MammonRoulette
    from AmorLib import MsgManager as _MsgManager

    for bot_hash in bot_hashes:
        OlivaDiceCore.helpDocData.dictHelpDoc.setdefault(bot_hash, {})

    PROC = FakeProc(bot_hashes)
    fake_event = FakeEvent("", "0", group_id=None)
    MammonRoulette.main.Event.init_after(fake_event, PROC)

    MR = MammonRoulette
    MsgManager = _MsgManager
    print("[调试] 环境初始化完成, 插件已就绪.")
    return MR, PROC


# ======================== 模拟指令 ========================
def send_message(user_id, msg, group_id=None, is_private=False, sender_name=None):
    """模拟一条消息: 构造事件经 MsgManager 与 unity_reply 完整走一遍插件流程.

    :param user_id:     发送者ID (字符串数字)
    :param msg:         消息内容
    :param group_id:    群号, 私聊时传 None
    :param is_private:  True 表示私聊消息
    :return:            机器人回复列表 list[str]
    """
    if MR is None:
        init_env()
    group_id = None if is_private else (group_id or DEFAULT_GROUP_ID)
    event = FakeEvent(
        msg,
        user_id,
        group_id=group_id,
        sender_name=sender_name or "测试员{}".format(user_id),
    )
    msg_manager = MsgManager(event)
    MR.main.unity_reply(event, PROC, msg_manager)
    return event.replies


# ======================== AI 辅助工具 ========================
def ai_import():
    """触发AI定义懒注册, 返回 AIComp."""
    from MammonRoulette.Defs import ai as _defs_ai  # noqa: F401
    from MammonRoulette.Core.comp import AIComp

    return AIComp


def get_stephen():
    AIComp = ai_import()
    if "斯蒂芬" not in AIComp.list():
        return None
    return AIComp.get("斯蒂芬").instance()


def make_msg_manager(user_id, gid):
    if MR is None:
        init_env()
    event = FakeEvent("", user_id, group_id=gid, sender_name="调试员")
    mm = MsgManager(event)
    MR.main.unity_state(mm)
    return mm


def make_ai_game(gid, ai_type="斯蒂芬", trace=False):
    """在指定群号开启一局AI自对弈, 返回对局 dict."""
    from MammonRoulette.Core.comp import AIComp
    from MammonRoulette.Core.work import RegGameWork

    game = {
        "start": False,
        "over": False,
        "expireTime": 0,
        "seats": 2,
        "mode": {
            "name": "经典",
            "points": 50,
            "props": {
                "pool": ["手铐", "锯子", "花生", "巧克力", "香烟", "红牛", "邀请函", "放大镜"],
                "ban": [],
                "limit": 6,
            },
        },
        "data": {
            "ammo_live": 0,
            "ammo_blank": 0,
            "bullet": False,
            "shooter": "",
            "order": [],
            "players": {},
            "modify": {"dmg": 1, "ammo_show": True, "bullet_show": False},
            "prop_event": [],
        },
        "reply": {"info": [], "note": {"ammo": False, "round": False}, "only": ""},
        "tmp": {},
    }
    MR.main.game_data[gid] = game
    mm = make_msg_manager("0", gid)
    RegGameWork.join(mm, "ai_{}_1".format(gid[-4:]), ai_model=ai_type)
    RegGameWork.join(mm, "ai_{}_2".format(gid[-4:]), ai_model=ai_type)

    orig_execute = None
    if trace:
        step = [0]
        from MammonRoulette.Core import comp as comp_mod

        orig_execute = comp_mod.AIComp.execute

        def trace_execute(cls, msg_manager, action):
            data = msg_manager.val["game"]["data"]
            shooter = data["shooter"]
            step[0] += 1
            print(
                "  [第{:>2}步] {} 执行 [{}] hp={} 道具={} 弹药={}/{}".format(
                    step[0],
                    data["players"][shooter]["name"],
                    action,
                    {u: p["hp"] for u, p in data["players"].items() if u in data["order"]},
                    data["players"][shooter]["props"],
                    data["ammo_live"],
                    data["ammo_blank"],
                )
            )
            return orig_execute(msg_manager, action)

        comp_mod.AIComp.execute = classmethod(trace_execute)

    try:
        RegGameWork.start(mm)  # start 会自动触发 AI 行动直至对局结束
    finally:
        if orig_execute is not None:
            from MammonRoulette.Core import comp as comp_mod

            comp_mod.AIComp.execute = orig_execute
    return game


def ai_train(rounds, trace_first=False):
    """AI自对弈N局, 返回(成功局数, 失败局数)."""
    ok, bad = 0, 0
    for n in range(1, rounds + 1):
        gid = "ai_self_{}".format(n)
        try:
            game = make_ai_game(gid, trace=(trace_first and n == 1))
        except Exception:
            traceback.print_exc()
            bad += 1
            continue
        finished = bool(game.get("over")) and len(game["data"]["order"]) <= 1
        if finished:
            ok += 1
        else:
            bad += 1
        print("  第{}局: over={} 幸存者={} {}".format(n, game.get("over"), game["data"]["order"], "OK" if finished else "BAD"))
    return ok, bad


def add_ai_to_game(gid, ai_type="斯蒂芬"):
    """向指定群号中正在匹配的对局添加一名AI, 满员自动开局."""
    from MammonRoulette.Core.work import RegGameWork

    game = MR.main.game_data.get(gid)
    if not game or not game.get("mode") or game.get("start"):
        print("[错误] 该群没有正在匹配的对局.")
        return False
    mm = make_msg_manager("0", gid)
    ai_id = "ai_{}".format(int(os.urandom(3).hex(), 16) % 1000000)
    RegGameWork.join(mm, ai_id, ai_model=ai_type)
    game = MR.main.game_data[gid]
    print("[AI] {} 已加入对局 [{}/{}]".format(ai_type, len(game["data"]["order"]), game["seats"]))
    if len(game["data"]["order"]) >= game["seats"]:
        RegGameWork.start(mm)
        print("[AI] 人数已满, 对局开始.")
    return True


def fill_ai_game(gid, ai_type="斯蒂芬"):
    """若指定群存在匹配中的对局, 用AI补满座位并开局(人机对战).

    :return: 接管成功返回对局 dict, 否则返回 None.
    """
    from MammonRoulette.Core.work import RegGameWork

    game = MR.main.game_data.get(gid)
    if not game or not game.get("mode") or game.get("start"):
        return None
    mm = make_msg_manager("0", gid)
    order = game["data"]["order"]
    seats = game["seats"]
    added = 0
    while len(order) < seats:
        ai_id = "ai_{}".format(int(os.urandom(3).hex(), 16) % 1000000)
        RegGameWork.join(mm, ai_id, ai_model=ai_type)
        added += 1
    print("[AI] 已补入{}名AI, 人数 [{}/{}]".format(added, len(order), seats))
    RegGameWork.start(mm)  # start 会自动触发 AI 行动
    return game


def model_info():
    """打印AI模型状态."""
    ste = get_stephen()
    if ste is None:
        print("[模型] 未注册AI.")
        return
    if not getattr(ste, "_model_ready", False):
        ste.load()  # 懒加载持久化权重
    path = ste.model_path
    print("[模型] 类型: {}".format(ste.name))
    print("[模型] 已学习局数: {}".format(ste.games))
    print("[模型] 探索率ε: {:.4f}".format(ste.eps))
    print("[模型] 经验回放样本: {}".format(len(ste.replay.memory)))
    print("[模型] 网络结构: {}".format(ste.net.sizes))
    print(
        "[模型] 模型文件: {} ({})".format(
            path, "存在, {}KB".format(os.path.getsize(path) // 1024) if os.path.exists(path) else "不存在"
        )
    )


def fresh_model():
    ste = get_stephen()
    if ste is not None and os.path.exists(ste.model_path):
        os.remove(ste.model_path)
        print("[模型] 已删除: {}".format(ste.model_path))
    else:
        print("[模型] 无需清理.")


# ======================== 状态查看 ========================
def print_state(gid=None):
    if gid:
        game = MR.main.game_data.get(gid)
        if not game:
            print("[状态] 群 {} 无对局数据.".format(gid))
            return
        print(json.dumps(game, ensure_ascii=False, indent=2, default=str))
        return
    print(json.dumps(MR.main.game_data, ensure_ascii=False, indent=2, default=str))


# ======================== REPL ========================
def repl_namespace():
    """预置常用对象, 供 py 命令自由使用."""
    from MammonRoulette.Core import comp, work
    from MammonRoulette.Core.comp import ModeComp, PropComp, EffectComp, AIComp
    from MammonRoulette.Core.work import RegGameWork

    return {
        "MR": MR,
        "PROC": PROC,
        "MsgManager": MsgManager,
        "config": __import__("MammonRoulette", fromlist=["config"]).config,
        "ModeComp": ModeComp,
        "PropComp": PropComp,
        "EffectComp": EffectComp,
        "AIComp": AIComp,
        "RegGameWork": RegGameWork,
        "comp": comp,
        "work": work,
        "send_message": send_message,
        "make_msg_manager": make_msg_manager,
        "make_ai_game": make_ai_game,
        "ai_train": ai_train,
        "add_ai_to_game": add_ai_to_game,
        "fill_ai_game": fill_ai_game,
        "get_stephen": get_stephen,
        "DEFAULT_GROUP_ID": DEFAULT_GROUP_ID,
    }


def handle_line(line, ns):
    """解析并执行一行 REPL 指令."""
    line = line.strip()
    if not line or line.startswith("#"):
        return
    low = line.lower()

    # 内部命令
    if low in ("exit", "quit", "q"):
        raise SystemExit(0)
    if low == "help":
        print(__doc__)
        return
    if low == "reset":
        MR.main.game_data.clear()
        print("[调试] 已清空所有对局数据.")
        return
    if low.startswith("state"):
        parts = line.split(" ", 1)
        print_state(parts[1].strip() if len(parts) > 1 else None)
        return
    if low.startswith("model"):
        model_info()
        return
    if low == "fresh":
        fresh_model()
        return
    if low.startswith("train"):
        parts = line.split(" ", 1)
        try:
            n = int(parts[1]) if len(parts) > 1 else 5
        except ValueError:
            n = 5
        ok, bad = ai_train(n)
        print("[训练] 完成: {}局成功, {}局失败.".format(ok, bad))
        model_info()
        return
    if low.startswith("aigame") or low.startswith("watch"):
        trace = low.startswith("watch")
        parts = line.split(" ", 2)
        ai_type = parts[1] if len(parts) > 1 and parts[1] else "斯蒂芬"
        gid = parts[2] if len(parts) > 2 else DEFAULT_GROUP_ID
        try:
            game = fill_ai_game(gid, ai_type)
            if game is not None:
                # 人机对战: AI补满后已开局
                finished = bool(game.get("over")) and len(game["data"]["order"]) <= 1
                if finished:
                    print("[AI] 对局结束: over={} 幸存者={}".format(game.get("over"), game["data"]["order"]))
                else:
                    print("[AI] 人机对局进行中, 请继续用 <用户ID> 开枪/使用道具 等命令推进.")
                return
            # 无匹配中对局: AI自对弈
            gid2 = "ai_watch" if trace else "ai_manual"
            game = make_ai_game(gid2, ai_type=ai_type, trace=trace)
            print("[AI] 对局结束: over={} 幸存者={}".format(game.get("over"), game["data"]["order"]))
        except Exception:
            traceback.print_exc()
        return
    if low.startswith("aiadd"):
        parts = line.split(" ", 2)
        ai_type = parts[1] if len(parts) > 1 and parts[1] else "斯蒂芬"
        gid = parts[2] if len(parts) > 2 else DEFAULT_GROUP_ID
        try:
            add_ai_to_game(gid, ai_type=ai_type)
        except Exception:
            traceback.print_exc()
        return
    if low.startswith("py "):
        code = line[3:].strip()
        try:
            result = eval(code, ns, ns)
            if result is not None:
                print(repr(result))
        except SyntaxError:
            try:
                exec(compile(code, "<repl>", "exec"), ns, ns)
            except Exception:
                traceback.print_exc()
        except Exception:
            traceback.print_exc()
        return

    # 模拟消息
    is_private = False
    if line.startswith(("p ", "私 ", "private ")):
        is_private = True
        line = line.split(" ", 1)[1].strip()
    parts = line.split(" ", 1)
    if len(parts) < 2 or not parts[0].isdigit():
        print("[调试] 输入格式: <用户ID> <消息内容>   (私聊: p <用户ID> <消息>)")
        return
    user_id, msg = parts[0], parts[1]
    try:
        replies = send_message(user_id, msg, is_private=is_private)
    except Exception:
        traceback.print_exc()
        return
    where = "私聊" if is_private else "群聊"
    print("[模拟] {} {}: {}".format(where, user_id, msg))
    if replies:
        for reply in replies:
            print("[机器人回复]")
            print(reply)
    else:
        print("[机器人] (无回复)")
    print()


def run_repl(ns):
    print("已进入交互模式, 输入 help 查看帮助, exit 退出.")
    while True:
        try:
            line = input("恶赌> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见.")
            break
        if not line:
            continue
        try:
            handle_line(line, ns)
        except SystemExit:
            break


def run_script(path, ns):
    if not os.path.exists(path):
        print("[调试] 脚本文件不存在: {}".format(path))
        return
    with open(path, "r", encoding="utf-8") as f:
        for no, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            print("----- 第 {} 行: {}".format(no, line))
            handle_line(line, ns)


def run_demo():
    """内置演示: 真人对局 + AI自对弈."""
    print("=" * 64)
    print("演示 1: 两名玩家开启 2 人经典对局")
    print("=" * 64)
    ns = repl_namespace()
    for line in (
        "10001 经典匹配2p",
        "10002 加入",
        "10001 局势",
        "10001 吞枪",
    ):
        handle_line(line, ns)

    print("=" * 64)
    print("演示 2: AI自对弈")
    print("=" * 64)
    ai_train(1, trace_first=True)
    model_info()


def main(argv=None):
    parser = argparse.ArgumentParser(description="恶魔轮盘(MammonRoulette)本地调试工具")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--repl", action="store_true", help="强制进入交互式 REPL")
    group.add_argument("--demo", action="store_true", help="运行内置演示")
    group.add_argument("--train", metavar="N", type=int, help="AI自对弈训练N局")
    group.add_argument("--script", metavar="FILE", help="按脚本文件逐行执行指令")
    args = parser.parse_args(argv)

    init_env()
    ns = repl_namespace()

    if args.demo:
        run_demo()
        return
    if args.script:
        run_script(args.script, ns)
        return
    if args.train is not None:
        ok, bad = ai_train(args.train)
        print("[训练] 完成: {}局成功, {}局失败.".format(ok, bad))
        model_info()
        return
    run_repl(ns)


if __name__ == "__main__":
    main()
