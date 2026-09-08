# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/Defs/effect.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

from ..Core.comp import EffectComp
from ..Core.work import RegGameWork


class BaseEffect:
    name = ""
    brief = ""
    reply: list = []

    @classmethod
    def init(cls):
        pass

    @classmethod
    def apply(cls, msg_manager, target, stacks) -> bool | None:
        raise NotImplementedError

    @classmethod
    def callback(cls, msg_manager, moment, target, effect_data) -> bool | None:
        pass

    @classmethod
    def unapply(cls, msg_manager) -> bool | None:
        pass


class 束缚(EffectComp, BaseEffect):
    name = "束缚"
    brief = "被手铐囚禁的标识."

    @classmethod
    def apply(cls, msg_manager, target, stacks):
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        effect_data = {"stacks": 1}
        RegGameWork.create_effect_event(msg_manager, target, cls.name, effect_data)
        return True

    @classmethod
    def callback(cls, msg_manager, moment, target, effect_data):
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        if moment != "switch" or target != shooter:
            return False
        return True


class 神经麻痹(EffectComp, BaseEffect):
    name = "神经麻痹"
    brief = "回合结束时失去所有[神经麻痹], 并失去等值的HP."
    reply = [
        ("strMrEffectPain_1", "神经麻痹效果 层数增加", "{tGamblerName}感到神经麻痹[{stacks_before}->{stacks_now}]."),
        ("strMrEffectPain_2", "神经麻痹效果 结算", "{tGamblerName}感到神经絮乱[hp {hp_before}->{hp_now}]."),
    ]

    @classmethod
    def apply(cls, msg_manager, target, stacks):
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        if cls.name not in players[target]["effect_event"]:
            expired = False if target == shooter else True
            players[target]["effect_event"][cls.name] = {
                "stacks": 0,
                "data": [],
                "expired": expired,
            }
        effect_data = players[target]["effect_event"][cls.name]
        effect_data["stacks"] += stacks
        effect_data["data"].append({"dmg": stacks, "murderer": target})
        return True

    @classmethod
    def callback(cls, msg_manager, moment, target, effect_data):
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        if moment == "damage" and target == tmp["target"] and tmp["dmg_type"] == "":
            stacks_before = effect_data["stacks"]
            dmg, tmp["dmg"] = tmp["dmg"], 0
            EffectComp.give(msg_manager, cls.name, target, dmg)
            msg_reply = msg_manager.msg_format(
                "strMrEffectPain_1",
                {
                    "tGamblerName": RegGameWork.get_name(game, target),
                    "stacks_before": stacks_before,
                    "stacks_now": stacks_before + dmg,
                },
            )
            RegGameWork.reply_info(msg_manager, msg_reply)
            return False
        elif moment == "end_round" and target == shooter:
            effect_data = players[target]["effect_event"][cls.name]
            if not effect_data["expired"]:
                effect_data["expired"] = True
                return False
            tmp["dmg_type"] = cls.name
            tmp["check_over"] = False
            hp_before = players[target]["hp"]
            for data in reversed(effect_data["data"]):
                RegGameWork.damage(msg_manager, target, data["dmg"], data["murderer"])
            if not RegGameWork.is_over(msg_manager):
                msg_reply = msg_manager.msg_format(
                    "strMrEffectPain_2",
                    {
                        "tGamblerName": RegGameWork.get_name(game, target),
                        "hp_before": hp_before,
                        "hp_now": tmp["hp_now"],
                    },
                )
                RegGameWork.reply_info(msg_manager, msg_reply)
            return True
