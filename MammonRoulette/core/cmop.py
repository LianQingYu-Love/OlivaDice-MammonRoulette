class Registerable:
    register = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        name = getattr(cls, "name", None)
        if name:
            cls.register[name] = cls

    @classmethod
    def get(cls, name):
        return cls.register[name]

    @classmethod
    def list(cls):
        return list(cls.register.keys())


class ModeComp(Registerable):
    register = {}

    @classmethod
    def trigger(cls, game, mode, event, **kwargs):
        return getattr(cls.get(mode), event)(game, **kwargs)


class PropComp(Registerable):
    register = {}

    @classmethod
    def use(cls, game, prop, target):
        return cls.get(prop).apply(game, target)

    @classmethod
    def trigger(cls, game, event, prop):
        return cls.get(prop).callback(game, event)
