# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/main.py
@Author    :    LianQingYu-Love恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

import OlivaDiceCore  # type: ignore
import MammonRoulette

import json
import os

from AmorLib import DataBase, FsmRouter, MsgManager, init_msgCustom

from . import DB_PATH
from .Core.cmop import ModeComp, PropComp

GAME_PATH = "plugin/tmp/MammonRoulette_data.json"
COMMON_CMD = ("priv", "ob", "prep", "play")
game_data = {}


class Event(object):
    def init(plugin_event, Proc):  # type: ignore
        if not os.path.exists("plugin/data/MammonRoulette/"):
            os.mkdir("plugin/data/MammonRoulette/")
        with DataBase(DB_PATH) as db:
            db.create(
                "gambler",
                {
                    "user_id": str,  # 用户
                    "name": str,  # 用户名
                    "points": int,  # 积分
                    "kills": int,  # 击杀
                    "suicide": int,  # 自杀
                    "surrender": int,  # 投降
                    "wins": int,  # 胜局
                    "losses": int,  # 败局
                },
                primary_key="user_id",
            )

    def init_after(plugin_event, Proc):  # type: ignore
        # region 加载对局数据
        try:
            if os.path.exists(GAME_PATH):
                with open(GAME_PATH, "r", encoding="utf-8") as f:
                    global game_data
                    game_data = json.load(f)
            else:
                Proc.log(
                    1, "[恶魔轮盘] - (数据) -> 对局数据存储文件不存在, 尝试创建中……"
                )
                with open(GAME_PATH, "w", encoding="utf-8") as f:
                    json.dump({}, f)
        except Exception as e:
            Proc.log(
                3,
                f"[恶魔轮盘] - (数据) -> 对局数据存储文件丢失, 对局数据清空!\n错误原因:{str(e)}",
            )
        # endregion
        ModeComp.init_after()
        PropComp.init_after()
        init_msgCustom(MammonRoulette, Proc)

    def save(plugin_event, Proc):  # type: ignore
        with open(GAME_PATH, "w", encoding="utf-8") as f:
            json.dump(game_data, f, ensure_ascii=False, indent=4)

    def menu(plugin_event, Proc):  # type: ignore
        if plugin_event.data.namespace == "MammonRoulette":  # type: ignore
            setConsoleSwitchByHash = OlivaDiceCore.console.setConsoleSwitchByHash
            # 总开关
            if plugin_event.data.event == "MammonRoulette_Menu_main_enabled":  # type: ignore
                main_enabled = 1 if not unity_enabled("MrMainEnabled") else -1
                setConsoleSwitchByHash("MrMainEnabled", main_enabled)
                Proc.log(
                    2, "[恶魔轮盘] - {unity} - (总开关) -> " + str(main_enabled == 1)
                )
            # poke开关
            elif plugin_event.data.event == "MammonRoulette_Menu_poke_enabled":  # type: ignore
                poke_enabled = 1 if not unity_enabled("MrPokeEnabled") else -1
                setConsoleSwitchByHash("MrPokeEnabled", poke_enabled)
                Proc.log(
                    2, "[恶魔轮盘] - {unity} - (poke开关) -> " + str(poke_enabled == 1)
                )
            # debug
            elif plugin_event.data.event == "MammonRoulette_Menu_debug":  # type: ignore
                debug_enabled = 1 if not unity_enabled("MrDebugEnabled") else -1
                setConsoleSwitchByHash("MrDebugEnabled", debug_enabled)
                Proc.log(
                    2,
                    "[恶魔轮盘] - {unity} - (debug开关) -> " + str(debug_enabled == 1),
                )
            # 开关重置
            elif plugin_event.data.event == "MammonRoulette_Menu_reset":  # type: ignore
                setConsoleSwitchByHash("MrMainEnabled", 1)
                setConsoleSwitchByHash("MrPokeEnabled", 1)
                setConsoleSwitchByHash("MrDebugEnabled", -1)
                Proc.log(
                    2,
                    "[恶魔轮盘] - (开关) -> 总开关: true; poke开关: true; debug开关: false.",
                )
            # 数据重加载
            elif plugin_event.data.event == "MammonRoulette_Menu_clear_cache":  # type: ignore
                with open(GAME_PATH, "w", encoding="utf-8") as f:
                    json.dump({}, f)
                game_data.clear()
                Proc.log(2, "[恶魔轮盘] - (数据) -> 清除缓存.")

    # region reply
    def group_message(plugin_event, Proc):  # type: ignore
        if not unity_enabled("MrMainEnabled", plugin_event.bot_info.hash):  # type: ignore
            return
        unity_reply(plugin_event, Proc, MsgManager(plugin_event))

    def private_message(plugin_event, Proc):  # type: ignore
        if not unity_enabled("MrMainEnabled", plugin_event.bot_info.hash):  # type: ignore
            return
        unity_reply(plugin_event, Proc, MsgManager(plugin_event))

    def poke(plugin_event, Proc):  # type: ignore
        if not (
            unity_enabled("MrMainEnabled", plugin_event.bot_info.hash)  # type: ignore
            and unity_enabled("MrPokeEnabled", plugin_event.bot_info.hash)  # type: ignore
            and plugin_event.data.group_id  # type: ignore
        ):  # type: ignore
            return
        plugin_event.data.message = "poke"  # type: ignore
        plugin_event.data.sender = {}  # type: ignore
        plugin_event.data.extend = {}  # type: ignore
        msg_manager = MsgManager(plugin_event)
        msg_manager.group_id = plugin_event.data.group_id  # type: ignore
        msg_manager.flags["is_group"] = True
        unity_reply(plugin_event, Proc, msg_manager)

    # endregion


commands = FsmRouter(COMMON_CMD)


def unity_enabled(switchKey, bot_hash="unity"):
    switchValue = OlivaDiceCore.console.getConsoleSwitchByHash(switchKey, bot_hash)
    if switchValue == 0 and bot_hash != "unity":
        switchValue = OlivaDiceCore.console.getConsoleSwitchByHash(switchKey)
    if switchValue == 0:
        switchValue = MammonRoulette.custom.dictConsoleSwitch[switchKey]
    return switchValue == 1


def unity_state(msg_manager):
    if msg_manager.group_id:
        game = game_data.setdefault(msg_manager.group_id, {})
        if msg_manager.user_id in game.get("data", {}).get("order", []):
            state = "play" if game["start"] else "prep"
        else:
            state = "ob"
    else:
        game = {}
        state = "priv"
    msg_manager.val["game"] = game
    msg_manager.val["state"] = state


def unity_reply(plugin_event, Proc, msg_manager):
    if not msg_manager.allow_reply:
        return
    debug = unity_enabled("MrDebugEnabled", plugin_event.bot_info.hash)
    if debug:
        global game_data
        with open(GAME_PATH, "r", encoding="utf-8") as f:
            game_data = json.load(f)
    unity_state(msg_manager)
    game = msg_manager.val["game"]
    state = msg_manager.val["state"]
    # region poke操作
    msg = ""
    if not plugin_event.plugin_info["func_type"] == "poke":
        msg = msg_manager.msg
    else:
        target_id = plugin_event.data.target_id
        is_poke_bot = target_id == plugin_event.base_info["self_id"]
        if is_poke_bot:
            if state == "ob":
                msg = "加入"
            elif state == "prep":
                msg = "退出"
            elif state == "play":
                msg = "局势"
        elif (
            state == "play"
            and msg_manager.user_id == game["data"]["shooter"]
            and target_id in game["data"]["order"]
        ):
            msg = f"开枪{target_id}"
    if not msg:
        return
    # endregion
    forward = commands.search(state, msg, commands.SearchMode.ANY)
    if forward:
        handler, groups = forward[0]
        handler(plugin_event, Proc, msg_manager, groups)
        if game.get("over", False):
            game.clear()
    if debug:
        with open(GAME_PATH, "w", encoding="utf-8") as f:
            json.dump(game_data, f, ensure_ascii=False, indent=4)
        Proc.log(0, f"[恶魔轮盘] - (debug) -> state: {state}; msg: {msg}.")
