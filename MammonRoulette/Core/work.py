# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/core/work.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

import MammonRoulette as MR

import random

from AmorLib import DataBase

from .. import config


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
    def is_bot(game, user_id: str) -> bool:  # 是否为AI玩家
        return game["data"]["players"][user_id]["ai_model"] != None

    @staticmethod
    def reply_info(msg_manager, info: str):
        reply = msg_manager.val["game"]["reply"]
        reply["info"].append(info)

    @staticmethod
    def format_reply(msg_manager) -> str:  # 格式化回复消息
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        if not reply["only"]:
            info, note = reply["info"], reply["note"]
            t_value = {}
            t_value.update({"tInfo": "\n".join(info)})
            if note["ammo"]:
                # 子弹
                t_value.update({"tNowBulletType": msg_manager.msg_format("strMrAmmoLive" if bullet else "strMrAmmoBlank")})
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
            if note["round"]:
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
            if not game["over"] and (note["ammo"] or note["round"]):
                msg_reply += "\n" + msg_manager.msg_format("strGameReplyNote", t_value)
        else:
            msg_reply = reply["only"]
        reply.update(
            {
                "info": [],
                "note": {
                    "ammo": modify["ammo_show"] or modify["bullet_show"],
                    "round": False,
                },
                "only": "",
            }
        )
        return msg_reply

    # endregion
    # region 事件
    @staticmethod
    def get_prop_data(msg_manager, prop_id: int | None = None, prop_name: str | None = None):
        game = msg_manager.val["game"]
        search = []
        if prop_id:
            for prop_data in game["data"]["prop_event"]:
                if prop_data["id"] == prop_id:
                    search.append(prop_data)
        if prop_name:
            for prop_data in game["data"]["prop_event"]:
                if prop_data["name"] == prop_name:
                    search.append(prop_data)
        return search

    @staticmethod
    def get_effect_stacks(msg_manager, effect: str, target: str):
        return msg_manager.val["game"]["data"]["players"][target]["effect_event"].get(effect, 0)

    @staticmethod
    def create_prop_event(msg_manager, prop_data):
        prop_data["id"] = id(prop_data)
        msg_manager.val["game"]["data"]["prop_event"].append(prop_data)

    @staticmethod
    def create_effect_event(msg_manager, effect: str, effect_data: dict, target: str):
        msg_manager.val["game"]["data"]["players"][target]["effect_event"][effect] = effect_data

    @staticmethod
    def remove_prop_event(msg_manager, prop_id: int | None = None, prop_name: str | None = None):
        if not prop_id and not prop_name:
            return
        search = prop_id if prop_id else prop_name
        search_key = "id" if prop_id else "name"
        prop_event = msg_manager.val["game"]["data"]["prop_event"]
        for prop_data in prop_event:
            if prop_data[search_key] == search:
                MR.Core.comp.PropComp.uninstall(msg_manager, prop_data["name"], prop_data)
                prop_event.remove(prop_data)
        return

    @staticmethod
    def remove_effect_event(msg_manager, effect, target, stacks: int = 0):
        effect_event = msg_manager.val["game"]["data"]["players"][target]["effect_event"]
        effect_data = effect_event[effect]
        effect_data["stacks"] -= stacks
        if effect_data["stacks"] <= 0 or stacks == 0:
            MR.Core.comp.EffectComp.uninstall(msg_manager, effect)
            del effect_event[effect]
        return

    @classmethod
    def handle_event(cls, msg_manager, moment, **kwargs):
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        tmp.update(kwargs)
        prop_event = data["prop_event"]
        for prop_data in reversed(prop_event):
            if MR.Core.comp.PropComp.trigger(msg_manager, prop_data["name"], moment, prop_data):
                cls.remove_prop_event(msg_manager, prop_data["id"])
        for target in players:
            effect_event = players[target]["effect_event"]
            for effect in list(effect_event.keys()):
                if MR.Core.comp.EffectComp.trigger(msg_manager, effect, moment, target, effect_event[effect]):
                    cls.remove_effect_event(msg_manager, effect, target, 0)
        MR.Core.comp.ModeComp.trigger(msg_manager, moment)
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
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        prop_pool = prop_pool or game["mode"]["props"]["pool"]
        draw_props = []
        for _ in range(count):
            prop = random.choice(prop_pool)
            if not cls.get_prop(game, user_id, prop):
                break
            draw_props.append(prop)
        if draw_props:
            link = msg_manager.msg_format("strMrLink")
            cls.reply_info(
                msg_manager,
                msg_manager.msg_format(
                    "strMrGamblerDrawnProps",
                    {
                        "tGamblerName": cls.get_name(game, user_id),
                        "tDrawnProps": link.join(draw_props),
                    },
                ),
            )
        return

    # endregion
    # region action
    @classmethod
    def join(cls, msg_manager, user_id, ai_model=None):
        """添加一名玩家."""
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        if ai_model is None:
            with DataBase(config.DB_PATH) as db:
                name = db.select("gambler", "name", "user_id = ?", user_id)[0][0]
        else:
            name = ai_model
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
            "ai_model": ai_model,
        }
        MR.Core.comp.ModeComp.get(game["mode"]["name"]).join(msg_manager, user_id)
        return

    @classmethod
    def start(cls, msg_manager):
        """对局开始"""
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        game["start"] = True
        game["expireTime"] = 0
        cls.bullet(msg_manager)
        random.shuffle(order)
        shooter = order[0]
        data["shooter"] = shooter
        data["players"][shooter]["actions"] = 1
        MR.Core.comp.ModeComp.get(game["mode"]["name"]).start(msg_manager)
        reply.update(
            {
                "info": [],
                "note": {
                    "ammo": modify["ammo_show"] or modify["bullet_show"],
                    "round": False,
                },
                "only": "",
            }
        )
        modify["ai_flag"] = cls.is_bot(game, shooter)
        MR.Core.comp.BotComp.action(msg_manager)
        return

    @classmethod
    def bullet(cls, msg_manager):  # 刷新子弹
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        if game["over"]:
            return
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
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        cls.handle_event(msg_manager, "reload")
        ammo_live, ammo_blank = random.randint(1, 4), random.randint(1, 4)
        data["ammo_live"], data["ammo_blank"] = ammo_live, ammo_blank
        cls.reply_info(msg_manager, msg_manager.msg_format("strMrGameAmmoRanOut"))
        return ammo_live, ammo_blank

    @classmethod
    def shoot(cls, msg_manager, target):  # 开枪
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        dmg_type = ""
        is_attack_me = target == shooter
        murderer = shooter
        consume_action = None
        cls.handle_event(
            msg_manager,
            "shoot",
            target=target,
            dmg=modify["dmg"],
            dmg_type=dmg_type,
            is_attack_me=is_attack_me,
            murderer=murderer,
            consume_action=consume_action,
        )
        target, dmg, dmg_type, is_attack_me, murderer, consume_action = (
            tmp["target"],
            tmp["dmg"],
            tmp["dmg_type"],
            tmp["is_attack_me"],
            tmp["murderer"],
            tmp["consume_action"],
        )
        pl_target = players[target]
        if data["bullet"]:
            if consume_action is None:
                consume_action = 1
            tmp["consume_action"] = consume_action
            data["ammo_live"] -= 1
            cls.damage(msg_manager, target, dmg, murderer)
            hp_before, hp_now = tmp["hp_before"], tmp["hp_now"]
            if tmp["hp_now"] > 0:
                cls.reply_info(
                    msg_manager,
                    msg_manager.msg_format(
                        "strMrGamblerWasAmmoLiveShot",
                        {
                            "tGamblerName": pl_target["name"],
                            "tHpBefore": hp_before,
                            "tHpNow": hp_now,
                        },
                    ),
                )
        else:
            data["ammo_blank"] -= 1
            if consume_action is None:
                consume_action = 0 if is_attack_me else 1
            tmp["consume_action"] = consume_action
            cls.reply_info(
                msg_manager,
                msg_manager.msg_format(
                    "strMrGamblerWasAmmoBlankShot",
                    {
                        "tGamblerName": pl_target["name"],
                        "tHpBefore": pl_target["hp"],
                        "tHpNow": pl_target["hp"],
                    },
                ),
            )
        cls.bullet(msg_manager)
        cls.end_round(msg_manager)
        return

    @classmethod
    def damage(cls, msg_manager, target, dmg, murderer):  # 受伤
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        if game["over"]:
            return
        dmg_type = tmp.get("dmg_type", "")
        check_over = tmp.get("check_over", True)
        cls.handle_event(
            msg_manager,
            "damage",
            target=target,
            dmg=dmg,
            murderer=murderer,
            dmg_type=dmg_type,
            check_over=check_over,
        )
        target, dmg, murderer, dmg_type, check_over = (
            tmp["target"],
            tmp["dmg"],
            tmp["murderer"],
            tmp["dmg_type"],
            tmp["check_over"],
        )
        pl_target = players[target]
        tmp["hp_before"] = pl_target["hp"]
        pl_target["hp"] -= dmg
        tmp["hp_now"] = pl_target["hp"]
        if pl_target["hp"] <= 0 and target in order:
            cls.dead(msg_manager, target, murderer)
        return

    @classmethod
    def dead(cls, msg_manager, target, murderer):  # 死亡
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        if game["over"]:
            return
        check_over = tmp.get("check_over", True)
        cls.handle_event(msg_manager, "dead", target=target, murderer=murderer, check_over=check_over)
        target, murderer, check_over = tmp["target"], tmp["murderer"], tmp["check_over"]
        if not murderer:
            murderer = shooter
        pl_target, pl_murderer = (
            players[target],
            players[murderer],
        )
        name = pl_target["name"]
        if target == murderer:
            pl_target["suicide"] = True
            cls.reply_info(
                msg_manager,
                msg_manager.msg_format("strMrGamblerSuicide", {"tGamblerName": name}),
            )
        else:
            pl_murderer["kills"] += 1
            pl_target["suicide"] = False
            cls.reply_info(
                msg_manager,
                msg_manager.msg_format(
                    "strMrGamblerKilled",
                    {"tGamblerName": name, "tMurdererName": pl_murderer["name"]},
                ),
            )
        if target == shooter:
            cls.switch(msg_manager)
            tmp["consume_action"] = 0
        order.remove(target)
        if check_over:
            cls.is_over(msg_manager)
        return

    @classmethod
    def is_over(cls, msg_manager):  # 游戏是否结束
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        if game["over"]:
            return True
        tmp["check_over"] = True
        if len(order) == 1:
            cls.reply_info(
                msg_manager,
                msg_manager.msg_format("strMrGameEnd", {"tWinnerName": cls.get_name(game, order[0])}),
            )
            cls.over(msg_manager)
            return True
        elif len(order) < 1:
            cls.reply_info(
                msg_manager,
                msg_manager.msg_format("strMrGameTied"),
            )
            cls.over(msg_manager)
            return True
        return False

    @classmethod
    def end_round(cls, msg_manager):  # 回合结束
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        if game["over"]:
            return
        cls.handle_event(msg_manager, "end_round")
        consume_action = tmp.get("consume_action") or 0
        pl_shooter = players[shooter]
        pl_shooter["actions"] -= consume_action
        if pl_shooter["actions"] < 1:
            cls.switch(msg_manager)
        shooter = data["shooter"]
        modify["ai_flag"] = cls.is_bot(game, shooter)
        MR.Core.comp.BotComp.action(msg_manager)
        return

    @classmethod
    def switch(cls, msg_manager):  # 换人
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        while True:
            shooter = order[(order.index(shooter) + 1) % len(order)]
            pl_shooter = players[shooter]
            pl_shooter["actions"] += 1
            if pl_shooter["actions"] > 0:
                break
        if shooter != data["shooter"]:
            data["shooter"] = shooter
            pl_shooter = players[shooter]
            reply["note"]["round"] = True
            cls.handle_event(msg_manager, "switch")
        return

    @classmethod
    def over(cls, msg_manager):  # 结算
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        game["over"] = True
        with DataBase(config.DB_PATH) as db:
            for pl in players.keys():
                if cls.is_bot(game, pl):
                    continue
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
        return

    # endregion
