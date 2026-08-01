# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/custom.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

dictStrCustom = {
    "strMrSignedResult": "{tGamblerName}在生死狀簽下姓名.",
    "strMrCardHas": (
        "『惡魔資料卡』"
        "\n真名: {tGamblerName}"
        "\n排名: {tGamblerRanking}"
        "\n賞金: {tGamblerPoints}"
        "\n槍下亡魂: {tGamblerKills}"
        "\n自取滅亡: {tGamblerSuicide}"
        "\n臨陣脫逃: {tGamblerSurrender}"
        "\n取勝: {tGamblerWins}｜戰敗: {tGamblerLosses}"
        "\n奪標率: {tGamblerWinRate}"
    ),
    "strMrCardNone": "只是个没有战绩的观众.",
    "strMrGamblerRankNode": "[{tGamblerRanking}] {tGamblerName}｜{tGamblerRecord}",
    "strMrLeaderboardResult": (
        "『惡魔{tLeaderboardType}榜』\n"
        "{tGamblerTopList}\n"
        "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁\n"
        "排名 {tRankingPageHome}-{tRankingPageEnd}｜总计上榜恶魔 {tGamblerCount}"
    ),
    "strMrLink": ",",
    "strMrAmmoLive": "實彈",
    "strMrAmmoBlank": "空包彈",
    "strMrGamePrep": "{tGameMode}對局靜候惡魔[{tSeatsHas}/{tSeatsMax}].",
    "strMrGameSeatsError": "非法人数, {tGameMode}模式限定人数为[{tSeatsMin},{tSeatsMax}] Defaults to {tSeatsDef}.",
    "strMrGameStarted": "对局已经开始, 无法加入.",
    "strMrGameModeError": "已开设{tGameMode}对局.",
    "strMrGameDismiss": "你已退出，对局解散.",
    "strMrGameRemain": "你已退出，剩余：{tSeatsHas}人.",
    "strMrGameAmmoRanOut": "彈藥耗盡，重新裝填中……",
    "strMrGameEnd": "{tWinnerName}用鮮血爲這場生死對局畫上句號.",
    "strMrGameTied": "這場對局沒有贏家.",
    "strMrGamblerWasAmmoLiveShot": "“嘭！”{tGamblerName}被崩倒在地[hp {tHpBefore}->{tHpNow}].",
    "strMrGamblerWasAmmoBlankShot": "“咔哒——”是空彈……",
    "strMrGamblerKilled": "{tGamblerName}死於他手.",
    "strMrGamblerSuicide": "{tGamblerName}自殺了……",
    "strMrGamblerSurrender": "{tGamblerName}臨陣脫逃.",
    "strMrGamblerTurn": "現在是{tGamblerName}的回合.",
    "strMrGamblerNoProp": "你没有{tPropName}道具.",
    "strMrGamblerDrawnProps": "{tGamblerName}抽取: {tDrawnProps}.",
    "strMrGamblerData": "〔{tGamblerIdx}〕 {tGamblerName}\n「hp: {tGamblerHp}」{tGamblerEffect}\n{tGamblerProps}\n",
    "strMrPropOneNode": "{tPropName}",
    "strMrPropManyNode": "{tPropName}*{tPropCount}",
    "strMrPropNoneNode": "無道具",
    "strMrEffectOneNode": "[{tEffectName}]",
    "strMrEffectManyNode": "[{tEffectName}:{tEffectStacks}]",
    "strMrEffectNoneNode": "",
    "strMrGameShooter": "\n槍手:〔{tGamblerIdx}〕{tGamblerName}",
    "strMrGameNowBulletShow": " 當前子彈: {tNowBulletType}",
    "strMrGameNowBulletHide": "",
    "strMrGameAmmoShow": "\n彈仓: {tAmmoLiveCount} / {tAmmoCount}",
    "strMrGameAmmoHide": "\n霰彈槍隱匿于迷霧之中.",
    "strMrGameDeadList": "\n滅亡: {tDeadList}",
    "strMrGameDeadNone": "",
    "strGameReplyInfo": "{tInfo}",
    "strGameReplyNote": "▁▁▁▁▁▁▁▁▁▁▁▁▁▁{tShooter}{tGameAmmo}{tGameNowBullet}",
    "strMrSituationResult": "{tGamblerData}▁▁▁▁▁▁▁▁▁▁▁▁▁▁{tShooter}{tGameAmmo}{tGameNowBullet}{tGameDeadList}",
}
dictStrCustomNote = {
    "strMrSignedResult": "【签署生死状】指令 注册或修改名称.",
    "strMrCardHas": "【恶魔名片】指令 显示玩家的资料.",
    "strMrCardNone": "【恶魔名片】指令 查看的玩家没有资料.",
    "strMrGamblerRankNode": "【恶魔排行】指令 每行玩家数据的显示格式.",
    "strMrLeaderboardResult": "【恶魔排行】指令 显示排行榜.",
    "strMrLink": "同类个体的连接符号 如道具、死亡玩家.",
    "strMrAmmoLive": "实弹",
    "strMrAmmoBlank": "空包弹",
    "strMrGamePrep": "【匹配】指令 正在等待其他玩家加入.",
    "strMrGameSeatsError": "【匹配】指令 席位设置不在允许范围.",
    "strMrGameStarted": "【匹配】指令 对局已经开始, 无法加入.",
    "strMrGameModeError": "【匹配】指令 已开设其他模式的对局.",
    "strMrGameDismiss": "【退出】指令 退出游戏后, 对局解散.",
    "strMrGameRemain": "【退出】指令 退出游戏后的剩余人数显示.",
    "strMrGameAmmoRanOut": "实弹耗尽, 重新装弹时的显示.",
    "strMrGameEnd": "游戏结束时的显示.",
    "strMrGameTied": "游戏平局时的显示.",
    "strMrGamblerWasAmmoLiveShot": "开枪 子弹为[AmmoLive]",
    "strMrGamblerWasAmmoBlankShot": "开枪 子弹为[AmmoBlank]",
    "strMrGamblerKilled": "玩家被其他玩家杀死时的显示.",
    "strMrGamblerSuicide": "玩家被自己杀死时的显示.",
    "strMrGamblerSurrender": "【投降】指令 玩家投降时的显示.",
    "strMrGamblerTurn": "显示当前行动的玩家.\n一般在行动换人或非行动玩家行动时显示.",
    "strMrGamblerNoProp": "【使用道具】指令 没有使用的道具.",
    "strMrGamblerDrawnProps": "显示玩家抽取的道具.",
    "strMrGamblerData": "玩家数据显示模板.\n包含道具列表.",
    "strMrPropOneNode": "道具列表 同名道具只有一个时的显示模板.",
    "strMrPropManyNode": "道具列表 同名道具有多个时的显示模板.",
    "strMrPropNoneNode": "道具列表 玩家没有道具时的显示模板.",
    "strMrEffectOneNode": "效果列表 同名效果只有一个时的显示模板.",
    "strMrEffectManyNode": "效果列表 同名效果有多个时的显示模板.",
    "strMrEffectNoneNode": "效果列表 玩家没有效果时的显示模板.",
    "strMrGameShooter": "枪手 当前枪手的显示.",
    "strMrGameNowBulletShow": "子弹 显示当前子弹的类型.",
    "strMrGameNowBulletHide": "子弹 隐藏当前子弹时的显示.",
    "strMrGameAmmoShow": "弹药 显示实弹、空包弹、总弹药.",
    "strMrGameAmmoHide": "弹药 隐藏弹药时的显示.",
    "strMrGameDeadList": "死亡列表 显示死亡的玩家.",
    "strMrGameDeadNone": "死亡列表 没有玩家死亡时的显示.",
    "strMrSituationResult": "【局势】指令 显示当前游戏局势.\n包括玩家数据、枪手、当前子弹、弹药、死亡玩家.",
}

dictStrConst = {}
dictGValue = {}
dictTValue = {
    # 赌徒基础信息
    "tGamblerName": "",  # 赌徒名称
    "tGamblerIdx": "N/A",  # 赌徒索引
    "tGamblerRanking": "N/A",  # 赌徒排名
    "tGamblerPoints": "N/A",  # 赌徒积分/赏金
    "tGamblerRecord": "N/A",  # 赌徒战绩
    "tGamblerHp": "N/A",  # 赌徒血量
    # 赌徒战绩统计
    "tGamblerKills": "N/A",  # 击杀数
    "tGamblerSuicide": "N/A",  # 自杀次数
    "tGamblerSurrender": "N/A",  # 投降次数
    "tGamblerWins": "N/A",  # 胜利次数
    "tGamblerLosses": "N/A",  # 失败次数
    "tGamblerWinRate": "N/A",  # 胜率
    # 排行榜相关
    "tLeaderboardType": "N/A",  # 排行榜类型
    "tGamblerTopList": "N/A",  # 赌徒上榜列表
    "tRankingPageHome": "N/A",  # 排行榜当前页起始
    "tRankingPageEnd": "N/A",  # 排行榜当前页结束
    "tGamblerCount": "N/A",  # 赌徒总数
    # 对局相关
    "tGameMode": "N/A",  # 游戏模式
    "tSeatsHas": "N/A",  # 当前座位数
    "tSeatsMax": "N/A",  # 最大座位数
    "tSeatsMin": "N/A",  # 最小座位数
    "tSeatsDef": "N/A",  # 默认座位数
    # 道具相关
    "tPropName": "",  # 道具名称
    "tPropCount": "N/A",  # 道具数量
    "tGamblerProps": "N/A",  # 赌徒持有的道具
    "tDrawnProps": "N/A",  # 玩家抽取的道具
    # 效果相关
    "tEffectName": "",  # 效果名称
    "tEffectStacks": "N/A",  # 效果层数
    "tGamblerEffect": "N/A",  # 赌徒持有的效果
    # 子弹/弹药相关
    "tNowBulletType": "N/A",  # 当前子弹类型
    "tAmmoLiveCount": "N/A",  # 实弹数量
    "tAmmoBlankCount": "N/A",  # 空包弹数量
    "tAmmoCount": "N/A",  # 总弹药数
    # 回复相关
    "tDeadList": "",  # 死亡列表
    "tGamblerData": "",  # 赌徒数据
    "tShooter": "",  # 枪手信息
    "tGameNowBullet": "",  # 回复-当前子弹
    "tGameAmmo": "",  # 回复-弹药信息
    "tGameDeadList": "",  # 回复-死亡列表
    "tHpBefore": "N/A",  # 玩家血量-受伤前
    "tHpNow": "N/A",  # 玩家血量-受伤后
    "tWinnerName": "",  # 胜利者名称
}

dictHelpDoc = {}

dictConsoleSwitch = {
    "MrMainEnabled": 1,
    "MrPokeEnabled": 1,
    "MrDebugEnabled": -1,
}
dictConsoleSwitchNote = {
    "MrMainEnabled": "[恶魔轮盘]全局开关, 默认开启\n-1 关闭\n0 跟随全局\n1 开启",
    "MrPokeEnabled": "[恶魔轮盘]poke开关, 默认开启\n-1 关闭\n0 跟随全局\n1 开启",
    "MrDebugEnabled": "[恶魔轮盘]调试开关, 默认关闭\n-1 关闭\n0 跟随全局\n1 开启",
}
