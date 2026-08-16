# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/Core/cmop.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

from ..msgCustom import dictHelpDoc, dictDefsMode, dictDefsProp, dictDefsEffect


def _():
    pass


class Registerable:
    _register = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        name = getattr(cls, "name", None)
        if name:
            cls._register[name] = cls

    @classmethod
    def get(cls, name):
        return cls._register.get(name, _)

    @classmethod
    def list(cls):
        return list(cls._register.keys())


class ModeComp(Registerable):
    _register = {}

    @classmethod
    def init_after(cls):
        mode_helpDoc = {}
        for mode_name, mode_cls in cls._register.items():
            mode_cls.init()
            t_dictDefsMode = dictDefsMode["default"].get(mode_name, {})
            dictDefsMode["default"][mode_name] = {
                "brief": t_dictDefsMode.get("brief", mode_cls.brief),
                "points": t_dictDefsMode.get("points", mode_cls.points),
                "seats": {
                    "default": t_dictDefsMode.get("seats", {}).get(
                        "default", mode_cls.seats.default
                    ),
                    "max": t_dictDefsMode.get("seats", {}).get(
                        "max", mode_cls.seats.max
                    ),
                    "min": t_dictDefsMode.get("seats", {}).get(
                        "min", mode_cls.seats.min
                    ),
                },
                "props": {
                    "pool": t_dictDefsMode.get("props", {}).get(
                        "pool", mode_cls.props.pool
                    ),
                    "ban": t_dictDefsMode.get("props", {}).get(
                        "ban", mode_cls.props.ban
                    ),
                    "limit": t_dictDefsMode.get("props", {}).get(
                        "limit", mode_cls.props.limit
                    ),
                },
                "modify": {
                    "dmg": t_dictDefsMode.get("modify", {}).get(
                        "dmg", mode_cls.modify.dmg
                    ),
                    "ammo_show": t_dictDefsMode.get("modify", {}).get(
                        "ammo_show", mode_cls.modify.ammo_show
                    ),
                    "bullet_show": t_dictDefsMode.get("modify", {}).get(
                        "bullet_show", mode_cls.modify.bullet_show
                    ),
                },
            }
            mode_helpDoc[f"恶赌模式 {mode_name}"] = mode_cls.brief
        dictHelpDoc.update(mode_helpDoc)
        return

    @classmethod
    def trigger(cls, msg_manager, event):
        return getattr(cls.get(msg_manager.val["game"]["mode"]["name"]), event)(
            msg_manager
        )


class PropComp(Registerable):
    _register = {}

    @classmethod
    def init_after(cls):
        prop_helpDoc = {}
        for prop_name, prop_cls in cls._register.items():
            prop_cls.init()
            t_dictDefsProp = dictDefsProp["default"].get(prop_name, {})
            dictDefsProp["default"][prop_name] = {
                "brief": t_dictDefsProp.get("brief", prop_cls.brief)
            }
            prop_helpDoc[f"恶赌道具 {prop_name}"] = prop_cls.brief
        dictHelpDoc.update(prop_helpDoc)
        return

    @classmethod
    def trigger(cls, msg_manager, prop, moment, prop_data):
        return cls.get(prop).callback(msg_manager, moment, prop_data)

    @classmethod
    def use(cls, msg_manager, prop, target):
        return cls.get(prop).apply(msg_manager, target)

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
            t_dictDefsEffect = dictDefsEffect["default"].get(effect_name, {})
            dictDefsEffect["default"][effect_name] = {
                "brief": t_dictDefsEffect.get("brief", effect_cls.brief)
            }
            effect_helpDoc[f"恶赌效果 {effect_name}"] = effect_cls.brief
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
