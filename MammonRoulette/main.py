import MammonRoulette
import OlivOS  # type: ignore

import json
import os
import time
import random

from AmorLib import DataBase, FsmRouter, MsgManager, init_msgCustom

from . import DB_PATH
from .Core.cmop import ModeComp, PropComp

GAME_PATH = "plugin/data/MammonRoulette/game.json"
COMMON_CMD = ("priv", "ob", "prep", "play")


class Event(object):
    def init(plugin_event, Proc):  # type: ignore
        if not os.path.exists("plugin/data/MammonRoulette/"):
            os.mkdir("plugin/data/MammonRoulette/")
        try:
            if os.path.exists(GAME_PATH):
                with open(GAME_PATH, "r", encoding="utf-8") as f:
                    json.load(f)
            else:
                Proc.log(3, "[恶魔轮盘] -「数据」-> 数据存储文件不存在, 尝试修复中……")
                with open(GAME_PATH, "w", encoding="utf-8") as f:
                    json.dump({}, f)
                Proc.log(1, "[恶魔轮盘] -「数据」-> 修复成功.")
        except Exception as e:
            Proc.log(4, f"[恶魔轮盘] -「数据」-> 无法修复! 错误原因: \n{str(e)}")
            Proc.database.set_basic_config(
                "MammonRoulette", "main_enabled", 0, pkl=False
            )
        with DataBase(DB_PATH) as db:
            db.create(
                "gambler",
                {
                    "user_id": str,  # 用户
                    "name": str,  # 用户名
                    "points": int,  # 积分
                    "kills": int,  # 击杀
                    "suicide": int,  # 自杀
                    "wins": int,  # 胜局
                    "losses": int,  # 败局
                },
                primary_key="user_id",
            )

    def init_after(plugin_event, Proc):  # type: ignore
        ModeComp.init_after()
        PropComp.init_after()
        init_msgCustom(MammonRoulette, Proc)

    def menu(plugin_event, Proc):  # type: ignore
        if plugin_event.data.namespace == "MammonRoulette":  # type: ignore
            # 总开关
            if plugin_event.data.event == "MammonRoulette_Menu_main_enabled":  # type: ignore
                main_enabled = not Proc.database.get_basic_config(
                    "MammonRoulette",
                    "main_enabled",
                    default_value=1,
                    pkl=False,
                )
                Proc.database.set_basic_config(
                    "MammonRoulette", "main_enabled", int(main_enabled), pkl=False
                )
                Proc.log(2, "恶魔轮盘 -〈总开关〉-> " + str(main_enabled))
            # poke开关
            elif plugin_event.data.event == "MammonRoulette_Menu_poke_enabled":  # type: ignore
                poke_enabled = not Proc.database.get_basic_config(
                    "MammonRoulette",
                    "poke_enabled",
                    default_value=1,
                    pkl=False,
                )
                Proc.database.set_basic_config(
                    "MammonRoulette", "poke_enabled", int(poke_enabled), pkl=False
                )
                Proc.log(2, "恶魔轮盘 -〈poke开关〉-> " + str(poke_enabled))
            # 数据重加载
            elif plugin_event.data.event == "MammonRoulette_Menu_clear_cache":  # type: ignore
                with open(GAME_PATH, "w", encoding="utf-8") as f:
                    json.dump({}, f)
                Proc.log(2, "[恶魔轮盘] -「数据」-> 清除缓存.")

    def group_message(plugin_event, Proc):  # type: ignore
        unity_reply(plugin_event, Proc)

    def private_message(plugin_event, Proc):  # type: ignore
        plugin_event.data.group_id = None  # type: ignore
        unity_reply(plugin_event, Proc)

    def poke(plugin_event, Proc):  # type: ignore
        if plugin_event.data.group_id and Proc.database.get_basic_config(  # type: ignore
            "MammonRoulette",
            "poke_enabled",
            default_value=1,
            pkl=False,
        ):  # type: ignore
            plugin_event.data.message = "poke"  # type: ignore
            plugin_event.data.sender = {}  # type: ignore
            plugin_event.data.extend = {}  # type: ignore
            unity_reply(plugin_event, Proc)


commands = FsmRouter(COMMON_CMD)
ANY = commands.SearchMode.ANY


def unity_reply(plugin_event, Proc):
    if not Proc.database.get_basic_config(
        "MammonRoulette",
        "main_enabled",
        default_value=1,
        pkl=False,
    ):
        return
    msg_manager = MsgManager(plugin_event)
    msg_manager.val["game_update"] = False
    if not msg_manager.allow_reply:
        return
    # region 数据
    with open(GAME_PATH, "r", encoding="utf-8") as f:
        game_data = json.load(f)
    # endregion
    # region 状态
    game = {}
    if plugin_event.data.group_id:
        game = game_data.setdefault(plugin_event.data.group_id, {})
        if msg_manager.user_id in game.get("order", []):
            state = "play" if game["start"] else "prep"
        else:
            state = "ob"
    else:
        state = "priv"
    msg_manager.val["game"] = game
    # endregion
    # region poke
    msg = ""
    if not plugin_event.plugin_info["func_type"] == "poke":
        msg = msg_manager.msg
    elif state == "ob":
        msg = "加入"
    elif state == "prep":
        msg = "退出"
    elif state == "play":
        msg = "局势"
    # endregion
    for handler, groups in commands.search(state, msg, ANY):
        result = handler(plugin_event, Proc, msg_manager, groups)
        if result:
            if msg_manager.val["game_update"]:
                with open(GAME_PATH, "w", encoding="utf-8") as f:
                    json.dump(game_data, f, ensure_ascii=False, indent=4)
            break
