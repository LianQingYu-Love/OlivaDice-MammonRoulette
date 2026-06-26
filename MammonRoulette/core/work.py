# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/core/work.py
@Author    :    LianQingYu-Love恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

import random
import re

from AmorLib import DataBase, STRING_ROW

from .cmop import ModeComp, PropComp, EffectComp
from .. import DB_PATH


class RegGameWork:
    # region Base
    @staticmethod
    def get_name(game, user_id: str | None = None) -> str:  # 获取玩家昵称
        data = game["data"]
        if not user_id:
            user_id = data["shooter"]
        return data["players"][user_id]["name"]

    @staticmethod
    def get_index(msg_manager):
        game: dict = msg_manager.val["game"]
        data: dict = game["data"]
        reply: dict = game["reply"]
        tmp: dict = game["tmp"]
        modify: dict = data["modify"]
        players: dict = data["players"]
        order: list = data["order"]
        shooter: str = data["shooter"]
        bullet: bool = data["bullet"]
        return game, data, reply, tmp, modify, players, order, shooter, bullet

    @staticmethod
    def format_reply(msg_manager) -> str:  # 格式化回复消息
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        if not reply["only"]:
            info, note = reply["info"], reply["note"]
            t_value = {}
            t_value.update({"tInfo": "\n".join(info)})
            if note["ammo"]:
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
                            else msg_manager.msg_format(
                                "strMrGameNowBulletHide", t_value
                            )
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
            if note["shooter"]:
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
            msg_reply = msg_manager.msg_format("strGameReplyInfo", t_value)
            if note["ammo"] or note["shooter"]:
                msg_reply += "\n" + msg_manager.msg_format("strGameReplyNote", t_value)
        else:
            msg_reply = reply["only"]
        reply.update(
            {
                "info": [],
                "note": {
                    "ammo": False,
                    "shooter": False,
                },
                "only": "",
            }
        )
        return msg_reply

    # endregion
    # region 事件
    @staticmethod
    def get_effect_stacks(game, effect, target):
        return game["data"]["players"][target]["effect_event"].get(effect, 0)

    @staticmethod
    def create_prop_event(game, prop, moments: STRING_ROW | str):
        moments = (moments,) if type(moments) == str else moments
        for moment in moments:
            game["data"]["prop_event"][moment].append(prop)
        return

    @staticmethod
    def create_effect_event(game, effect, target, stacks: int = 1):
        effect_event = game["data"]["players"][target]["effect_event"]
        effect_event[effect] = effect_event.get(effect, 0) + stacks
        return

    @staticmethod
    def remove_prop_event(game, prop, moment: STRING_ROW | str):
        moments = (moment,) if type(moment) == str else moment
        for moment in moments:
            game["data"]["prop_event"][moment].remove(prop)
        return

    @staticmethod
    def remove_effect_event(game, effect, target, stacks: int = 1):
        effect_event = game["data"]["players"][target]["effect_event"]
        effect_event[effect] -= stacks
        if effect_event[effect] <= 0:
            del effect_event[effect]
        return

    @staticmethod
    def handle_event(msg_manager, moment, **kwargs):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        tmp.update(kwargs)
        prop_event = data["prop_event"][moment]
        for prop in reversed(prop_event):
            if PropComp.trigger(msg_manager, prop, moment):
                prop_event.remove(prop)
        for target in players:
            effect_event = players[target]["effect_event"]
            for effect in list(effect_event.keys()):
                stacks = effect_event[effect]
                if EffectComp.trigger(msg_manager, effect, moment, target, stacks):
                    del effect_event[effect]
        ModeComp.trigger(msg_manager, moment)
        return

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
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        prop_pool = prop_pool or game["mode"]["props"]["pool"]
        draw_props = []
        for _ in range(count):
            prop = random.choice(prop_pool)
            if not cls.get_prop(game, user_id, prop):
                break
            draw_props.append(prop)
        if draw_props:
            link = msg_manager.msg_format("strMrLink")
            reply["info"].append(
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
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        if data["ammo_live"] < 1:
            ammo_live, ammo_blank = cls.reload(msg_manager)
        else:
            ammo_live, ammo_blank = data["ammo_live"], data["ammo_blank"]
        ammo = ammo_live + ammo_blank
        data["bullet"] = random.randint(1, ammo) > ammo_blank
        reply["note"]["ammo"] = True
        return

    @classmethod
    def reload(cls, msg_manager):  # 装弹
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        cls.handle_event(msg_manager, "reload")
        ammo_live, ammo_blank = random.randint(1, 4), random.randint(1, 4)
        data["ammo_live"], data["ammo_blank"] = ammo_live, ammo_blank
        reply["info"].append(msg_manager.msg_format("strMrGameAmmoRanOut"))
        return ammo_live, ammo_blank

    @classmethod
    def shoot(cls, msg_manager, target):  # 开枪
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        is_attack_me = target == shooter
        dmg_type = "shoot"
        murderer = shooter
        cls.handle_event(
            msg_manager,
            "shoot",
            target=target,
            dmg=modify["dmg"],
            dmg_type=dmg_type,
            is_attack_me=is_attack_me,
            murderer=murderer,
        )
        target, dmg, is_attack_me, murderer = (
            tmp["target"],
            tmp["dmg"],
            tmp["is_attack_me"],
            tmp["murderer"],
        )
        pl_target, pl_shooter = (
            players[target],
            players[shooter],
        )
        if data["bullet"]:
            cls.damage(msg_manager, target, dmg, murderer)
            data["ammo_live"] -= 1
            hp_before, hp_now = tmp["hp_before"], tmp["hp_now"]
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
            if is_attack_me:
                pl_shooter["actions"] += 1
            reply["info"].append(
                msg_manager.msg_format(
                    "strMrGamblerWasAmmoBlankShot",
                    {
                        "tGamblerName": pl_target["name"],
                        "tHpBefore": pl_target["hp"],
                        "tHpNow": pl_target["hp"],
                    },
                )
            )
        cls.bullet(msg_manager)
        cls.end_round(msg_manager)
        return

    @classmethod
    def damage(cls, msg_manager, target, dmg, murderer=None):  # 受伤
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        dmg_type = tmp.get("dmg_type", "shoot")
        cls.handle_event(
            msg_manager,
            "damage",
            target=target,
            dmg=dmg,
            murderer=murderer,
            dmg_type=dmg_type,
        )
        target, dmg, murderer, dmg_type = (
            tmp["target"],
            tmp["dmg"],
            tmp["murderer"],
            tmp["dmg_type"],
        )
        pl_target = players[target]
        tmp["hp_before"] = pl_target["hp"]
        pl_target["hp"] -= dmg
        tmp["hp_now"] = pl_target["hp"]
        if pl_target["hp"] <= 0:
            cls.dead(msg_manager, target, murderer)
        return

    @classmethod
    def dead(cls, msg_manager, target, murderer):  # 死亡
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        cls.handle_event(msg_manager, "dead", target=target, murderer=murderer)
        target, murderer = tmp["target"], tmp["murderer"]
        if not murderer:
            murderer = shooter
        pl_target, pl_murderer = (
            players[target],
            players[murderer],
        )
        name = pl_target["name"]
        if tmp["is_attack_me"]:
            pl_target["suicide"] = True
            reply["info"].append(
                msg_manager.msg_format("strMrGamblerSuicide", {"tGamblerName": name})
            )
        else:
            pl_murderer["kills"] += 1
            pl_target["suicide"] = False
            reply["info"].append(
                msg_manager.msg_format(
                    "strMrGamblerKilled",
                    {"tGamblerName": name, "tMurdererName": pl_murderer["name"]},
                )
            )
        order.remove(target)
        if len(order) == 1:
            reply["only"] = msg_manager.msg_format(
                "strMrGameEnd", {"tWinnerName": cls.get_name(game, order[0])}
            )
            cls.over(msg_manager)
        if len(order) < 1:
            reply["only"] = msg_manager.msg_format("strMrGameTied")
            cls.over(msg_manager)
        return

    @classmethod
    def end_round(cls, msg_manager):  # 回合结束
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        cls.handle_event(msg_manager, "end_round")
        pl_shooter = players[shooter]
        pl_shooter["actions"] -= 1
        if pl_shooter["actions"] < 1:
            cls.switch(msg_manager)
        return

    @classmethod
    def switch(cls, msg_manager):  # 换人
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        for _ in range(game["seats"] * 10):
            shooter = order[(order.index(shooter) + 1) % len(order)]
            pl_shooter = players[shooter]
            pl_shooter["actions"] += 1
            if pl_shooter["actions"] > 0:
                break
        if shooter != data["shooter"]:
            data["shooter"] = shooter
            pl_shooter = players[shooter]
            reply["note"]["shooter"] = True
            cls.handle_event(msg_manager, "switch")
        return

    @classmethod
    def over(cls, msg_manager):  # 结算
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        with DataBase(DB_PATH) as db:
            for pl in players.keys():
                pl_target = players[pl]
                mult = pl_target["points_mult"] + pl_target["kills"]
                if pl not in order:
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
