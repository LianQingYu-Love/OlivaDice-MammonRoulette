from ..msgCustom import dictHelpDocTemp


class Registerable:
    _register = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        name = getattr(cls, "name", None)
        if name:
            cls._register[name] = cls

    @classmethod
    def get(cls, name):
        return cls._register[name]

    @classmethod
    def list(cls):
        return list(cls._register.keys())


class ModeComp(Registerable):
    _register = {}

    @classmethod
    def init_after(cls):
        mode_helpDoc = {}
        for mode_name, mode_cls in cls._register.items():
            mode_helpDoc[f"恶赌模式 {mode_name}"] = mode_cls.brief
        dictHelpDocTemp.update(mode_helpDoc)
        return

    @classmethod
    def trigger(cls, game, mode, event, **kwargs):
        return getattr(cls.get(mode), event)(game, **kwargs)


class PropComp(Registerable):
    _register = {}

    @classmethod
    def init_after(cls):
        prop_helpDoc = {}
        for prop_name, prop_cls in cls._register.items():
            prop_helpDoc[f"恶赌道具 {prop_name}"] = prop_cls.brief
            prop_cls._init_after()
        dictHelpDocTemp.update(prop_helpDoc)
        return

    @classmethod
    def use(cls, game, prop, target):
        return cls.get(prop).apply(game, target)

    @classmethod
    def trigger(cls, game, event, prop):
        return cls.get(prop).callback(game, event)
