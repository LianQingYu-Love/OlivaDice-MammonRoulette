# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/Defs/ai.py
@Author    :    MammonRoulette
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

import random
import os
import copy
from collections import deque
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .. import config
from ..Core.comp import BotComp, PropComp, EffectComp, ModeComp
from ..Core.work import RegGameWork

from AmorLib import Registerable


# region DQN 网络
class DQN(nn.Module):
    """深度Q网络：输入状态向量，输出每个动作的Q值。"""

    def __init__(self, state_dim: int, action_dim: int, hidden: int = 256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden // 2),
            nn.ReLU(),
            nn.Linear(hidden // 2, action_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# endregion


# region BaseAI 基类
class BaseBot:
    name = ""  # AI 名称，用于前端展示
    brief = ""  # AI 简介，用于前端展示

    @classmethod
    def instance(cls):
        """获取 AI 的唯一实例（单例模式）."""
        if getattr(cls, "_instance", None) is None:
            cls._instance = cls()
        return cls._instance

    def decide(self, msg_manager) -> str:
        """依据当前局势生成指令文本."""
        raise NotImplementedError

    def learning(self, msg_manager) -> None:
        """AI 执行完一条指令后调用，用于学习."""
        pass

    def save(self) -> None:
        """将模型参数持久化."""
        pass

    def load(self) -> None:
        """从持久化文件恢复模型参数."""
        pass

    # region 动态类型列表
    @property
    def ALL_MODES(self):
        return ModeComp.list()

    @property
    def ALL_PROPS(self):
        return PropComp.list()

    @property
    def ALL_EFFECTS(self):
        return EffectComp.list()

    # endregion


# endregion


class Stephen(BotComp, BaseBot):
    name = "斯蒂芬"
    brief = ""
    # region 状态编码常量
    MAX_PLAYERS = 8
    MAX_HP = 6.0
    MAX_ACTIONS = 10.0
    MAX_PROP_COUNT = 6.0
    MAX_EFFECT_STACKS = 5.0

    # endregion
    # region 初始化
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.policy_net = DQN(self.state_dim, self.action_dim).to(self.device)
        self.target_net = DQN(self.state_dim, self.action_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.optimizer = torch.optim.Adam(self.policy_net.parameters(), lr=0.001)
        self.memory = deque(maxlen=10000)
        self.epsilon = 1.0
        self.epsilon_min = 0.05
        self.epsilon_decay = 0.995
        self.gamma = 0.99
        self.batch_size = 64
        self.train_step = 0
        self.target_update_freq = 100

    # endregion

    # region 动态类型列表

    @property
    def state_dim(self) -> int:
        """返回状态向量的总维度。"""
        return (
            6
            + (2 + len(self.ALL_PROPS) + len(self.ALL_EFFECTS))
            + self.MAX_PLAYERS * (2 + len(self.ALL_PROPS) + len(self.ALL_EFFECTS))
            + 3
            + len(self.ALL_MODES)
        )

    @property
    def action_dim(self) -> int:
        """全局动作空间大小。"""
        return 1 + self.MAX_PLAYERS + len(self.ALL_PROPS) + len(self.ALL_PROPS) * self.MAX_PLAYERS

    # endregion

    # region 状态编码
    def encode_state(self, msg_manager) -> np.ndarray:
        """将游戏状态编码为固定长度的 numpy 向量，供神经网络使用。"""
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)

        # 弹药特征: [实弹比例, 空包弹比例, 总弹数归一化, 是否实弹, 弹药可见, 子弹可见]
        ammo_live = data["ammo_live"] if modify["ammo_show"] else 0
        ammo_blank = data["ammo_blank"] if modify["ammo_show"] else 0
        ammo_total = ammo_live + ammo_blank
        bullet_val = bullet if modify["bullet_show"] else 0.5
        feat_ammo = np.array(
            [
                ammo_live / max(ammo_total, 1),
                ammo_blank / max(ammo_total, 1),
                ammo_total / 8.0,
                float(bullet_val),
                1.0 if modify["ammo_show"] else 0.0,
                1.0 if modify["bullet_show"] else 0.0,
            ],
            dtype=np.float32,
        )

        # 自身特征: [HP归一化, 行动力] + [各道具持有数量] + [各效果层数]
        player = players[shooter]
        prop_vec = np.zeros(len(self.ALL_PROPS), dtype=np.float32)
        for prop in player["props"]:
            prop_vec[self.ALL_PROPS.index(prop)] += 1.0
        prop_vec = np.clip(prop_vec / self.MAX_PROP_COUNT, 0.0, 1.0)

        effect_vec = np.zeros(len(self.ALL_EFFECTS), dtype=np.float32)
        for i, effect_name in enumerate(self.ALL_EFFECTS):
            effect_data = player["effect_event"].get(effect_name)
            if effect_data and isinstance(effect_data, dict):
                effect_vec[i] = effect_data.get("stacks", 0) / self.MAX_EFFECT_STACKS

        feat_self = np.concatenate(
            [
                np.array(
                    [player["hp"] / self.MAX_HP, np.clip(player["actions"] / self.MAX_ACTIONS, -1.0, 1.0)], dtype=np.float32
                ),
                prop_vec,
                effect_vec,
            ]
        )

        # 全体玩家特征: 每人 [HP, 行动力, 道具, 效果]，与自身特征格式一致
        reordered = [shooter] + [uid for uid in order if uid != shooter]
        per_player_dim = 2 + len(self.ALL_PROPS) + len(self.ALL_EFFECTS)
        feat_players_list = []
        for i in range(self.MAX_PLAYERS):
            if i < len(reordered):
                p = players[reordered[i]]
                p_prop_vec = np.zeros(len(self.ALL_PROPS), dtype=np.float32)
                for prop in p["props"]:
                    p_prop_vec[self.ALL_PROPS.index(prop)] += 1.0
                p_prop_vec = np.clip(p_prop_vec / self.MAX_PROP_COUNT, 0.0, 1.0)

                p_effect_vec = np.zeros(len(self.ALL_EFFECTS), dtype=np.float32)
                for j, effect_name in enumerate(self.ALL_EFFECTS):
                    effect_data = p["effect_event"].get(effect_name)
                    if effect_data and isinstance(effect_data, dict):
                        p_effect_vec[j] = effect_data.get("stacks", 0) / self.MAX_EFFECT_STACKS

                p_vec = np.concatenate(
                    [
                        np.array(
                            [p["hp"] / self.MAX_HP, np.clip(p["actions"] / self.MAX_ACTIONS, -1.0, 1.0)],
                            dtype=np.float32,
                        ),
                        p_prop_vec,
                        p_effect_vec,
                    ]
                )
                feat_players_list.append(p_vec)
            else:
                feat_players_list.append(np.zeros(per_player_dim, dtype=np.float32))
        feat_players = np.array(feat_players_list, dtype=np.float32).flatten()

        # 对局上下文: [存活人数, 敌人数, 回合位置, 模式one-hot]
        alive_count = sum(1 for uid in order if players[uid]["hp"] > 0)
        enemy_count = sum(1 for uid in order if uid != shooter and players[uid]["hp"] > 0)
        shooter_idx = order.index(shooter) if shooter in order else 0

        mode_name = game["mode"]["name"]
        mode_onehot = np.zeros(len(self.ALL_MODES), dtype=np.float32)
        mode_onehot[self.ALL_MODES.index(mode_name)] = 1.0

        feat_context = np.concatenate(
            [
                np.array(
                    [alive_count / self.MAX_PLAYERS, enemy_count / 7.0, shooter_idx / max(len(order), 1)],
                    dtype=np.float32,
                ),
                mode_onehot,
            ]
        )

        return np.concatenate([feat_ammo, feat_self, feat_players, feat_context], dtype=np.float32)

    # endregion

    # region 动作空间

    def encode_action(self, action: str) -> int:
        """将合法动作文本映射为全局索引。"""
        if action == "吞枪":
            return 0
        if action.startswith("开枪"):
            return int(action[2:])
        if action.startswith("使用"):
            prop = action[2:]
            target_seat = 0
            for pos, ch in enumerate(prop):
                if ch.isdigit():
                    target_seat = int(prop[pos:])
                    prop = prop[:pos]
                    break
            prop_idx = self.ALL_PROPS.index(prop)
            if target_seat == 0:
                return 1 + self.MAX_PLAYERS + prop_idx
            return 1 + self.MAX_PLAYERS + len(self.ALL_PROPS) + prop_idx * self.MAX_PLAYERS + (target_seat - 1)
        raise ValueError(f"未知动作: {action}")

    def decode_action(self, idx: int) -> str:
        """将全局索引解码为动作文本。"""
        if idx == 0:
            return "吞枪"
        if idx <= self.MAX_PLAYERS:
            return f"开枪{idx}"
        offset = idx - 1 - self.MAX_PLAYERS
        if offset < len(self.ALL_PROPS):
            return f"使用{self.ALL_PROPS[offset]}"
        offset -= len(self.ALL_PROPS)
        prop_idx = offset // self.MAX_PLAYERS
        target_seat = offset % self.MAX_PLAYERS + 1
        return f"使用{self.ALL_PROPS[prop_idx]}{target_seat}"

    def action_mask(self, msg_manager) -> tuple:
        """返回 (合法动作掩码, 合法动作列表)。掩码中 True 表示该全局动作可执行。"""
        legal_actions = BotComp.legal_actions(msg_manager)
        mask = np.zeros(self.action_dim, dtype=bool)
        for action in legal_actions:
            mask[self.encode_action(action)] = True
        return mask, legal_actions

    # endregion

    # region 决策与学习
    def decide(self, msg_manager) -> str:
        """ε-greedy 策略：以 epsilon 概率随机探索，否则选择 Q 值最大的合法动作。"""
        state = self.encode_state(msg_manager)
        mask, legal_actions = self.action_mask(msg_manager)

        if np.random.random() < self.epsilon:
            action = random.choice(legal_actions)
        else:
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            with torch.no_grad():
                q_values = self.policy_net(state_tensor).cpu().numpy().flatten()
            q_values[~mask] = -float("inf")
            action = self.decode_action(int(np.argmax(q_values)))

        self.last_state = state
        self.last_action = action
        self.last_snapshot = copy.deepcopy(msg_manager.val["game"])
        return action

    def learning(self, msg_manager, action=None, shooter=None) -> None:
        """执行动作后学习：存储经验并训练网络。"""
        game = msg_manager.val["game"]
        reward = self.compute_reward(msg_manager)
        done = game.get("over", False)
        next_state = self.encode_state(msg_manager)
        action_idx = self.encode_action(self.last_action)

        self.memory.append((self.last_state, action_idx, reward, next_state, done))
        self._train()

    def compute_reward(self, msg_manager) -> float:
        """根据状态变化计算奖励。"""
        prev_game = self.last_snapshot
        prev_data = prev_game["data"]
        prev_modify, prev_players, prev_order, prev_shooter, prev_bullet = (
            prev_data["modify"],
            prev_data["players"],
            prev_data["order"],
            prev_data["shooter"],
            prev_data["bullet"],
        )
        game, data, reply, tmp, modify, players, order, shooter, bullet = RegGameWork.get_index(msg_manager)
        reward = 0

        return reward

    def _train(self) -> None:
        """经验回放训练：从记忆中采样一批数据，用贝尔曼方程更新策略网络。"""
        if len(self.memory) < self.batch_size:
            return

        batch = random.sample(list(self.memory), self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states = torch.FloatTensor(np.array(states)).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(np.array(next_states)).to(self.device)
        dones = torch.FloatTensor(dones).to(self.device)

        q_values = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            next_q_values = self.target_net(next_states).max(1)[0]
            target_q_values = rewards + self.gamma * next_q_values * (1 - dones)

        loss = F.mse_loss(q_values, target_q_values)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.train_step += 1
        if self.train_step % self.target_update_freq == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    # endregion

    # region 持久化
    def save(self) -> None:
        """将模型参数、优化器状态、经验回放保存到磁盘。"""
        path = os.path.join(config.AI_MODEL_DIR, f"{self.name}.pth")
        torch.save(
            {
                "policy_net": self.policy_net.state_dict(),
                "target_net": self.target_net.state_dict(),
                "optimizer": self.optimizer.state_dict(),
                "epsilon": self.epsilon,
                "train_step": self.train_step,
                "memory": list(self.memory),
            },
            path,
        )

    def load(self) -> None:
        """从磁盘恢复模型参数、优化器状态、经验回放。"""
        path = os.path.join(config.AI_MODEL_DIR, f"{self.name}.pth")
        if not os.path.exists(path):
            return
        checkpoint = torch.load(path, map_location=self.device)
        self.policy_net.load_state_dict(checkpoint["policy_net"])
        self.target_net.load_state_dict(checkpoint["target_net"])
        self.optimizer.load_state_dict(checkpoint["optimizer"])
        self.epsilon = checkpoint.get("epsilon", self.epsilon)
        self.train_step = checkpoint.get("train_step", 0)
        self.memory = deque(checkpoint.get("memory", []), maxlen=10000)

    # endregion
