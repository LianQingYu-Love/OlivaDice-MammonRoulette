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

    @classmethod
    def init(cls):
        pass

    @classmethod
    def apply(cls, msg_manager, target, stacks) -> bool | None:
        pass

    @classmethod
    def callback(cls, msg_manager, moment, target) -> bool | None:
        pass

    @classmethod
    def unapply(cls, msg_manager) -> bool | None:
        pass


class 束缚(EffectComp, BaseEffect):
    name = "束缚"
    brief = ""

    @classmethod
    def apply(cls, msg_manager, target, stacks):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        effect_data = {"stacks": 1}
        RegGameWork.create_effect_event(game, cls.name, effect_data, target)
        return True

    @classmethod
    def callback(cls, msg_manager, moment, target):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        if moment != "switch" or target != shooter:
            return False
        return True


class 神经麻痹(EffectComp, BaseEffect):
    name = "神经麻痹"
    brief = "回合结束时失去所有[神经麻痹], 并失去等值的HP."

    @classmethod
    def apply(cls, msg_manager, target, stacks):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        if cls.name not in players[target]["effect_event"]:
            expired = False if target == shooter else True
            players[target]["effect_event"][cls.name] = {
                "stacks": 0,
                "data": [],
                "expired": expired,
            }
        comp = players[target]["effect_event"][cls.name]
        comp["stacks"] += stacks
        comp["data"].append({"dmg": stacks, "murderer": tmp["murderer"]})
        return True

    @classmethod
    def callback(cls, msg_manager, moment, target):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        if moment == "damage" and target == tmp["target"] and tmp["dmg_type"] == "":
            comp = players[target]["effect_event"][cls.name]
            stacks_before = comp["stacks"]
            dmg, tmp["dmg"] = tmp["dmg"], 0
            EffectComp.give(msg_manager, cls.name, target, dmg)
            RegGameWork.reply_info(
                msg_manager,
                f"{RegGameWork.get_name(game, target)}感到神经麻痹[{stacks_before}->{stacks_before+dmg}].",
            )
            return False
        elif moment == "end_round" and target == shooter:
            comp = players[target]["effect_event"][cls.name]
            if not comp["expired"]:
                comp["expired"] = True
                return False
            tmp["dmg_type"] = cls.name
            hp_before = players[target]["hp"]
            for data in comp["data"]:
                RegGameWork.damage(msg_manager, target, data["dmg"], data["murderer"])
            RegGameWork.reply_info(
                msg_manager,
                f"{RegGameWork.get_name(game, target)}感到神经絮乱[hp{hp_before}->{tmp['hp_now']}].",
            )
            return True
