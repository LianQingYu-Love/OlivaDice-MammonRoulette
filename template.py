key = "group_id"
game = {
    "start": bool,  # false 准备阶段、true 正式游戏
    "over": bool,  # false 游戏中、true 游戏结束
    "expireTime": int,  # 过期时间
    "seats": int,  # 席位
    "mode": {
        "name": str,  # 游戏模式名称
        "points": int,  # 积分
        "props": {
            "pool": [],  # 道具池
            "ban": [],  # 道具黑名单
            "limit": int,  # 持有道具上限
        },
    },
    "data": {
        "ammo_live": int,  # 实弹
        "ammo_blank": int,  # 空包弹
        "bullet": int,  # 当前子弹
        "shooter": str,  # 枪手
        "order": [],  # 行动顺序
        "players": {
            "user_id": {
                "name": str,
                "hp": int,
                "props": [],
                "actions": int,
                "kills": int,
                "suicide": bool,  # 自杀
                "surrender": bool,  # 投降
                "points_mult": int,  # 积分倍率
                "effect_event": {},  # 效果事件
            },
        },
        "modify": {
            "dmg": int,  # 伤害
            "ammo_show": bool,  # 显示弹药
            "bullet_show": bool,  # 显示子弹
        },
        "prop_event": [],  # 道具事件
    },
    "reply": {
        "info": [],  # 常规信息
        "note": {
            "ammo": bool,  # 弹药消息刷新
            "round": bool,  # 轮次信息刷新
        },  # 分割线以下的消息
        "only": "",  # 会覆盖其他消息
    },
    "tmp": {},
}

moment = [
    "shoot",
    "damage",
    "dead",
    "end_round",
    "switch",
    "reload",
]
# 特殊事件
remove_prop_event = "remove"
remove_effect_event = "remove"

prop_data = {
    "name": str,  # 道具名称
    "data": {},  # 道具数据
}
key = "effect"
effect_data = {"stacks": int, "data": {}}
