# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/Core/cmop.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

import MammonRoulette as MR

from ..msgCustom import (
    dictStrCustom,
    dictStrCustomNote,
    dictHelpDoc,
    dictDefsMode,
    dictDefsProp,
    dictDefsEffect,
)

from AmorLib import Registerable


class ModeComp(Registerable):
    _register = {}

    @classmethod
    def init_after(cls):
        mode_helpDoc = {}
        for mode_name, mode_cls in cls._register.items():
            mode_cls.init()
            dictDefsMode["default"][mode_name] = {
                "brief": mode_cls.brief,
                "points": mode_cls.points,
                "seats": {
                    "default": mode_cls.seats.default,
                    "max": mode_cls.seats.max,
                    "min": mode_cls.seats.min,
                },
                "props": {
                    "pool": mode_cls.props.pool,
                    "ban": mode_cls.props.ban,
                    "limit": mode_cls.props.limit,
                },
                "modify": {
                    "dmg": mode_cls.modify.dmg,
                    "ammo_show": mode_cls.modify.ammo_show,
                    "bullet_show": mode_cls.modify.bullet_show,
                },
            }
            mode_helpDoc[f"恶赌模式 {mode_name}"] = mode_cls.brief
            for reply in mode_cls.reply:
                reply_field, reply_note, reply_msg = reply
                dictStrCustom[reply_field] = reply_msg
                dictStrCustomNote[reply_field] = reply_note
        dictHelpDoc.update(mode_helpDoc)
        return

    @classmethod
    def trigger(cls, msg_manager, event):
        return getattr(cls.get(msg_manager.val["game"]["mode"]["name"]), event)(msg_manager)


class PropComp(Registerable):
    _register = {}

    @classmethod
    def init_after(cls):
        prop_helpDoc = {}
        for prop_name, prop_cls in cls._register.items():
            prop_cls.init()
            dictDefsProp["default"][prop_name] = {
                "brief": prop_cls.brief,
            }
            prop_helpDoc[f"恶赌道具 {prop_name}"] = prop_cls.brief
            for reply in prop_cls.reply:
                reply_field, reply_note, reply_msg = reply
                dictStrCustom[reply_field] = reply_msg
                dictStrCustomNote[reply_field] = reply_note
        dictHelpDoc.update(prop_helpDoc)
        return

    @classmethod
    def trigger(cls, msg_manager, prop, moment, prop_data):
        return cls.get(prop).callback(msg_manager, moment, prop_data)

    @classmethod
    def use(cls, msg_manager, prop, user_id, target):
        if cls.get(prop).apply(msg_manager, target):
            MR.Core.work.RegGameWork.remove_prop(msg_manager.val["game"], user_id, prop)

    @classmethod
    def uninstall(cls, msg_manager, prop, prop_data):
        return cls.get(prop).unapply(msg_manager, prop_data)


class EffectComp(Registerable):
    _register = {}

    @classmethod
    def init_after(cls):
        effect_helpDoc = {}
        for effect_name, effect_cls in cls._register.items():
            effect_cls.init()
            dictDefsEffect["default"][effect_name] = {
                "brief": effect_cls.brief,
            }
            effect_helpDoc[f"恶赌效果 {effect_name}"] = effect_cls.brief
            for reply in effect_cls.reply:
                reply_field, reply_note, reply_msg = reply
                dictStrCustom[reply_field] = reply_msg
                dictStrCustomNote[reply_field] = reply_note
        dictHelpDoc.update(effect_helpDoc)
        return

    @classmethod
    def trigger(cls, msg_manager, effect, moment, target, effect_data):
        return cls.get(effect).callback(msg_manager, moment, target, effect_data)

    @classmethod
    def give(cls, msg_manager, effect, target, stacks: int = 1):
        return cls.get(effect).apply(msg_manager, target, stacks)

    @classmethod
    def uninstall(cls, msg_manager, effect):
        return cls.get(effect).unapply(msg_manager)


class BotComp(Registerable):
    _register = {}

    @classmethod
    def state_snapshot(cls, msg_manager):
        """抓取枪手视角的对局快照"""
        game, data, reply, tmp, modify, players, order, shooter, bullet = MR.Core.work.RegGameWork.get_index(msg_manager)
        enemies = [uid for uid in order if uid != shooter]
        t_players = {
            uid: {
                "hp": players[uid]["hp"],
                "props": players[uid]["props"],
                "actions": players[uid]["actions"],
                "effect_event": players[uid]["effect_event"],
            }
            for uid in order
        }
        t_ammo = {"live": data["ammo_live"], "blank": data["ammo_blank"], "bullet": data["bullet"]}
        return {
            "game": game,
            "modify": modify,
            "shooter": shooter,
            "order": order,
            "enemies": enemies,
            "players": t_players,
            "ammo": t_ammo,
            "bullet": bullet,
            "prop_event": data["prop_event"],
        }

    @classmethod
    def legal_actions(cls, msg_manager):
        """枚举当前枪手全部合法指令文本(仅开枪/吞枪/使用道具)"""
        game, data, reply, tmp, modify, players, order, shooter, bullet = MR.Core.work.RegGameWork.get_index(msg_manager)
        target_props = ("手铐", "红牛", "止疼药", "口红", "邀请函", "牛奶")
        # 开枪动作
        actions = ["吞枪"]
        for idx, uid in enumerate(order, 1):
            if uid != shooter:
                actions.append(f"开枪{idx}")
        # 使用道具动作
        for prop in players[shooter]["props"]:
            if prop == "金币":
                continue  # 金币仅用于购买, 而AI只允许开枪与使用道具
            if prop == "手铐":
                next_uid = order[(order.index(shooter) + 1) % len(order)]
                if not MR.Core.work.RegGameWork.get_effect_stacks(game, "束缚", next_uid):
                    actions.append(f"使用{prop}")
                for idx, uid in enumerate(order, 1):
                    if uid != shooter and not MR.Core.work.RegGameWork.get_effect_stacks(game, "束缚", uid):
                        actions.append(f"使用{prop}{idx}")
                continue
            if prop == "止疼药":
                if not MR.Core.work.RegGameWork.get_effect_stacks(game, "神经麻痹", shooter):
                    actions.append(f"使用{prop}")
                for idx, uid in enumerate(order, 1):
                    if uid != shooter and not MR.Core.work.RegGameWork.get_effect_stacks(game, "神经麻痹", uid):
                        actions.append(f"使用{prop}{idx}")
                continue
            if prop == "锯子" and MR.Core.work.RegGameWork.get_prop_data(msg_manager, prop_name="锯子"):
                continue
            if prop == "放大镜" and modify["bullet_show"]:
                continue
            actions.append(f"使用{prop}")
            if prop in target_props:
                for idx, uid in enumerate(order, 1):
                    if uid != shooter:
                        actions.append(f"使用{prop}{idx}")
        return actions

    @classmethod
    def execute(cls, msg_manager, action):
        """执行单条AI指令
        - "吞枪":   Core.work.RegGameWork.shoot(msg_manager, shooter)
        - "开枪N":  Core.work.RegGameWork.shoot(msg_manager, order[N-1])
        - "使用X":  PropComp.use(msg_manager, X, shooter, shooter)
        - "使用XN": PropComp.use(msg_manager, X, shooter, order[N-1])
        """
        game, data, reply, tmp, modify, players, order, shooter, bullet = MR.Core.work.RegGameWork.get_index(msg_manager)
        if action == "吞枪":
            MR.Core.work.RegGameWork.shoot(msg_manager, shooter)
        elif action.startswith("开枪"):
            seat = int(action[2:]) - 1
            target = order[seat]
            MR.Core.work.RegGameWork.shoot(msg_manager, target)
        elif action.startswith("使用"):
            prop = action[2:]
            target = shooter
            for pos, ch in enumerate(prop):
                if ch.isdigit():
                    seat = int(prop[pos:]) - 1
                    prop = prop[:pos]
                    target = order[seat]
                    break
            PropComp.use(msg_manager, prop, shooter, target)

    @classmethod
    def action(cls, msg_manager):
        """AI行动"""
        game = msg_manager.val["game"]
        if not game["data"]["modify"]["ai_flag"]:
            return
        while not game.get("over", False):
            game, data, reply, tmp, modify, players, order, shooter, bullet = MR.Core.work.RegGameWork.get_index(msg_manager)
            ai_model = players[shooter]["ai_model"]
            if not MR.Core.work.RegGameWork.is_bot(game, shooter):
                modify["ai_flag"] = False
                break
            ai = cls.get(ai_model).instance()
            action = ai.decide(msg_manager)
            cls.execute(msg_manager, action)
            ai.learning(msg_manager, action, shooter)
        return

    @classmethod
    def load_all(cls):
        for ai_cls in cls._register.values():
            try:
                ai_cls.instance().load()
            except Exception:
                pass

    @classmethod
    def save_all(cls):
        for ai_cls in cls._register.values():
            try:
                ai_cls.instance().save()
            except Exception:
                pass
