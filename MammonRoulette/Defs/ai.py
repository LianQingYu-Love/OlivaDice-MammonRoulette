# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/Defs/ai.py
@Author    :    MammonRoulette
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    AI 定义. 斯蒂芬: 基于纯Python深度Q网络(DQN)的深度学习AI.
"""

import json
import math
import os
import random

from .. import config
from ..Core.comp import AIComp, PropComp
from ..Core.work import RegGameWork

from AmorLib import Registerable


class BaseAI:
    name = ""
    brief = ""

    @classmethod
    def instance(cls):
        if getattr(cls, "_instance", None) is None:
            cls._instance = cls()
        return cls._instance

    def decide(self, msg_manager) -> str:
        """依据当前局势生成指令文本."""
        raise NotImplementedError

    def learning(self, msg_manager, action=None, user_id=None) -> None:
        """AI执行完一条指令后调用, 用于在线学习."""
        pass

    def save(self) -> None:
        pass

    def load(self) -> None:
        pass


class 斯蒂芬(AIComp, BaseAI):
    name = "斯蒂芬"
    brief = "基于纯Python深度Q网络(DQN)的深度学习AI."

    # 超参数
    SEATS = 8  # 固定席位特征数
    HIDDEN = (64, 32)  # 隐层大小
    GAMMA = 0.95  # 折扣因子
    LR = 0.001  # 学习率
    BATCH = 8  # 每次学习的回放采样数
    REPLAY_CAP = 4096  # 回放池容量
    EPS_START = 0.5  # 初始探索率
    EPS_MIN = 0.02  # 最小探索率
    EPS_DECAY = 0.995  # 探索率衰减

    class _MLP:
        """纯Python三层全连接网络(两个隐层), 支持单样本反向传播训练."""

        def __init__(self, sizes, rng):
            self.sizes = list(sizes)
            self.weights = []
            self.biases = []
            for i in range(len(sizes) - 1):
                fan_in, fan_out = sizes[i], sizes[i + 1]
                limit = math.sqrt(6.0 / (fan_in + fan_out))
                self.weights.append([[rng.uniform(-limit, limit) for _ in range(fan_in)] for _ in range(fan_out)])
                self.biases.append([0.0] * fan_out)

        def forward(self, x):
            """前向传播, 返回(各层激活, 各层线性输出)."""
            acts = [x]
            zs = []
            a = x
            for layer, (w, b) in enumerate(zip(self.weights, self.biases)):
                z = [sum(w[k][j] * a[j] for j in range(len(a))) + b[k] for k in range(len(w))]
                zs.append(z)
                if layer < len(self.weights) - 1:
                    a = [max(0.0, v) for v in z]  # ReLU
                else:
                    a = z[:]  # 输出层线性
                acts.append(a)
            return acts, zs

        def train_step(self, x, target, lr):
            """以均方误差目标对单样本执行一次梯度下降."""
            acts, zs = self.forward(x)
            deltas = [[acts[-1][k] - target[k] for k in range(len(target))]]
            for layer in reversed(range(len(self.weights) - 1)):
                w_next = self.weights[layer + 1]
                z = zs[layer]
                d_prev = deltas[-1]
                delta = [
                    sum(w_next[k][j] * d_prev[k] for k in range(len(w_next))) * (1.0 if z[j] > 0.0 else 0.0)
                    for j in range(len(z))
                ]
                deltas.append(delta)
            deltas.reverse()
            for layer in range(len(self.weights)):
                w, b = self.weights[layer], self.biases[layer]
                a, d = acts[layer], deltas[layer]
                for k in range(len(w)):
                    for j in range(len(a)):
                        w[k][j] -= lr * d[k] * a[j]
                    b[k] -= lr * d[k]

    class _Replay:
        """经验回放池: 存储 (state, action, reward, next_state, done)."""

        def __init__(self, capacity, rng):
            self.capacity = capacity
            self.memory = []
            self.rng = rng

        def push(self, item):
            if len(self.memory) >= self.capacity:
                self.memory.pop(0)
            self.memory.append(item)

        def sample(self, count):
            count = min(count, len(self.memory))
            return self.rng.sample(self.memory, count)

    def __init__(self):
        self.rng = random.Random()
        self.prop_names = sorted(PropComp.list())
        # 动作表: 吞枪 | 开枪1-8 | 使用X / 使用X1-8
        self.action_list = ["吞枪"]
        for i in range(1, self.SEATS + 1):
            self.action_list.append(f"开枪{i}")
        for prop in self.prop_names:
            self.action_list.append(f"使用{prop}")
            for i in range(1, self.SEATS + 1):
                self.action_list.append(f"使用{prop}{i}")
        self.action_index = {a: i for i, a in enumerate(self.action_list)}
        n_in = self.SEATS * 3 + 3 + 2 + len(self.prop_names) + self.SEATS * 2 + 1
        sizes = [n_in, self.HIDDEN[0], self.HIDDEN[1], len(self.action_list)]
        self.net = self._MLP(sizes, self.rng)
        self.replay = self._Replay(self.REPLAY_CAP, self.rng)
        self.eps = self.EPS_START
        self.games = 0
        self._model_ready = False
        # 各对局轨迹: {(game_id, user_id): {"state", "action", "info"}}
        self._games = {}

    # region 模型持久化
    @property
    def model_path(self):
        dir_path = config.AI_MODEL_DIR or config.default_ai_model_dir
        return os.path.join(dir_path, f"{self.name}.json")

    def save(self) -> None:
        try:
            dir_path = os.path.dirname(self.model_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            payload = {
                "name": self.name,
                "props": self.prop_names,
                "sizes": self.net.sizes,
                "weights": self.net.weights,
                "biases": self.net.biases,
                "eps": self.eps,
                "games": self.games,
            }
            with open(self.model_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        except Exception:
            pass

    def load(self) -> None:
        try:
            if not os.path.exists(self.model_path):
                self._model_ready = True
                return
            with open(self.model_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if payload.get("props") != self.prop_names or payload.get("sizes") != self.net.sizes:
                self._model_ready = True
                return  # 特征/动作空间变化, 放弃旧模型
            self.net.weights = payload["weights"]
            self.net.biases = payload["biases"]
            self.eps = payload.get("eps", self.eps)
            self.games = payload.get("games", 0)
            self._model_ready = True
        except Exception:
            pass

    # endregion

    # region 决策
    def decide(self, msg_manager) -> str:
        """依据当前局势生成指令文本(ε-贪心).

        约定: 绝不抛异常(comp.action无保护), 且只返回合法指令;
        失败时一律回退到 "吞枪".
        """
        try:
            if not self._model_ready:
                self.load()
            game = msg_manager.val["game"]
            state = self._state_vector(msg_manager)
            actions = self._filter_actions(msg_manager, AIComp.legal_actions(msg_manager))
            action_idx = self._choose(state, actions)
            key = (id(game), game["data"]["shooter"])
            self._games[key] = {
                "state": state,
                "action": action_idx,
                "info": self._info(msg_manager),
            }
            return self.action_list[action_idx]
        except Exception:
            return "吞枪"

    def _choose(self, state, actions):
        legal = [self.action_index[a] for a in actions if a in self.action_index]
        if not legal:
            legal = [self.action_index["吞枪"]]
        q_values = self._q_all(state)
        if self.rng.random() < self.eps:
            return self.rng.choice(legal)
        return max(legal, key=lambda i: q_values[i])

    def _filter_actions(self, msg_manager, actions):
        """剔除指向已死亡(待移除)玩家的开枪/道具动作, 避免work层重复移除崩溃."""
        try:
            game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
            if not any(players[uid]["hp"] <= 0 for uid in order):
                return actions
            filtered = []
            for action in actions:
                if action == "吞枪":
                    filtered.append(action)
                    continue
                digits = [ch for ch in action[2:] if ch.isdigit()]
                if digits:
                    seat = int("".join(digits)) - 1
                    if 0 <= seat < len(order) and players[order[seat]]["hp"] <= 0:
                        continue
                filtered.append(action)
            return filtered or ["吞枪"]
        except Exception:
            return actions

    # endregion

    # region 学习
    def learning(self, msg_manager, action=None, user_id=None) -> None:
        """AI执行完一条指令后调用: 计算回报并训练网络. 内部不抛异常."""
        try:
            game = msg_manager.val["game"]
            if user_id is None:
                for k in list(self._games.keys()):
                    if k[0] == id(game):
                        user_id = k[1]
                        break
            key = (id(game), user_id)
            prev = self._games.pop(key, None)
            if prev is None or prev["action"] is None:
                return
            # 实际执行的是兜底动作且与决策不符时, 跳过本次学习
            if action is not None and self.action_list[prev["action"]] != action:
                return
            state_next = self._state_vector(msg_manager)
            reward, done = self._reward(prev["info"], msg_manager, user_id)
            self._train(prev["state"], prev["action"], reward, state_next, done)
            if done:
                self.games += 1
                self.save()  # 终局立即持久化
        except Exception:
            pass

    def _train(self, state, action_idx, reward, state_next, done):
        self.replay.push((state, action_idx, reward, state_next, done))
        for s, a, r, s_next, d in self.replay.sample(self.BATCH):
            q_values = self._q_all(s)
            target = q_values[:]
            if d:
                target[a] = r
            else:
                target[a] = r + self.GAMMA * max(self._q_all(s_next))
            self.net.train_step(s, target, self.LR)
        self.eps = max(self.EPS_MIN, self.eps * self.EPS_DECAY)

    def _q_all(self, state):
        acts, _ = self.net.forward(state)
        return acts[-1]

    # endregion

    # region 状态与回报
    def _state_vector(self, msg_manager):
        """构造固定长度的状态特征向量(枪手视角)."""
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        feats = []
        # 席位特征: 0号位为枪手
        for i in range(self.SEATS):
            if i < len(order):
                uid = order[i]
                feats += [1.0, min(players[uid]["hp"], 10.0) / 6.0, players[uid]["actions"] / 3.0]
            else:
                feats += [0.0, 0.0, 0.0]
        # 弹药
        if modify["ammo_show"]:
            feats += [data["ammo_live"] / 4.0, data["ammo_blank"] / 4.0, 1.0]
        else:
            feats += [0.0, 0.0, 0.0]
        # 子弹
        if modify["bullet_show"]:
            feats += [1.0 if data["bullet"] else -1.0, 1.0]
        else:
            feats += [0.0, 0.0]
        # 自身道具
        for prop in self.prop_names:
            feats.append(players[shooter]["props"].count(prop) / 2.0)
        # 效果层数
        for i in range(self.SEATS):
            uid = order[i] if i < len(order) else None
            if uid:
                bound = RegGameWork.get_effect_stacks(game, "束缚", uid)
                pain = RegGameWork.get_effect_stacks(game, "神经麻痹", uid)
                # get_effect_stacks 返回的是效果数据字典, 取其中的层数
                bound = bound.get("stacks", 0) if isinstance(bound, dict) else (bound or 0)
                pain = pain.get("stacks", 0) if isinstance(pain, dict) else (pain or 0)
                feats.append(min(bound, 4) / 3.0)
                feats.append(min(pain, 8) / 3.0)
            else:
                feats += [0.0, 0.0]
        # 伤害
        feats.append(modify["dmg"] / 3.0)
        return feats

    def _info(self, msg_manager):
        """抓取用于计算回报的对局信息."""
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        return {
            "order": list(order),
            "hp": {uid: players[uid]["hp"] for uid in players},
        }

    def _reward(self, prev_info, msg_manager, user_id=None):
        """由状态转移计算即时回报."""
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        me = user_id or shooter
        prev_hp, cur_hp = prev_info["hp"], {uid: players[uid]["hp"] for uid in players}
        prev_alive, cur_alive = set(prev_info["order"]), set(order)
        reward = 0.0
        # 自身血量变化
        if me in prev_hp and me in cur_hp:
            diff = cur_hp[me] - prev_hp[me]
            reward += diff * 4.0 if diff < 0 else diff * 1.0
        # 敌人受伤 / 死亡
        died = prev_alive - cur_alive
        for uid in prev_hp:
            if uid == me or uid not in cur_hp:
                continue
            diff = prev_hp[uid] - cur_hp[uid]
            if diff > 0:
                reward += diff * 3.0
        if me in died:
            reward -= 60.0
        else:
            reward += len(died) * 30.0
        # 对局真正结束 = over标志 且 存活人数<=1
        done = (bool(game.get("over", False)) and len(order) <= 1) or me in died
        if done:
            reward += 100.0 if me in order else -100.0
        reward -= 0.1  # 步数代价
        return reward, done

    # endregion
