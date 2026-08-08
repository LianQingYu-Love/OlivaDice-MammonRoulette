# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/Core/cmop.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

from ..msgCustom import dictHelpDoc


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
