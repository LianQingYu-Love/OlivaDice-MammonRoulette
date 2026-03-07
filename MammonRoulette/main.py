import MammonRoulette

import json
import os

from AmorLib import DataBase, FsmRouter, MsgManager, init_msgCustom

from . import DB_PATH
from .Core.cmop import ModeComp, PropComp

GAME_PATH = "plugin/tmp/MammonRoulette_game_data.json"
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
                Proc.log(2, "[恶魔轮盘] - (数据) -> " + str(main_enabled))
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
                Proc.log(2, "[恶魔轮盘] - (数据) -> " + str(poke_enabled))
            # 数据重加载
            elif plugin_event.data.event == "MammonRoulette_Menu_clear_cache":  # type: ignore
                with open(GAME_PATH, "w", encoding="utf-8") as f:
                    json.dump({}, f)
                game_data.clear()
                Proc.log(2, "[恶魔轮盘] - (数据) -> 清除缓存.")

    def group_message(plugin_event, Proc):  # type: ignore
        unity_reply(plugin_event, Proc)

    def private_message(plugin_event, Proc):  # type: ignore
        unity_reply(plugin_event, Proc)

    def poke(plugin_event, Proc):  # type: ignore
        if (
            Proc.database.get_basic_config(  # type: ignore
                "MammonRoulette",
                "poke_enabled",
                default_value=1,
                pkl=False,
            )
            and plugin_event.data.group_id  # type: ignore
        ):  # type: ignore
            plugin_event.data.message = "poke"  # type: ignore
            plugin_event.data.sender = {}  # type: ignore
            plugin_event.data.extend = {}  # type: ignore
            unity_reply(plugin_event, Proc)


commands = FsmRouter(COMMON_CMD)


def unity_reply(plugin_event, Proc):
    if not Proc.database.get_basic_config(
        "MammonRoulette",
        "main_enabled",
        default_value=1,
        pkl=False,
    ):
        return
    msg_manager = MsgManager(plugin_event)
    if not msg_manager.allow_reply:
        return
    # region 数据与状态
    if msg_manager.group_id:
        game = game_data.setdefault(msg_manager.group_id, {})
        if msg_manager.user_id in game.get("order", []):
            state = "play" if game["start"] else "prep"
        else:
            state = "ob"
    else:
        game = {}
        state = "priv"
    msg_manager.val["game"] = game
    # endregion
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
            and msg_manager.user_id == game["shooter"]
            and target_id in game["order"]
        ):
            msg = f"开枪{target_id}"
    if not msg:
        return
    # endregion
    forward = commands.search(state, msg, commands.SearchMode.ANY)
    if forward:
        handler, groups = forward[0]
        handler(plugin_event, Proc, msg_manager, groups)
