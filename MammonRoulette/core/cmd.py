from AmorLib import FsmRouter

COMMON_CMD = ("priv", "ob", "prep", "play", "dead")
commands = FsmRouter(COMMON_CMD + ("setting",))
