from AmorLib import FsmRouter

COMMON_CMD = ("priv", "ob", "prep", "play", "dead")
commands = FsmRouter(COMMON_CMD + ("setting",))


def get_target(game, target):
    order = game["order"]
    if not target:
        target = order[(order.index(game["shooter"]) + 1) % len(order)]
    elif target not in order:
        target = int(target)
        if target > len(order):
            return
        target = order[target - 1]
    return target
