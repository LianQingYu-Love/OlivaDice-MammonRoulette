import random
import time
from collections import Counter

from AmorLib import DataBase

from . import DB_PATH
from .main import commands, COMMON_CMD
from .msgCustom import dictHelpDocTemp
from .Core.cmop import ModeComp, PropComp
from .Core.work import GameWork

dictHelpDocTemp["恶赌命令"] = (
    "〔设置〕\n"
    "恶赌(on,off) //游戏开关(需管理权限).\n"
    "〔资料〕\n"
    "(名称)签署[生死状,契约] //注册角色或修改名称.\n"
    "恶魔名片(数值,留空) //查看自己或他人的资料.\n"
    "恶魔(赏金,杀戮,自杀,留空)[排行,榜] //查询排行, 留空默认查询赏金榜单.\n"
    "〔对局操作〕\n"
    "(模式名)匹配 //以默认人数匹配对局, 满人自动开启\n(模式名)匹配(数值)p //以自定义人数匹配对局.\n"
    "退出 //退出匹配\n"
    "(吞或开)枪(目标) //对目标射击, 可用qq号或序号指定目标, 留空默认下一顺位.\n"
    "[使用,留空](道具名) (目标) //对目标使用道具, 可用qq号或序号指定目标.\n"
    "局势 //查询当前游戏局势信息.\n"
    "投降 //以自杀的形式结束."
)


# --------
poker = {
    "suits": ("方片♦️", "梅花♣️", "红桃♥️", "黑桃♠️"),
    "ranks": ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"),
}


def get_target(game, target):
    order = game["order"]
    if not target:
        target = order[(order.index(game["shooter"]) + 1) % len(order)]
    elif target not in order:
        target = int(target)
        if target > len(order):
            return
        target = order[target - 1]
    return target


# region 资料
@commands.route(COMMON_CMD, "^(.+)(?:签署|簽署)(?:生死状|契约|生死狀|契約)$")
def signed(plugin_event, Proc, msg_manager, groups):
    name = groups[0]
    user_id = msg_manager.user_id
    with DataBase(DB_PATH) as db:
        gambler_info = db.select("gambler", "user_id", "user_id = ?", user_id)
        if gambler_info:
            db.update("gambler", {"name": name}, "user_id = ?", user_id)
        else:
            db.insert(
                "gambler",
                {
                    "user_id": user_id,
                    "name": name,
                    "points": 0,
                    "kills": 0,
                    "suicide": 0,
                    "wins": 0,
                    "losses": 0,
                },
            )
    reply = msg_manager.msg_format("strMrSignedResult", {"gamblerName": name})
    plugin_event.reply(reply)
    return True


@commands.route(COMMON_CMD, "^[惡恶]魔名片(\\d*)$")
def card(plugin_event, Proc, msg_manager, groups):
    user_id = msg_manager.user_id
    target = groups[0] if groups[0] != "" else user_id
    with DataBase(DB_PATH) as db:
        gambler_info = db.select("gambler", "*", "user_id = ?", target)
        if not gambler_info:
            reply = msg_manager.msg_format("strMrCardNone")
            plugin_event.reply(reply)
            return False
        gambler_info = gambler_info[0]
        gambler_ranking = db.select(
            "gambler", "COUNT(*)", "points > ?", gambler_info["points"]
        )[0][0]
    wins, losses = int(gambler_info["wins"]), int(gambler_info["losses"])
    total = wins + losses
    win_rate = f"{ round(wins/total*100 ,2) } %" if total > 0 else "未參與過輪盤"
    reply = msg_manager.msg_format(
        "strMrCardHas",
        {
            "gamblerName": gambler_info["name"],
            "gamblerRanking": gambler_ranking + 1,
            "gamblerPoints": gambler_info["points"],
            "gamblerKills": gambler_info["kills"],
            "gamblerSuicide": gambler_info["suicide"],
            "gamblerWins": wins,
            "gamblerLosses": losses,
            "gamblerWinRate": win_rate,
        },
    )
    plugin_event.reply(reply)
    return True


@commands.route(COMMON_CMD, "^[恶惡]魔(赏金|杀戮|自杀|)(?:排行|榜)(\\d*)$")
def leaderboard(plugin_event, Proc, msg_manager, groups):
    ranking_page = int(groups[1] or 1) * 10 - 10
    ranking_type = groups[0] or "赏金"
    if ranking_type == "赏金":
        leaderboard_type = "points"
    elif ranking_type == "杀戮":
        leaderboard_type = "kills"
    else:
        leaderboard_type = "suicide"
    with DataBase(DB_PATH) as db:
        gambler_list = db.select(
            "gambler",
            f"name, {leaderboard_type}",
            order=f"{leaderboard_type} DESC",
            limit=10,
            offset=ranking_page,
        )
        if not gambler_list:
            return False
        gambler_total = db.select("gambler", "COUNT(*)")
    top_list = "\n".join(
        msg_manager.msg_format(
            "strMrLeaderboardCard",
            {
                "gamblerRanking": idx + ranking_page + 1,
                "gamblerName": gambler_info["name"],
                "gamblerRecord": gambler_info[leaderboard_type],
            },
        )
        for idx, gambler_info in enumerate(gambler_list)
    )
    reply = msg_manager.msg_format(
        "strMrLeaderboard",
        {
            "leaderboardType": ranking_type,
            "gamblerTopList": top_list,
            "rankingPageHome": ranking_page + 1,
            "rankingPageEnd": ranking_page + 10,
            "gamblerNumCount": gambler_total[0][0],
        },
    )
    plugin_event.reply(reply)
    return True


# endregion
# region 房间操作
@commands.route("ob", f"^({'|'.join(ModeComp.list())})匹配(?:(\\d+)p)?$")
def match_game(plugin_event, Proc, msg_manager, groups):
    msg_manager.val["game_update"] = True
    user_id, game = msg_manager.user_id, msg_manager.val["game"]
    # region 自动注册
    with DataBase(DB_PATH) as db:
        gambler_info = db.select("gambler", "user_id", "user_id = ?", user_id)
    if not gambler_info:
        name = f"{random.choice(poker['suits'])+random.choice(poker['ranks'])}"
        signed(plugin_event, Proc, msg_manager, (name,))
    # endregion
    # region 读取模式数据
    mode_name, seats = groups[0], groups[1]
    mode_cfg = ModeComp.get(mode_name)
    seats_min, seats_max, seats_def = (
        mode_cfg.seats.min,
        mode_cfg.seats.max,
        mode_cfg.seats.default,
    )
    seats = int(seats) if seats else seats_def
    if not (seats_min <= seats <= seats_max):
        reply = msg_manager.msg_format(
            "strMrGameSeatsError",
            {
                "gameMode": mode_name,
                "seatsMin": seats_min,
                "seatsMax": seats_max,
                "seatsDef": seats_def,
            },
        )
        plugin_event.reply(reply)
        return False
    # endregion
    # region 清除过期对局
    expireTime = int(time.time())
    if expireTime > game.get("expireTime", 0) and not game.get("start", False):
        game.clear()
    # endregion
    # region 构建对局
    if not game.get("mode", None):
        game.clear()
        game.update(
            {
                "start": False,
                "expireTime": expireTime + 600,
                "mode": mode_name,
                "points": mode_cfg.points,
                "seats": seats,
                "ammo_live": 0,
                "ammo_blank": 0,
                "bullet": False,
                "shooter": "",
                "order": [],
                "props": {
                    "pool": mode_cfg.props.pool,
                    "ban": mode_cfg.props.ban,
                    "limit": mode_cfg.props.limit,
                },
                "players": {},
                "modify": {},
                "callback": {
                    "reload": [],
                    "shoot": [],
                    "damage": [],
                    "end_round": [],
                    "switch": [],
                },
                "reply": {
                    "info": [],
                    "ammo": "",
                    "shooter": "",
                    "over": "",
                },
            }
        )
    elif game["start"]:
        reply = msg_manager.msg_format("strMrGameStartError")
        plugin_event.reply(reply)
        return False
    elif mode_name != game["mode"]:
        reply = msg_manager.msg_format(
            "strMrMatchModeError", {"gameMode": game["mode"]}
        )
        plugin_event.reply(reply)
        return False
    # endregion
    # region 添加玩家
    if user_id not in game["order"]:
        with DataBase(DB_PATH) as db:
            name = db.select("gambler", "name", "user_id = ?", user_id)[0][0]
        game["order"].append(user_id)
        game["players"][user_id] = {
            "name": name,
            "hp": 3,
            "actions": 0,
            "props": [],
            "kills": 0,
            "suicide": False,
        }
        mode_cfg.join(game, user_id)
    # endregion
    # region 检查人数
    seats = game["seats"]
    if len(game["order"]) >= seats:
        game["start"] = True
        game["expireTime"] = 0
        GameWork.bullet(game)
        random.shuffle(game["order"])
        shooter = game["order"][0]
        game["shooter"] = shooter
        game["players"][shooter]["actions"] = 1
        mode_cfg.start(game)
        game["reply"].update({"info": [], "ammo": "", "shooter": ""})
        situation(plugin_event, Proc, msg_manager, None)
    else:
        reply = msg_manager.msg_format(
            "strMrGamePrep",
            {
                "gameMode": game["mode"],
                "seatsHas": len(game["order"]),
                "seatsMax": seats,
            },
        )
        plugin_event.reply(reply)
        return True
    # endregion


@commands.route("ob", "^加入$")
def join_game(plugin_event, Proc, msg_manager, groups):
    game = msg_manager.val["game"]
    if not game or game["start"]:
        return False
    mode_name = game["mode"]
    match_game(plugin_event, Proc, msg_manager, (mode_name, ""))
    return True


@commands.route("prep", "^退出$")
def exit_game(plugin_event, Proc, msg_manager, groups):
    msg_manager.val["game_update"] = True
    user_id, game = msg_manager.user_id, msg_manager.val["game"]
    game["order"].remove(user_id)
    del game["players"][user_id]
    if not game["order"]:
        game.clear()
        reply = msg_manager.msg_format("strMrExitDismiss")
    else:
        reply = msg_manager.msg_format(
            "strMrExitRemain", {"seatsHas": len(game["order"])}
        )
    plugin_event.reply(reply)
    return True


# endregion
# region 对局操作
@commands.route("play", "^(吞|开|開)[槍|枪] *(\\d*)$")
def shoot(plugin_event, Proc, msg_manager, groups):
    msg_manager.val["game_update"] = True
    user_id, game = msg_manager.user_id, msg_manager.val["game"]
    if game["shooter"] != user_id:
        reply = msg_manager.msg_format(
            "strMrActionsError", {"gamblerName": GameWork.get_name(game)}
        )
        plugin_event.reply(reply)
        return False
    # 确定目标
    target = groups[1]
    if groups[0] == "吞":
        target = user_id
    elif not (target := get_target(game, target)):
        return False
    GameWork.shoot(game, target)
    reply = GameWork.reply(game)
    plugin_event.reply(reply)
    return True


@commands.route("play", f"^(?:使用|) *({'|'.join(PropComp.list())}) *(\\d*)$")
def use_prop(plugin_event, Proc, msg_manager, groups):
    msg_manager.val["game_update"] = True
    user_id, game = msg_manager.user_id, msg_manager.val["game"]
    if game["shooter"] != user_id:
        reply = msg_manager.msg_format(
            "strMrActionsError", {"gamblerName": GameWork.get_name(game)}
        )
        plugin_event.reply(reply)
        return False
    prop, target = groups[0], groups[1]
    pl = game["players"][user_id]
    if prop not in pl["props"]:
        reply = msg_manager.msg_format("strMrPropError", {"propName": prop})
        plugin_event.reply(reply)
        return False
    if not target:
        target = user_id
    elif not (target := get_target(game, target)):
        return False
    if PropComp.use(game, prop, target):
        GameWork.remove_prop(game, user_id, prop)
        reply = GameWork.reply(game)
        plugin_event.reply(reply)
        return True
    return False


@commands.route(COMMON_CMD, "^(?:局势|局勢)$")
def situation(plugin_event, Proc, msg_manager, groups):
    game = msg_manager.val["game"]
    if not game:
        return False
    order, players, shooter = game["order"], game["players"], game["shooter"]
    # 赌徒
    modify = game["modify"]
    pl_list = [
        (
            f"〔{idx+1}〕 {pl['name']}{'「束縛中」' if pl in modify.get('手铐',[]) else ''}\n"
            f"「hp: {pl['hp']}」\n"
            f"{('、'.join(f'{prop}' if count == 1 else f'{prop}*{count}' for prop, count in Counter(pl['props']).items()) if pl.get('props') else '無道具')}\n"
        )
        for idx, user_id in enumerate(order)
        for pl in [players[user_id]]
    ]
    # 弹药
    ammo_live, ammo_blank = game["ammo_live"], game["ammo_blank"]
    ammo = (
        f"\n彈仓: {ammo_live} / {ammo_live+ammo_blank}"
        if not game["modify"].get("ammo_hide")
        else "\n霰彈槍隱匿于迷霧之中."
    )
    # 子弹
    bullet = (
        f"\n當前子彈: {'實彈' if game['bullet'] else '空包彈'}"
        if game["modify"].get("bullet_show")
        else ""
    )
    # 死亡
    dead_list = [players[uid]["name"] for uid in players if uid not in order]
    dead = f"\n滅亡[{'、'.join(dead_list)}]" if dead_list else ""
    reply = (
        "".join(pl_list) + "▁▁▁▁▁▁▁▁▁▁▁▁▁▁\n"
        f"槍手:〔{order.index(shooter)+1}〕{players[shooter]['name']}"
        + ammo
        + bullet
        + dead
    )
    plugin_event.reply(reply)
    return True


@commands.route("play", "^投降$")
def surrender(plugin_event, Proc, msg_manager, groups):
    msg_manager.val["game_update"] = True
    user_id, game = msg_manager.user_id, msg_manager.val["game"]
    game["reply"]["info"].append(f"{GameWork.get_name(game,user_id)}被清除。")
    GameWork.dead(game, user_id, True)
    if len(game["order"]) <= 1:
        GameWork.end_round(game)
    reply = GameWork.reply(game)
    plugin_event.reply(reply)
    return True


# endregion
