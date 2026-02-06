import random
import time
from collections import Counter

from AmorLib import DataBase, is_master, get_group_role

from . import DB_PATH
from .Core.doc import helpdoc
from .Core.cmop import ModeComp, PropComp
from .Core.work import GameWork
from .Core.cmd import commands, COMMON_CMD


# region 设置
helpdoc.append_cmd("恶赌(on,off) #游戏开关, 要求管理权限")


@commands.route("setting", "^[惡恶]赌 *(on|off|ON|OFF|)$")
def enabled(plugin_event, Proc, group_id, msg_groups):
    if is_master(plugin_event) or get_group_role(plugin_event) != "member":
        game_enabled = msg_groups[0]
    else:
        game_enabled = None
    group_reply = ""
    main_enabled = Proc.database.get_basic_config(
        "MammonRoulette",
        "main_enabled",
        default_value=1,
        pkl=False,
    )
    if game_enabled:
        game_enabled = game_enabled.lower() == "on"
        if group_id:
            Proc.database.set_group_config(
                "MammonRoulette",
                "game_enabled",
                int(game_enabled),
                "qq",
                group_id,
                None,
                pkl=False,
            )
            group_reply = (
                f"\n[{group_id}] -〈群开关〉-> {'开' if game_enabled else '关'}"
            )
        else:
            Proc.database.set_basic_config(
                "MammonRoulette", "main_enabled", game_enabled, pkl=False
            )
            main_enabled = game_enabled
    elif group_id:
        group_enabled = game_enabled = Proc.database.get_group_config(
            "MammonRoulette",
            "main_enabled",
            "qq",
            group_id,
            host_id=None,
            default_value=1,
            pkl=False,
        )
        group_reply = f"\n[{group_id}] -〈群开关〉-> {'开' if group_enabled else '关'}"
    return f"〖确认〗\n [恶魔轮盘] -〈总开关〉-> {'开' if main_enabled else '关'}{group_reply}"


# endregion


# region 资料
helpdoc.append_cmd("(名称)签署[生死状,契约] #注册或修改名称")


@commands.route(COMMON_CMD, "^(.+)(?:签署|簽署)(?:生死状|契约|生死狀|契約)$")
def signed(game, user_id, group_id, msg_groups):
    name = msg_groups[0]
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
    return f"{name}在生死狀簽下姓名。", False


helpdoc.append_cmd("恶魔名片(数值,留空) #查看自己或他人的资料")


@commands.route(COMMON_CMD, "^[惡恶]魔名片(\\d*)$")
def card(game, user_id, group_id, msg_groups):
    target = msg_groups[0] if msg_groups[0] != "" else user_id
    with DataBase(DB_PATH) as db:
        gambler_info = db.select("gambler", "*", "user_id = ?", target)
        if not gambler_info:
            return "只是个没有战绩的观众。"
        gambler_info = gambler_info[0]
        gambler_rank = db.select(
            "gambler", "COUNT(*)", "points > ?", gambler_info["points"]
        )[0][0]
    wins, losses = int(gambler_info["wins"]), int(gambler_info["losses"])
    total = wins + losses
    win_rate = f"{ round(wins/total*100 ,2) } %" if total > 0 else "未參與過輪盤"
    return (
        f"『惡魔資料卡』"
        f"\n真名: {gambler_info['name']}"
        f"\n排行: {gambler_rank}"
        f"\n賞金: {gambler_info['points']}"
        f"\n槍下亡魂: {gambler_info['kills']}"
        f"\n自取滅亡: {gambler_info['suicide']}"
        f"\n取勝: {wins} | 戰敗: {losses}"
        f"\n奪標率: {win_rate}"
    ), False


helpdoc.append_cmd("恶魔(赏金,杀戮,自杀,留空)[排行,榜] #查询排行, 留空默认查询赏金榜单")


@commands.route(COMMON_CMD, "^[恶惡]魔(赏金|杀戮|自杀|)(?:排行|榜)(\\d*)$")
def leaderboard(game, user_id, group_id, msg_groups):
    ranking_page = int(msg_groups[1] or 1) * 10 - 10
    ranking_type = msg_groups[0] or "赏金"
    if ranking_type == "赏金":
        ranking = "points"
    elif ranking_type == "杀戮":
        ranking = "kills"
    else:
        ranking = "suicide"
    with DataBase(DB_PATH) as db:
        gambler_list = db.select(
            "gambler",
            f"name, {ranking}",
            order=f"{ranking} DESC",
            limit=10,
            offset=ranking_page,
        )
        if not gambler_list:
            return
        gambler_total = db.select("gambler", "COUNT(*)")
    top_list = "\n".join(
        f"[{idx+1}] {gambler_info['name']}| {gambler_info[ranking]}"
        for idx, gambler_info in enumerate(gambler_list)
    )
    return (
        f"『惡魔{ranking_type}榜』\n"
        f"{top_list}\n"
        "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁\n"
        f"排名 {ranking_page+1}-{ranking_page+10} | 总计上榜恶魔 {gambler_total[0][0]}"
    ), False


# endregion


# region 对局操作

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


helpdoc.append_cmd(
    "(模式名)匹配 #以默认人数匹配对局, 满人自动开启"
    "\n(模式名)匹配(数值)p #以自定义人数匹配对局"
)


@commands.route("ob", f"^({'|'.join(ModeComp.list())})匹配(?:(\\d+)p)?$")
def match(game, user_id, group_id, msg_groups):
    # 自动注册
    with DataBase(DB_PATH) as db:
        gambler_info = db.select("gambler", "user_id", "user_id = ?", user_id)
    if not gambler_info:
        name = f"{random.choice(poker['suits'])+random.choice(poker['ranks'])}"
        signed(None, user_id, group_id, (name,))
    # 读取游戏数据
    mode_name, seats = msg_groups[0], msg_groups[1]
    mode_cfg = ModeComp.get(mode_name)
    seats_min, seats_max, seats_def = (
        mode_cfg.seats.min,
        mode_cfg.seats.max,
        mode_cfg.seats.default,
    )
    seats = int(seats) if seats else seats_def
    if not (seats_min <= seats <= seats_max):
        return f"非法人数, {mode_name}模式限定人数为[{seats_min},{seats_max}] Defaults to {seats_def}."
    # 清除过期对局
    expireTime = int(time.time())
    if expireTime > game.get("expireTime", 0) and not game.get("start", False):
        game.clear()
    # 构建对局
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
        return "对局进行中，无法加入。"
    elif mode_name != game["mode"]:
        return f"已经开设{game['mode']}对局。"

    # 添加玩家
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

    # 检查人数
    pl_num = game["seats"]
    if len(game["order"]) >= pl_num:
        game["start"] = True
        game["expireTime"] = 0
        GameWork.bullet(game)
        random.shuffle(game["order"])
        shooter = game["order"][0]
        game["shooter"] = shooter
        game["players"][shooter]["actions"] = 1
        mode_cfg.start(game)
        game["reply"].update({"info": [], "ammo": "", "shooter": ""})
        reply, _ = situation(game, None, None, None)
    else:
        reply = f"{game['mode']}對局靜候惡魔[{len(game['order'])}/{pl_num}]."
    return reply, True


helpdoc.append_cmd("退出 #退出匹配")


@commands.route("prep", "^退出$")
def exit(game, user_id, group_id, msg_groups):
    game["order"].remove(user_id)
    del game["players"][user_id]
    if not game["order"]:
        game.clear()
        reply = "你已退出，游戏解散"
    else:
        reply = f"你已退出，剩余：{len(game['order'])}人"
    return reply, True


helpdoc.append_cmd(
    "(吞或开)枪(目标) #对目标射击, 可用qq号或序号指定目标, 留空默认下一顺位"
)


@commands.route("play", "^(吞|开|開)[槍|枪] *(\\d*)$")
def shoot(game, user_id, group_id, msg_groups):
    if game["shooter"] != user_id:
        return f"現在是{GameWork.get_name(game)}的回合."
    # 确定目标
    target = msg_groups[1]
    if msg_groups[0] == "吞":
        target = user_id
    elif not (target := get_target(game, target)):
        return
    GameWork.shoot(game, target)
    return GameWork.reply(game), True


helpdoc.append_cmd("[使用,留空](道具名) (目标) #对目标使用道具, 可用qq号或序号指定目标")

prop_list = PropComp.list()


@commands.route("play", f"^(?:使用|) *({'|'.join(prop_list)}) *(\\d*)$")
def use_prop(game, user_id, group_id, msg_groups):
    if game["shooter"] != user_id:
        return f"現在是{GameWork.get_name(game)}的回合."
    prop, target = msg_groups[0], msg_groups[1]
    pl = game["players"][user_id]
    if prop not in pl["props"]:
        return "未擁有該道具."
    if not target:
        target = user_id
    elif not (target := get_target(game, target)):
        return
    if PropComp.use(game, prop, target):
        GameWork.prop_remove(game, user_id, prop)
    return GameWork.reply(game), True


helpdoc.append_cmd("局势 #查询当前游戏局势信息")


@commands.route(("ob", "prep", "play", "dead"), "^(?:局势|局勢)$")
def situation(game, user_id, group_id, msg_groups):
    order = game["order"]
    players = game["players"]
    shooter = game["shooter"]
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
    return (
        "".join(pl_list) + "▁▁▁▁▁▁▁▁▁▁▁▁▁▁\n"
        f"槍手:〔{order.index(shooter)+1}〕{players[shooter]['name']}"
        + ammo
        + bullet
        + dead
    ), False


helpdoc.append_cmd("投降 #以自杀的形式结束")


@commands.route("play", "^投降$")
def surrender(game, user_id, group_id, msg_groups):
    game["reply"]["info"].append(f"{GameWork.get_name(game,user_id)}被清除。")
    GameWork.dead(game, user_id, True)
    if len(game["order"]) <= 1:
        GameWork.end_round(game)
    return GameWork.reply(game), True


# endregion
