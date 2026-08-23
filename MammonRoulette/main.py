# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/main.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

import OlivaDiceCore
import MammonRoulette

import json
import os
import platform

from AmorLib import DataBase, FsmRouter, MsgManager, init_msgCustom

from . import config
from .Core.comp import ModeComp, PropComp, EffectComp, AIComp

COMMON_CMD = ("priv", "ob", "prep", "play")
game_data = {}


class Event(object):
    def init(plugin_event, Proc):  # type: ignore
        pass

    def init_after(plugin_event, Proc):  # type: ignore
        config.initConfig(Proc)
        # region 初始化数据库
        with DataBase(config.DB_PATH) as db:
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
        # endregion
        # region 加载对局数据
        try:
            if os.path.exists(config.TMP_GAME_PATH):
                with open(config.TMP_GAME_PATH, "r", encoding="utf-8") as f:
                    global game_data
                    game_data = json.load(f)
            else:
                Proc.log(
                    1,
                    "[unity] - [恶魔轮盘] - <game_data> - 本地对局数据存储文件不存在, 尝试创建.",
                )
                with open(config.TMP_GAME_PATH, "w", encoding="utf-8") as f:
                    json.dump({}, f)
        except Exception as e:
            Proc.log(
                3,
                f"[unity] - [恶魔轮盘] - <game_data> - 本地对局数据存储文件丢失, 对局数据清空!\n{str(e)}",
            )
        # endregion
        ModeComp.init_after()
        PropComp.init_after()
        EffectComp.init_after()
        init_msgCustom(MammonRoulette, Proc)
        config.readConfig(Proc)
        config.saveConfig(Proc)
        AIComp.load_all()

    def save(plugin_event, Proc):  # type: ignore
        with open(config.TMP_GAME_PATH, "w", encoding="utf-8") as f:
            json.dump(game_data, f, ensure_ascii=False, indent=4)
        AIComp.save_all()

    def menu(plugin_event, Proc):  # type: ignore
        if plugin_event.data.namespace == "MammonRoulette":  # type: ignore
            setConsoleSwitchByHash = OlivaDiceCore.console.setConsoleSwitchByHash
            # 全局开关
            if plugin_event.data.event == "MammonRoulette_Menu_main_enabled":  # type: ignore
                main_enabled = 1 if not unity_enabled("MrMainEnabled") else 0
                setConsoleSwitchByHash("MrMainEnabled", main_enabled)
                Proc.log(
                    2,
                    "[unity] - [恶魔轮盘] - <MammonRoulette_Menu_main_enabled> - " + str(main_enabled == 1),
                )
            # poke开关
            elif plugin_event.data.event == "MammonRoulette_Menu_poke_enabled":  # type: ignore
                poke_enabled = 1 if not unity_enabled("MrPokeEnabled") else 0
                setConsoleSwitchByHash("MrPokeEnabled", poke_enabled)
                Proc.log(
                    2,
                    "[unity] - [恶魔轮盘] - <MammonRoulette_Menu_poke_enabled> - " + str(poke_enabled == 1),
                )
            # debug模式
            elif plugin_event.data.event == "MammonRoulette_Menu_debug":  # type: ignore
                config.DEBUG_FLAG = not config.DEBUG_FLAG
                config.saveConfig(Proc)
                Proc.log(
                    2,
                    "[unity] - [恶魔轮盘] - <MammonRoulette_Menu_debug> - " + str(config.DEBUG_FLAG),
                )
            # 清除缓存
            elif plugin_event.data.event == "MammonRoulette_Menu_clear_cache":  # type: ignore
                with open(config.TMP_GAME_PATH, "w", encoding="utf-8") as f:
                    json.dump({}, f)
                game_data.clear()
                Proc.log(2, "[unity] - [恶魔轮盘] - <game_data> - None")
            # 重载配置
            elif plugin_event.data.event == "MammonRoulette_Menu_config_reload":  # type: ignore
                config.readConfig(Proc)
                Proc.log(
                    2,
                    "[unity] - [恶魔轮盘] - [config] - 重加载.",
                )
            elif plugin_event.data.event == "MammonRoulette_Menu_manage":  # type: ignore
                if MammonRoulette.config.has_NativeGUI and platform.system() == "Windows":
                    MammonRoulette.GUI.ConfigUI(
                        Model_name="MammonRoulette_manage",
                        logger_proc=Proc.Proc_info.logger_proc.log,
                    ).start()

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
    unity_switchValue = OlivaDiceCore.console.getConsoleSwitchByHash(switchKey, "unity") == 1
    if bot_hash == "unity":
        return unity_switchValue
    bot_switchValue = OlivaDiceCore.console.getConsoleSwitchByHash(switchKey, bot_hash) == 1
    return unity_switchValue and bot_switchValue


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
    if config.DEBUG_FLAG:
        global game_data
        with open(config.TMP_GAME_PATH, "r", encoding="utf-8") as f:
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
        elif state == "play" and msg_manager.user_id == game["data"]["shooter"] and target_id in game["data"]["order"]:
            msg = f"开枪{target_id}"
    if not msg:
        return
    # endregion
    forward = commands.search(state, msg, commands.SearchMode.ANY)
    if forward:
        game["tmp"] = {}
        handler, groups = forward[0]
        handler(plugin_event, Proc, msg_manager, groups)
        if game.get("over", False):
            game.clear()
    if config.DEBUG_FLAG:
        with open(config.TMP_GAME_PATH, "w", encoding="utf-8") as f:
            json.dump(game_data, f, ensure_ascii=False, indent=4)
        Proc.log(0, f"[unity] - [恶魔轮盘] - [debug] - commands({state}, {msg}).")
