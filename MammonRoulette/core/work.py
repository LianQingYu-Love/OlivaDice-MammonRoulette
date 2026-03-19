import random
import re

from AmorLib import DataBase, STRING_ROW

from .cmop import ModeComp, PropComp
from .. import DB_PATH


class RegGameWork:
    @staticmethod
    def get_name(game, user_id: str | None = None):  # 获取玩家昵称
        data = game["data"]
        if not user_id:
            user_id = data["shooter"]
        return data["players"][user_id]["name"]

    @staticmethod
    def format_reply(game):  # 格式化回复消息
        game_reply = game["reply"]
        if not game_reply["only"]:
            info, note = game_reply["info"], game_reply["note"]
            extra = [note[key] for key in ["ammo", "shooter"] if note[key]]
            if extra:
                info.extend(["▁▁▁▁▁▁▁▁▁▁▁▁▁▁"] + extra)
            reply = "\n".join(info)
            reply = re.sub(r"\n\n+", "\n", reply)
        else:
            reply = game_reply["only"]
        game_reply.update(
            {
                "info": [],
                "note": {
                    "ammo": "",
                    "shooter": "",
                },
                "only": "",
            }
        )
        return reply

    # region 事件
    @staticmethod
    def create_prop_event(game, callback, moments: STRING_ROW | str):
        moments = (moments,) if type(moments) == str else moments
        for moment in moments:
            game["data"]["prop_event"][moment].append(callback)

    @staticmethod
    def handle_event(msg_manager, moment, **kwargs):
        game = msg_manager.val["game"]
        game["tmp"].update(kwargs)
        prop_event = game["data"]["prop_event"][moment]
        for prop in prop_event:
            if PropComp.trigger(msg_manager, prop, moment):
                prop_event.remove(prop)
        ModeComp.trigger(msg_manager, moment)

    # endregion
    # region 道具
    @staticmethod
    def get_prop(game, user_id, prop):  # 获取道具
        mode_props = game["mode"]["props"]
        pl_props = game["data"]["players"][user_id]["props"]
        if len(pl_props) >= mode_props["limit"]:
            return False
        elif prop in mode_props["ban"]:
            prop = random.choice(mode_props["pool"])
        pl_props.append(prop)
        return True

    @staticmethod
    def remove_prop(game, user_id, prop):  # 删除道具
        pl_props = game["data"]["players"][user_id]["props"]
        if prop not in pl_props:
            return False
        pl_props.remove(prop)
        return True

    @classmethod
    def draw_prop(cls, msg_manager, user_id, count, prop_pool=None):  # 抽取道具
        game = msg_manager.val["game"]
        prop_pool = prop_pool or game["mode"]["props"]["pool"]
        draw_props = []
        for _ in range(count):
            prop = random.choice(prop_pool)
            if not cls.get_prop(game, user_id, prop):
                break
            draw_props.append(prop)
        if draw_props:
            link = msg_manager.msg_format("strMrLink")
            game["reply"]["info"].append(
                msg_manager.msg_format(
                    "strMrGamblerDrawnProps",
                    {
                        "tGamblerName": cls.get_name(game, user_id),
                        "tDrawnProps": link.join(draw_props),
                    },
                )
            )
        return

    # endregion
    # region action
    @classmethod
    def bullet(cls, msg_manager):  # 刷新子弹
        game = msg_manager.val["game"]
        data = game["data"]
        if data["ammo_live"] < 1:
            ammo_live, ammo_blank = cls.reload(msg_manager)
        else:
            ammo_live, ammo_blank = data["ammo_live"], data["ammo_blank"]

        ammo = ammo_live + ammo_blank
        data["bullet"] = random.randint(1, ammo) > ammo_blank

        modify = data["modify"]
        ammo_reply = []
        if modify["ammo_show"]:
            t_value = {
                "tAmmoLiveCount": ammo_live,
                "tAmmoBlankCount": ammo_blank,
                "tAmmoCount": ammo,
            }
            ammo_reply.append(
                msg_manager.msg_format("strMrGameAmmoShow", t_value)
                if modify["ammo_show"]
                else msg_manager.msg_format("strMrGameAmmoHide", t_value)
            )
        if modify["bullet_show"]:
            t_value = {
                "tBulletType": msg_manager.msg_format(
                    "strMrAmmoLive" if data["bullet"] else "strMrAmmoBlank"
                ),
            }
            ammo_reply.append(
                msg_manager.msg_format("strMrGameNowBulletShow", t_value)
                if modify["bullet_show"]
                else msg_manager.msg_format("strMrGameNowBulletHide", t_value)
            )
        game["reply"]["note"]["ammo"] = "\n".join(ammo_reply)
        return

    @classmethod
    def reload(cls, msg_manager):  # 装弹
        game = msg_manager.val["game"]
        data = game["data"]
        cls.handle_event(msg_manager, "reload")
        ammo_live, ammo_blank = random.randint(1, 4), random.randint(1, 4)
        data["ammo_live"], data["ammo_blank"] = ammo_live, ammo_blank
        game["reply"]["info"].append(msg_manager.msg_format("strMrGameAmmoRanOut"))
        return ammo_live, ammo_blank

    @classmethod
    def shoot(cls, msg_manager, target):  # 开枪
        game = msg_manager.val["game"]
        data, reply, tmp = game["data"], game["reply"], game["tmp"]
        is_attack_me = target == data["shooter"]
        cls.handle_event(msg_manager, "shoot", target=target, is_attack_me=is_attack_me)
        target = tmp["target"]
        pl_target, pl_shooter = (
            data["players"][target],
            data["players"][data["shooter"]],
        )
        hp_before = pl_target["hp"]
        if data["bullet"]:
            cls.damage(msg_manager, target, data["modify"]["dmg"])
            hp_now = pl_target["hp"]
            data["ammo_live"] -= 1
            reply["info"].append(
                msg_manager.msg_format(
                    "strMrGamblerWasAmmoLiveShot",
                    {
                        "tGamblerName": pl_target["name"],
                        "tHpBefore": hp_before,
                        "tHpNow": hp_now,
                    },
                )
            )
        else:
            data["ammo_blank"] -= 1
            if tmp["is_attack_me"]:
                pl_shooter["actions"] += 1
            reply["info"].append(
                msg_manager.msg_format(
                    "strMrGamblerWasAmmoBlankShot",
                    {
                        "tGamblerName": pl_target["name"],
                        "tHpBefore": hp_before,
                        "tHpNow": hp_before,
                    },
                )
            )
        cls.bullet(msg_manager)
        cls.end_round(msg_manager)
        return

    @classmethod
    def damage(cls, msg_manager, target, dmg):  # 受伤
        game = msg_manager.val["game"]
        data, reply = game["data"], game["reply"]
        cls.handle_event(msg_manager, "damage", target=target, dmg=dmg)
        target, dmg = game["tmp"]["target"], game["tmp"]["dmg"]
        pl_target, pl_shooter = (
            data["players"][target],
            data["players"][data["shooter"]],
        )
        name = pl_target["name"]
        pl_target["hp"] -= dmg
        if pl_target["hp"] <= 0:
            if game["tmp"]["is_attack_me"]:
                pl_target["suicide"] = True
                reply["info"].append(
                    msg_manager.msg_format(
                        "strMrGamblerSuicide", {"tGamblerName": name}
                    )
                )
            else:
                pl_shooter["kills"] += 1
                pl_target["suicide"] = False
                reply["info"].append(
                    msg_manager.msg_format(
                        "strMrGamblerKilled",
                        {"tGamblerName": name, "tMurdererName": pl_shooter["name"]},
                    )
                )
            data["order"].remove(target)
        return

    @classmethod
    def end_round(cls, msg_manager):  # 回合结束
        game = msg_manager.val["game"]
        data = game["data"]
        order = data["order"]
        if len(order) > 1:
            cls.handle_event(msg_manager, "end_round")
            pc_shooter = data["players"][data["shooter"]]
            pc_shooter["actions"] -= 1
            if pc_shooter["actions"] < 1:
                cls.switch(msg_manager)
        else:
            game["reply"]["only"] = msg_manager.msg_format(
                "strMrGameEnd", {"tWinnerName": cls.get_name(game, order[0])}
            )
            cls.over(game)
        return

    @classmethod
    def switch(cls, msg_manager):  # 换人
        game = msg_manager.val["game"]
        data = game["data"]
        order, shooter = data["order"], data["shooter"]
        for _ in range(game["seats"] * 10):
            shooter = order[(order.index(shooter) + 1) % len(order)]
            pc_shooter = data["players"][shooter]
            pc_shooter["actions"] += 1
            if pc_shooter["actions"] > 0:
                break
        if shooter != data["shooter"]:
            data["shooter"] = shooter
            pc_shooter = data["players"][shooter]
            game["reply"]["note"]["shooter"] = msg_manager.msg_format(
                "strMrGamblerTurn", {"tGamblerName": pc_shooter["name"]}
            )
            cls.handle_event(msg_manager, "switch")
        return

    @classmethod
    def over(cls, game):  # 结算
        data = game["data"]
        players = data["players"]
        with DataBase(DB_PATH) as db:
            for pl in players.keys():
                pl_target = players[pl]
                mult = pl_target["points_mult"] + pl_target["kills"]
                if pl not in data["order"]:
                    mult -= 1
                    wl = "losses"
                else:
                    mult += 1
                    wl = "wins"
                db.update(
                    "gambler",
                    {
                        "points": game["mode"]["points"] * mult,
                        "kills": pl_target["kills"],
                        "suicide": 1 if pl_target["suicide"] else 0,
                        "surrender": 1 if pl_target["surrender"] else 0,
                        wl: 1,
                    },
                    "user_id = ?",
                    pl,
                    increment=("points", "kills", "suicide", wl),
                )
        game["over"] = True
        return

    # endregion
