import MammonRoulette

import json
import os

from AmorLib import DataBase, init_msgCustom, format_reply

from . import DB_PATH
from .Core.cmd import commands
from .Core.cmop import ModeComp, PropComp

GAME_PATH = "plugin/data/MammonRoulette/game.json"


class Event(object):
    def init(plugin_event, Proc):  # type: ignore
        if not os.path.exists("plugin/data/MammonRoulette/"):
            os.mkdir("plugin/data/MammonRoulette/")
        with open(GAME_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)
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
        # 数据重加载
        if plugin_event.data.event == "MammonRoulette_Menu_clear_cache":  # type: ignore
            with open(GAME_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f)
            Proc.log(2, "[恶魔轮盘] -「数据」-> 清除缓存.")

    def group_message(plugin_event, Proc):  # type: ignore
        unity_reply(plugin_event, Proc, plugin_event.data.group_id)  # type: ignore

    def private_message(plugin_event, Proc):  # type: ignore
        unity_reply(plugin_event, Proc, None)


def unity_reply(plugin_event, Proc, group_id):
    # region 数据
    if os.path.exists(GAME_PATH):
        with open(GAME_PATH, "r", encoding="utf-8") as f:
            game_data = json.load(f)
    else:
        Proc.log(3, "[恶魔轮盘] -「数据」-> 数据文件不存在, 尝试修复中……")
        try:
            with open(GAME_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f)
            game_data = {}
            Proc.log(1, "[恶魔轮盘] -「数据」-> 修复成功.")
        except Exception as e:
            Proc.log(4, f"[恶魔轮盘] -「数据」-> 无法修复! 错误原因: \n{str(e)}")
            return
    # endregion
    msg = plugin_event.data.message
    user_id = plugin_event.data.user_id
    # region 状态
    game = {}
    if not (
        Proc.database.get_basic_config(
            "MammonRoulette",
            "main_enabled",
            default_value=1,
            pkl=False,
        )
        and Proc.database.get_group_config(
            "MammonRoulette",
            "game_enabled",
            "qq",
            group_id,
            None,
            default_value=1,
            pkl=False,
        )
    ):
        state = ""
    elif group_id:
        game = game_data.setdefault(group_id, {})
        if user_id in game.get("order", []):
            state = "play" if game_data[group_id]["start"] else "prep"
        else:
            state = "ob"
    else:
        state = "priv"
    # endregion
    # region 命令
    tValue = {
        "tUserName": plugin_event.data.sender["name"],
        "tName": plugin_event.data.sender["name"],
    }
    custom = ""
    handle, msg_groups = commands.search(state, msg)
    if handle:
        result = handle(game, user_id, group_id, msg_groups)
        if type(result) == tuple:
            custom, tValue_tmp = result
            tValue.update(tValue_tmp)
        else:
            custom = result
    else:
        handle = None
        handle, msg_groups = commands.search("setting", msg)
        if handle:
            custom = handle(plugin_event, Proc, group_id, msg_groups)
    if custom:
        reply = format_reply(
            plugin_event,
            custom,
            tValue,
        )
        plugin_event.reply(str(reply))
    if state in ("ob", "prep", "play"):
        with open(GAME_PATH, "w", encoding="utf-8") as f:
            json.dump(game_data, f, indent=4, ensure_ascii=False)
    # endregion
    return
