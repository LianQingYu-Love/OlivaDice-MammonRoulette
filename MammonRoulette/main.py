import json
import os

from AmorLib import DataBase

from . import DB_PATH
from .Core.cmd import commands
from .Core.cmop import ModeComp, PropComp
from .Core.doc import helpdoc

GAME_PATH = "plugin/data/MammonRoulette/game.json"


class Event(object):
    def init(plugin_event, Proc):  # type: ignore
        if not os.path.exists("plugin/data/MammonRoulette/"):
            os.mkdir("plugin/data/MammonRoulette/")
        MammonRoulette.load()

    def menu(plugin_event, Proc):  # type: ignore
        # 总开关
        if plugin_event.data.event == "MammonRoulette_Menu_main_enabled":  # type: ignore
            main_enabled = not MammonRoulette.main_enabled(Proc, "main_enabled")
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
        Proc.log(3, "[恶魔轮盘] -「数据」-> 数据无法加载, 尝试修复中……")
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
        MammonRoulette.main_enabled(Proc, "main_enabled")
        and MammonRoulette.group_enabled(Proc, "game_enabled", group_id)
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
    reply, update = None, False
    handle, msg_groups = commands.search(state, msg)
    if handle:
        result = handle(game, user_id, group_id, msg_groups)
        reply, update = result if type(result) == tuple else (result, False)
    else:
        handle = None
        handle, msg_groups = commands.search("setting", msg)
        if handle:
            reply = handle(plugin_event, Proc, group_id, msg_groups)
    if reply:
        plugin_event.reply(str(reply))
    if update:
        with open(GAME_PATH, "w", encoding="utf-8") as f:
            json.dump(game_data, f, indent=4, ensure_ascii=False)
    # endregion
    return


class MammonRoulette:
    @classmethod
    def load(cls):
        with open(GAME_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)
        PropComp.init_after()
        # region 数据库
        with DataBase(DB_PATH) as db:
            # 玩家表
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
        # endregion
        # region helpdoc
        helpdoc.update_cmd()
        help = helpdoc.doc
        for mode_name in ModeComp.list():
            mode_cfg = ModeComp.get(mode_name)
            brief = mode_cfg.brief
            if brief:
                help["helpdoc"][f"恶赌模式 {mode_name}"] = mode_cfg.brief
        for prop_name in PropComp.list():
            prop_cfg = PropComp.get(prop_name)
            brief = prop_cfg.brief
            if brief:
                help["helpdoc"][f"恶赌道具 {prop_name}"] = prop_cfg.brief
        helpdoc_path = (
            "plugin/data/OlivaDice/unity/extend/helpdoc/恶魔轮盘帮助文档.json"
        )
        with open(helpdoc_path, "w", encoding="utf-8") as f:
            json.dump(help, f, ensure_ascii=False, indent=4)
        # endregion

    @staticmethod
    def main_enabled(Proc, key):
        return Proc.database.get_basic_config(
            "MammonRoulette",
            key,
            default_value=1,
            pkl=False,
        )

    @staticmethod
    def group_enabled(Proc, key, group_id):
        if group_id:
            return Proc.database.get_group_config(
                "MammonRoulette", key, "qq", group_id, None, default_value=1, pkl=False
            )
        return True
