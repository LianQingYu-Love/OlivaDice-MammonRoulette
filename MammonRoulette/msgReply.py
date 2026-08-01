# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/router.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

import random
import time
from collections import Counter

from AmorLib import DataBase

from . import DB_PATH
from .main import commands, COMMON_CMD
from .msgCustom import dictHelpDoc
from .Core.cmop import ModeComp, PropComp
from .Core.work import RegGameWork

dictHelpDoc["恶赌 命令"] = (
    "#设置\n"
    "(名称)签署[生死状,契约] //注册角色或修改名称.\n"
    "恶魔名片(数值,留空) //查看自己或他人的资料.\n"
    "恶魔(赏金,杀戮,自杀,留空)[排行,榜] //查询排行, 留空默认查询赏金榜单.\n"
    "#房间操作\n"
    "(模式名)[匹配,对局] //以默认人数匹配对局, 满人自动开启\n(模式名)匹配(数值)p //以自定义人数匹配对局.\n"
    "[加入,进入] //加入正在匹配的对局\n"
    "[退出,离开] //退出匹配\n"
    "#对局操作\n"
    "(吞或开)枪(目标) //对目标射击, 可用qq号或序号指定目标, 留空默认下一顺位.\n"
    "[使用,留空](道具名) (目标) //对目标使用道具, 可用qq号或序号指定目标.\n"
    "局势 //查询当前游戏局势信息.\n"
    "投降 //以自杀的形式结束.\n"
)
dictHelpDoc["恶赌 戳一戳命令"] = (
    "#戳一戳骰娘\n未加入对局: 加入正则匹配的对局;\n"
    "对局匹配中: 退出正则匹配的对局;\n"
    "对局进行时: 查看局势.\n"
    "#戳一戳玩家: 向其开枪."
)


# --------
poker = {
    "suits": ("方片♦️", "梅花♣️", "红桃♥️", "黑桃♠️"),
    "ranks": ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"),
}


def get_target(game, target):
    data = game["data"]
    order = data["order"]
    if not target:
        target = order[(order.index(data["shooter"]) + 1) % len(order)]
    elif target not in order:
        target = int(target)
        if target > len(order) or target < 1:
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
                    "surrender": 0,
                    "wins": 0,
                    "losses": 0,
                },
            )
    msg_reply = msg_manager.msg_format("strMrSignedResult", {"tGamblerName": name})
    plugin_event.reply(msg_reply)
    return


@commands.route(COMMON_CMD, "^[惡恶]魔名片(\\d*)$")
def card(plugin_event, Proc, msg_manager, groups):
    user_id = msg_manager.user_id
    target = groups[0] if groups[0] != "" else user_id
    with DataBase(DB_PATH) as db:
        gambler_info = db.select("gambler", "*", "user_id = ?", target)
        if not gambler_info:
            msg_reply = msg_manager.msg_format("strMrCardNone")
            plugin_event.reply(msg_reply)
            return
        gambler_info = gambler_info[0]
        gambler_ranking = db.select(
            "gambler", "COUNT(*)", "points > ?", gambler_info["points"]
        )[0][0]
    wins, losses = int(gambler_info["wins"]), int(gambler_info["losses"])
    total = wins + losses
    win_rate = f"{ round(wins/total*100 ,2) } %" if total > 0 else "未參與過輪盤"
    msg_reply = msg_manager.msg_format(
        "strMrCardHas",
        {
            "tGamblerName": gambler_info["name"],
            "tGamblerRanking": gambler_ranking + 1,
            "tGamblerPoints": gambler_info["points"],
            "tGamblerKills": gambler_info["kills"],
            "tGamblerSuicide": gambler_info["suicide"],
            "tGamblerSurrender": gambler_info["surrender"],
            "tGamblerWins": wins,
            "tGamblerLosses": losses,
            "tGamblerWinRate": win_rate,
        },
    )
    plugin_event.reply(msg_reply)
    return


@commands.route(COMMON_CMD, "^[恶惡]魔(赏金|杀戮|自杀|投降|)(?:排行|榜)(\\d*)$")
def leaderboard(plugin_event, Proc, msg_manager, groups):
    ranking_page = int(groups[1] or 1) * 10 - 10
    ranking_type = groups[0]
    if ranking_type == "赏金":
        leaderboard_type = "points"
    elif ranking_type == "杀戮":
        leaderboard_type = "kills"
    elif ranking_type == "自杀":
        leaderboard_type = "suicide"
    elif ranking_type == "投降":
        leaderboard_type = "surrender"
    else:
        leaderboard_type = "points"
    with DataBase(DB_PATH) as db:
        gambler_list = db.select(
            "gambler",
            f"name, {leaderboard_type}",
            order=f"{leaderboard_type} DESC",
            limit=10,
            offset=ranking_page,
        )
        if not gambler_list:
            return
        gambler_total = db.select("gambler", "COUNT(*)")
    top_list = "\n".join(
        msg_manager.msg_format(
            "strMrGamblerRankNode",
            {
                "tGamblerRanking": idx + ranking_page + 1,
                "tGamblerName": gambler_info["name"],
                "tGamblerRecord": gambler_info[leaderboard_type],
            },
        )
        for idx, gambler_info in enumerate(gambler_list)
    )
    msg_reply = msg_manager.msg_format(
        "strMrLeaderboardResult",
        {
            "tLeaderboardType": ranking_type,
            "tGamblerTopList": top_list,
            "tRankingPageHome": ranking_page + 1,
            "tRankingPageEnd": ranking_page + 10,
            "tGamblerCount": gambler_total[0][0],
        },
    )
    plugin_event.reply(msg_reply)
    return


# endregion
# region 房间操作
@commands.route("ob", f"^({'|'.join(ModeComp.list())})(?:匹配|对局)(?:(\\d+)p)?$")
def match_game(plugin_event, Proc, msg_manager, groups):
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
        msg_reply = msg_manager.msg_format(
            "strMrGameSeatsError",
            {
                "tGameMode": mode_name,
                "tSeatsMin": seats_min,
                "tSeatsMax": seats_max,
                "tSeatsDef": seats_def,
            },
        )
        plugin_event.reply(msg_reply)
        return
    # endregion
    game_start = game.get("start", False)
    # region 清除过期对局
    expireTime = int(time.time())
    if expireTime > game.get("expireTime", 0) and not game_start:
        game.clear()
    # endregion
    # region 构建对局
    if not game.get("mode", None):
        game.clear()
        game.update(
            {
                "start": False,
                "over": False,
                "expireTime": expireTime + 600,
                "seats": seats,
                "mode": {
                    "name": mode_name,
                    "points": mode_cfg.points,
                    "props": {
                        "pool": mode_cfg.props.pool,
                        "ban": mode_cfg.props.ban,
                        "limit": mode_cfg.props.limit,
                    },
                },
                "data": {
                    "ammo_live": 0,
                    "ammo_blank": 0,
                    "bullet": False,
                    "shooter": "",
                    "order": [],
                    "players": {},
                    "modify": {
                        "dmg": mode_cfg.modify.dmg,
                        "ammo_show": mode_cfg.modify.ammo_show,
                        "bullet_show": mode_cfg.modify.bullet_show,
                    },
                    "prop_event": [],
                },
                "reply": {
                    "info": [],
                    "note": {
                        "ammo": False,
                        "round": False,
                    },
                    "only": "",
                },
                "tmp": {},
            }
        )
    elif game_start:
        msg_reply = msg_manager.msg_format("strMrGameStarted")
        plugin_event.reply(msg_reply)
        return
    elif mode_name != game["mode"]["name"]:
        msg_reply = msg_manager.msg_format(
            "strMrGameModeError", {"tGameMode": game["mode"]["name"]}
        )
        plugin_event.reply(msg_reply)
        return
    # endregion
    data = game["data"]
    order = data["order"]
    # region 添加玩家
    if user_id not in order:
        with DataBase(DB_PATH) as db:
            name = db.select("gambler", "name", "user_id = ?", user_id)[0][0]
        order.append(user_id)
        data["players"][user_id] = {
            "name": name,
            "hp": 3,
            "actions": 0,
            "props": [],
            "kills": 0,
            "suicide": False,
            "surrender": False,
            "points_mult": 0,
            "effect_event": {},
        }
        mode_cfg.join(msg_manager, user_id)
    # endregion
    # region 检查人数
    seats = game["seats"]
    if len(order) >= seats:
        game["start"] = True
        game["expireTime"] = 0
        RegGameWork.bullet(msg_manager)
        random.shuffle(order)
        shooter = order[0]
        data["shooter"] = shooter
        data["players"][shooter]["actions"] = 1
        mode_cfg.start(msg_manager)
        game["reply"].update(
            {
                "info": [],
                "note": {
                    "ammo": False,
                    "round": False,
                },
                "only": "",
            }
        )
        situation(plugin_event, Proc, msg_manager, None)
    else:
        msg_reply = msg_manager.msg_format(
            "strMrGamePrep",
            {
                "tGameMode": mode_name,
                "tSeatsHas": len(order),
                "tSeatsMax": seats,
            },
        )
        plugin_event.reply(msg_reply)
        return
    # endregion


@commands.route("ob", "^(?:加入|进入)$")
def join_game(plugin_event, Proc, msg_manager, groups):
    game = msg_manager.val["game"]
    if not game or game["start"]:
        return
    mode_name = game["mode"]["name"]
    match_game(plugin_event, Proc, msg_manager, (mode_name, ""))
    return


@commands.route("prep", "^(?:退出|离开)$")
def exit_game(plugin_event, Proc, msg_manager, groups):
    user_id, game = msg_manager.user_id, msg_manager.val["game"]
    data = game["data"]
    order = data["order"]
    order.remove(user_id)
    del data["players"][user_id]
    if not order:
        game.clear()
        msg_reply = msg_manager.msg_format("strMrGameDismiss")
    else:
        msg_reply = msg_manager.msg_format("strMrGameRemain", {"tSeatsHas": len(order)})
    plugin_event.reply(msg_reply)
    return


# endregion
# region 对局操作
@commands.route("play", "^(吞|开|開)[槍|枪] *(\\d*)$")
def shoot(plugin_event, Proc, msg_manager, groups):
    user_id = msg_manager.user_id
    game, data, reply, tmp, modify, players, order, shooter, bullet = (
        RegGameWork.get_index(msg_manager)
    )
    if user_id != shooter:
        msg_reply = msg_manager.msg_format(
            "strMrGamblerTurn", {"tGamblerName": RegGameWork.get_name(game, shooter)}
        )
        plugin_event.reply(msg_reply)
        return
    if groups[0] == "吞":
        target = user_id
    elif not (target := get_target(game, groups[1])):
        return
    RegGameWork.shoot(msg_manager, target)
    msg_reply = RegGameWork.format_reply(msg_manager)
    plugin_event.reply(msg_reply)
    return


@commands.route("play", f"^(?:使用|) *({'|'.join(PropComp.list())}) *(\\d*)$")
def use_prop(plugin_event, Proc, msg_manager, groups):
    user_id, game = msg_manager.user_id, msg_manager.val["game"]
    game, data, reply, tmp, modify, players, order, shooter, bullet = (
        RegGameWork.get_index(msg_manager)
    )
    if user_id != shooter:
        msg_reply = msg_manager.msg_format(
            "strMrGamblerTurn", {"tGamblerName": RegGameWork.get_name(game, shooter)}
        )
        plugin_event.reply(msg_reply)
        return
    prop, target = groups[0], groups[1]
    if prop not in players[user_id]["props"]:
        msg_reply = msg_manager.msg_format("strMrGamblerNoProp", {"tPropName": prop})
        plugin_event.reply(msg_reply)
        return
    if not target:
        target = user_id
    elif not (target := get_target(game, target)):
        return
    if PropComp.use(msg_manager, prop, target):
        RegGameWork.remove_prop(game, user_id, prop)
    msg_reply = RegGameWork.format_reply(msg_manager)
    plugin_event.reply(msg_reply)
    return


@commands.route("play", "^投降$")
def surrender(plugin_event, Proc, msg_manager, groups):
    user_id = msg_manager.user_id
    game, data, reply, tmp, modify, players, order, shooter, bullet = (
        RegGameWork.get_index(msg_manager)
    )
    order.remove(user_id)
    players[user_id]["surrender"] = True
    if len(order) <= 1:
        RegGameWork.end_round(msg_manager)
    RegGameWork.reply_info(
        msg_manager,
        msg_manager.msg_format(
            "strMrGamblerSurrender",
            {"tGamblerName": RegGameWork.get_name(game, user_id)},
        ),
    )
    msg_reply = RegGameWork.format_reply(msg_manager)
    plugin_event.reply(msg_reply)
    return


@commands.route(COMMON_CMD, "^(?:局势|局勢)$")
def situation(plugin_event, Proc, msg_manager, groups):
    game = msg_manager.val["game"]
    if not game.get("start"):
        return
    game, data, reply, tmp, modify, players, order, shooter, bullet = (
        RegGameWork.get_index(msg_manager)
    )
    t_value = {}
    link = msg_manager.msg_format("strMrLink")
    # 赌徒
    pl_data_list = []
    for idx, user_id in enumerate(order):
        pl = players[user_id]
        props = []
        for prop, count in Counter(pl["props"]).items():
            props.append(
                msg_manager.msg_format(
                    "strMrPropOneNode" if count == 1 else "strMrPropManyNode",
                    {"tPropName": prop, "tPropCount": count},
                )
            )
        effects = []
        for effect, effect_data in pl["effect_event"].items():
            stacks = effect_data["stacks"]
            effects.append(
                msg_manager.msg_format(
                    "strMrEffectOneNode" if stacks == 1 else "strMrEffectManyNode",
                    {"tEffectName": effect, "tEffectStacks": stacks},
                )
            )
        pl_data = {
            "tGamblerIdx": idx + 1,
            "tGamblerName": pl["name"],
            "tGamblerHp": pl["hp"],
            "tGamblerProps": (
                link.join(props)
                if pl["props"]
                else msg_manager.msg_format("strMrPropNoneNode")
            ),
            "tGamblerEffect": (
                link.join(effects)
                if pl["effect_event"]
                else msg_manager.msg_format("strMrEffectNoneNode")
            ),
            "tGamblerActions": pl["actions"],
            "tGamblerKills": pl["kills"],
        }
        pl_data_list.append(msg_manager.msg_format("strMrGamblerData", pl_data))
    t_value.update({"tGamblerData": "".join(pl_data_list)})
    # 枪手
    t_value.update(
        {
            "tShooter": msg_manager.msg_format(
                "strMrGameShooter",
                {
                    "tGamblerIdx": order.index(shooter) + 1,
                    "tGamblerName": players[shooter]["name"],
                },
            )
        }
    )
    # 子弹
    t_value.update(
        {
            "tNowBulletType": msg_manager.msg_format(
                "strMrAmmoLive" if bullet else "strMrAmmoBlank"
            )
        }
    )
    t_value.update(
        {
            "tGameNowBullet": (
                msg_manager.msg_format("strMrGameNowBulletShow", t_value)
                if modify["bullet_show"]
                else msg_manager.msg_format("strMrGameNowBulletHide", t_value)
            )
        }
    )
    # 弹药
    ammo_live, ammo_blank = data["ammo_live"], data["ammo_blank"]
    t_value.update(
        {
            "tAmmoLiveCount": ammo_live,
            "tAmmoBlankCount": ammo_blank,
            "tAmmoCount": ammo_live + ammo_blank,
        }
    )
    t_value.update(
        {
            "tGameAmmo": (
                msg_manager.msg_format("strMrGameAmmoShow", t_value)
                if modify["ammo_show"]
                else msg_manager.msg_format("strMrGameAmmoHide", t_value)
            )
        }
    )
    # 死亡
    dead_list = [players[uid]["name"] for uid in players if uid not in order]
    t_value.update({"tDeadList": f"{link.join(dead_list)}"})
    t_value.update(
        {
            "tGameDeadList": (
                msg_manager.msg_format("strMrGameDeadList", t_value)
                if dead_list
                else msg_manager.msg_format("strMrGameDeadNone", t_value)
            )
        }
    )

    msg_reply = msg_manager.msg_format("strMrSituationResult", t_value)
    plugin_event.reply(msg_reply)
    return


# endregion
