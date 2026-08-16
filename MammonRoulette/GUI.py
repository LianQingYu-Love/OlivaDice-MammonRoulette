# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/GUI.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

import OlivaDiceCore
import OlivaDiceNativeGUI

import copy
import base64
import os
import tkinter
from tkinter import ttk, filedialog, messagebox
import webbrowser
import traceback
import threading
import json
import importlib
import datetime
import re

from PIL import Image, ImageTk  # type: ignore

from . import config
from .msgCustom import (
    dictHelpDoc,
    dictDefsMode,
    dictDefsProp,
    dictDefsEffect,
    dictDefsNote,
)

dictColorContext = {
    "color_001": "#00A0EA",
    "color_002": "#BBE9FF",
    "color_003": "#40C3FF",
    "color_004": "#FFFFFF",
    "color_005": "#000000",
    "color_006": "#80D7FF",
}


class ConfigUI(object):
    def __init__(self, Model_name, logger_proc=None):
        self.Model_name = Model_name
        self.UIObject = {}  # 存储所有UI控件对象
        self.UIData = {}  # 存储UI运行时数据 (状态、选中项等)
        self.UIConfig = {}  # 存储UI配置 (颜色等)
        self.logger_proc = logger_proc
        self.UIData["flag_open"] = False  # 窗口是否已打开标记
        self.UIData["click_record"] = {}  # 点击记录 (暂未使用)
        self.UIConfig.update(dictColorContext)  # 加载颜色配置

    def start(self):
        # 创建主窗口
        self.UIObject["root"] = tkinter.Toplevel()
        self.UIObject["root"].title("MammonRoulette 设置面板")
        self.UIObject["root"].geometry("800x600")
        self.UIObject["root"].minsize(800, 600)
        self.UIObject["root"].resizable(width=True, height=True)
        self.UIObject["root"].grid_rowconfigure(0, weight=0)
        self.UIObject["root"].grid_rowconfigure(1, weight=15)
        self.UIObject["root"].grid_columnconfigure(0, weight=15)
        self.UIObject["root"].grid_columnconfigure(1, weight=15)
        self.UIObject["root"].configure(bg=self.UIConfig["color_001"])

        self.UIData["hash_now"] = "unity"  # 当前选中的 Bot，默认为 unity (全局)

        # 初始化各个UI组件
        self.init_hash_Combobox()  # Bot 选择下拉框
        self.init_notebook()  # 主选项卡容器

        self.init_frame_main()  # "首页" 选项卡
        self.UIObject["Notebook_root"].add(self.UIObject["frame_main_root"], text="首页")
        self.init_frame_mode()  # "模式" 选项卡
        self.UIObject["Notebook_root"].add(self.UIObject["frame_mode_root"], text="模式")
        # self.init_frame_prop()  # "道具" 选项卡
        # self.UIObject["Notebook_root"].add(
        #     self.UIObject["frame_prop_root"], text="道具"
        # )
        # self.init_frame_effect()  # "效果" 选项卡
        # self.UIObject["Notebook_root"].add(
        #     self.UIObject["frame_effect_root"], text="效果"
        # )

        # 初始化所有数据 (加载回复词、配置项等)
        self.init_data_total()

        # 设置窗口图标并启动消息循环
        self.UIObject["root"].iconbitmap("./resource/tmp_favoricon.ico")
        self.UIObject["root"].mainloop()

    # region Bot 选择下拉框
    def init_hash_Combobox(self):
        """初始化 Bot 选择下拉框"""
        self.UIData["hash_Combobox_root_StringVar"] = tkinter.StringVar()
        self.UIObject["hash_Combobox_root"] = ttk.Combobox(
            self.UIObject["root"],
            textvariable=self.UIData["hash_Combobox_root_StringVar"],
        )
        self.UIObject["hash_Combobox_root"].grid(
            row=0,
            column=0,
            sticky="nsw",
            rowspan=1,
            columnspan=1,
            padx=(15, 0),
            pady=(15, 0),
        )
        self.UIObject["hash_Combobox_root"].configure(state="readonly")

        # 构建下拉选项列表
        self.UIData["hash_default"] = "unity"
        self.UIData["hash_default_key"] = "全局 (不推荐)"
        self.UIData["hash_find"] = {self.UIData["hash_default_key"]: self.UIData["hash_default"]}
        self.UIData["hash_list"] = [self.UIData["hash_default_key"]]

        for hash_this in OlivaDiceNativeGUI.load.dictBotInfo:
            key_info = "%s | %s" % (
                OlivaDiceNativeGUI.load.dictBotInfo[hash_this].platform["platform"],
                OlivaDiceNativeGUI.load.dictBotInfo[hash_this].id,
            )
            self.UIData["hash_list"].append(key_info)
            self.UIData["hash_find"][key_info] = hash_this
            if self.UIData["hash_default"] == "unity":
                self.UIData["hash_default_key"] = key_info
                self.UIData["hash_default"] = hash_this

        self.UIData["hash_now"] = self.UIData["hash_default"]
        self.UIObject["hash_Combobox_root"]["value"] = tuple(self.UIData["hash_list"])
        self.UIObject["hash_Combobox_root"].current(self.UIData["hash_list"].index(self.UIData["hash_default_key"]))
        self.UIObject["hash_Combobox_root"].bind(
            "<<ComboboxSelected>>", lambda x: self.Combobox_ComboboxSelected(x, "set", "hash_Combobox_root")
        )

        # 在线状态标签 (显示当前在线Bot数量)
        self.UIData["onlineStatus_Label_root_StringVar"] = tkinter.StringVar()
        self.UIObject["onlineStatus_Label_root"] = tkinter.Label(
            self.UIObject["root"],
            textvariable=self.UIData["onlineStatus_Label_root_StringVar"],
        )
        self.UIObject["onlineStatus_Label_root"].configure(bg=self.UIConfig["color_001"], fg=self.UIConfig["color_004"])
        self.UIObject["onlineStatus_Label_root"].grid(
            row=0,
            column=1,
            sticky="nse",
            rowspan=1,
            columnspan=1,
            padx=(0, 15),
            pady=(15, 0),
        )

    def Combobox_ComboboxSelected(self, action, event, target):
        if target == "hash_Combobox_root":
            self.UIData["hash_now"] = self.UIData["hash_find"][self.UIData["hash_Combobox_root_StringVar"].get()]
            self.init_data_total()

    # endregion
    # region 容器
    def init_notebook(self):
        """初始化 Notebook 容器"""
        self.UIData["style"] = ttk.Style(self.UIObject["root"])

        # 创建自定义元素
        try:
            self.UIData["style"].element_create("Plain.Notebook.tab", "from", "default")
        except:
            pass

        # 调整 Tab 内部布局
        self.UIData["style"].layout(
            "TNotebook.Tab",
            [
                (
                    "Plain.Notebook.tab",
                    {
                        "children": [
                            (
                                "Notebook.padding",
                                {
                                    "side": "top",
                                    "children": [
                                        (
                                            "Notebook.focus",
                                            {
                                                "side": "top",
                                                "children": [
                                                    (
                                                        "Notebook.label",
                                                        {"side": "top", "sticky": ""},
                                                    )
                                                ],
                                                "sticky": "nswe",
                                            },
                                        )
                                    ],
                                    "sticky": "nswe",
                                },
                            )
                        ],
                        "sticky": "nswe",
                    },
                )
            ],
        )

        # 配置 Notebook 整体样式
        self.UIData["style"].configure(
            "TNotebook",
            background=self.UIConfig["color_001"],  # 背景为主蓝色
            borderwidth=0,  # 无边框
            relief=tkinter.FLAT,  # 扁平风格
            padding=[-1, 1, -3, -3],  # 微调内边距，让内容更贴合
            tabmargins=[5, 5, 0, 0],  # 标签外间距
        )

        # 配置标签（Tab）样式
        self.UIData["style"].configure(
            "TNotebook.Tab",
            background=self.UIConfig["color_006"],  # 默认背景（浅蓝）
            foreground=self.UIConfig["color_001"],  # 默认文字（主蓝）
            padding=4,  # 标签内边距
            borderwidth=0,  # 无边框
            font=("等线", 12, "bold"),  # 字体
        )

        # 标签状态颜色映射（选中 / 未选中）
        self.UIData["style"].map(
            "TNotebook.Tab",
            background=[
                ("selected", self.UIConfig["color_004"]),  # 选中 → 白色
                ("!selected", self.UIConfig["color_003"]),  # 未选中 → 亮蓝
            ],
            foreground=[
                ("selected", self.UIConfig["color_003"]),  # 选中 → 亮蓝文字
                ("!selected", self.UIConfig["color_004"]),  # 未选中 → 白色文字
            ],
        )

        # 创建 Notebook 实例并放置到主窗口
        self.UIObject["Notebook_root"] = ttk.Notebook(self.UIObject["root"], style="TNotebook")
        self.UIObject["Notebook_root"].grid(
            row=1,
            column=0,
            sticky="nsew",
            rowspan=1,
            columnspan=2,
            padx=(15, 15),
            pady=(8, 15),
        )

        # 设置内部行列权重（让子页面可以填充全部空间）
        self.UIObject["Notebook_root"].grid_rowconfigure(0, weight=0)
        self.UIObject["Notebook_root"].grid_rowconfigure(1, weight=15)
        self.UIObject["Notebook_root"].grid_columnconfigure(0, weight=15)

    def show_project_site(self, url):
        """在默认浏览器中打开项目链接"""
        messagebox.showinfo("提示", "将通过浏览器访问 " + url)
        try:
            webbrowser.open(url)
        except webbrowser.Error as error_info:
            messagebox.showerror("webbrowser.Error", str(error_info))

    def button_action(self, name, action):
        """
        按钮悬停/离开事件处理
        改变按钮背景色提供视觉反馈
        """
        if name in self.UIObject:
            if action == "<Enter>":
                self.UIObject[name].configure(bg=self.UIConfig["color_006"])
            if action == "<Leave>":
                self.UIObject[name].configure(bg=self.UIConfig["color_003"])

    # endregion
    def init_data_total(self):
        """初始化数据"""
        tmp_hashSelection = self.UIData["hash_now"]
        is_global_mode = tmp_hashSelection == "unity"

        # 全局模式 (unity) 下的安全限制
        buttons_to_disable_in_global = [
            "button_reset_mode_default",
            "button_import_mode",
            "button_export_mode",
            "button_refresh_mode",
            "button_reset_mode_config",
            "button_reset_mode_detail",
            "button_edit_mode_detail",
        ]
        for button_name in buttons_to_disable_in_global:
            if button_name in self.UIObject:
                state = tkinter.DISABLED if is_global_mode else tkinter.NORMAL
                self.UIObject[button_name].config(state=state)

        # 更新右上角在线状态
        self.UIData["onlineStatus_Label_root_StringVar"].set("当前在线: %s" % OlivaDiceNativeGUI.load.onlineAPICount)

        # region 模式数据
        # 保存当前选中的模式，以便刷新后恢复选择
        selected_mode_name = None
        tree_selection = self.UIObject["tree_mode"].selection()
        if tree_selection:
            selected_item = self.UIObject["tree_mode"].item(tree_selection[0])
            selected_mode_name = selected_item["values"][0]

        for item in self.UIObject["tree_mode"].get_children():
            self.UIObject["tree_mode"].delete(item)

        source_data = dictDefsMode["default"] if is_global_mode else dictDefsMode.get(self.UIData["hash_now"], {})
        for mode_name, mode_data in source_data.items():
            brief = mode_data.get("brief", "").replace("\n", " ").strip()
            points = mode_data.get("points", 0)
            seats = mode_data.get("seats", {})
            seat_range = f"{seats.get('min', 2)}-{seats.get('max', 8)}"
            self.UIObject["tree_mode"].insert("", "end", text=mode_name, values=(mode_name, points, seat_range, brief))

        # 恢复之前选中的模式
        if selected_mode_name is not None:
            for child in self.UIObject["tree_mode"].get_children():
                if self.UIObject["tree_mode"].item(child)["values"][0] == selected_mode_name:
                    self.UIObject["tree_mode"].selection_set(child)
                    self.UIObject["tree_mode"].focus(child)
                    self.UIObject["tree_mode"].see(child)
                    break
        self.tree_mode_select()
        # endregion

    # region 首页
    def init_frame_main(self):
        """初始化首页"""
        self.UIObject["frame_main_root"] = tkinter.Frame(self.UIObject["Notebook_root"])
        self.UIObject["frame_main_root"].configure(relief=tkinter.FLAT)
        self.UIObject["frame_main_root"].grid(row=1, column=0, sticky="nsew", rowspan=1, columnspan=1)
        # 配置网格权重
        for i in range(5):
            self.UIObject["frame_main_root"].grid_rowconfigure(i, weight=0)
        self.UIObject["frame_main_root"].grid_rowconfigure(3, weight=15)
        for i in range(9):
            self.UIObject["frame_main_root"].grid_columnconfigure(i, weight=15)
        self.UIObject["frame_main_root"].configure(bg=self.UIConfig["color_001"], borderwidth=0)

        # ---------- Bot 信息 ----------
        self.UIObject["label_bot_info"] = tkinter.Label(
            self.UIObject["frame_main_root"],
            text="\n".join(
                [
                    OlivaDiceCore.data.bot_info,
                    "",
                    "世界是属于每一个人的。要创造一个充满逻辑并尊重每一个人的世界。",
                    "                                        ——《Новый Элемент Расселения》A.D.1960 Москва",
                ]
            ),
        )
        self.UIObject["label_bot_info"].configure(
            bg=self.UIConfig["color_001"],
            fg=self.UIConfig["color_004"],
            font=("等线", 14, "bold"),
        )
        self.UIObject["label_bot_info"].grid(
            row=3,
            column=0,
            sticky="nwe",
            rowspan=1,
            columnspan=9,
            padx=(0, 0),
            pady=(15, 0),
        )

        # ---------- 社区链接按钮 ----------
        # 论坛地址
        self.UIObject["button_share_1"] = tkinter.Button(
            self.UIObject["frame_main_root"],
            text="论坛地址",
            command=lambda: self.show_project_site("https://forum.olivos.run/"),
            bd=0,
            activebackground=self.UIConfig["color_002"],
            activeforeground=self.UIConfig["color_001"],
            bg=self.UIConfig["color_003"],
            fg=self.UIConfig["color_004"],
            relief="groove",
            height=2,
            width=12,
        )
        self.UIObject["button_share_1"].bind("<Enter>", lambda x: self.button_action("button_share_1", "<Enter>"))
        self.UIObject["button_share_1"].bind("<Leave>", lambda x: self.button_action("button_share_1", "<Leave>"))
        self.UIObject["button_share_1"].grid(
            row=4,
            column=0,
            sticky="nwe",
            rowspan=1,
            columnspan=2,
            padx=(15, 0),
            pady=(15, 0),
        )

        # 使用手册
        self.UIObject["button_share_2"] = tkinter.Button(
            self.UIObject["frame_main_root"],
            text="使用手册",
            command=lambda: self.show_project_site("https://wiki.dice.center/"),
            bd=0,
            activebackground=self.UIConfig["color_002"],
            activeforeground=self.UIConfig["color_001"],
            bg=self.UIConfig["color_003"],
            fg=self.UIConfig["color_004"],
            relief="groove",
            height=2,
            width=12,
        )
        self.UIObject["button_share_2"].bind("<Enter>", lambda x: self.button_action("button_share_2", "<Enter>"))
        self.UIObject["button_share_2"].bind("<Leave>", lambda x: self.button_action("button_share_2", "<Leave>"))
        self.UIObject["button_share_2"].grid(
            row=4,
            column=2,
            sticky="nwe",
            rowspan=1,
            columnspan=2,
            padx=(15, 0),
            pady=(15, 0),
        )

        # 项目源码
        self.UIObject["button_share_3"] = tkinter.Button(
            self.UIObject["frame_main_root"],
            text="项目源码",
            command=lambda: self.show_project_site("https://github.com/OlivOS-Team/OlivaDiceCore"),
            bd=0,
            activebackground=self.UIConfig["color_002"],
            activeforeground=self.UIConfig["color_001"],
            bg=self.UIConfig["color_003"],
            fg=self.UIConfig["color_004"],
            relief="groove",
            height=2,
            width=12,
        )
        self.UIObject["button_share_3"].bind("<Enter>", lambda x: self.button_action("button_share_3", "<Enter>"))
        self.UIObject["button_share_3"].bind("<Leave>", lambda x: self.button_action("button_share_3", "<Leave>"))
        self.UIObject["button_share_3"].grid(
            row=4,
            column=5,
            sticky="nwe",
            rowspan=1,
            columnspan=2,
            padx=(15, 0),
            pady=(15, 0),
        )

    # endregion
    # region 模式
    def init_frame_mode(self):
        """初始化模式选项"""
        self.UIObject["frame_mode_root"] = tkinter.Frame(self.UIObject["Notebook_root"])
        self.UIObject["frame_mode_root"].configure(relief=tkinter.FLAT)
        self.UIObject["frame_mode_root"].grid(row=1, column=0, sticky="nsew", rowspan=1, columnspan=1, padx=0, pady=0)
        self.UIObject["frame_mode_root"].grid_rowconfigure(0, weight=0)
        self.UIObject["frame_mode_root"].grid_rowconfigure(1, weight=1)
        self.UIObject["frame_mode_root"].grid_rowconfigure(2, weight=0)
        self.UIObject["frame_mode_root"].grid_columnconfigure(0, weight=1)
        self.UIObject["frame_mode_root"].grid_columnconfigure(1, weight=4)
        self.UIObject["frame_mode_root"].configure(bg=self.UIConfig["color_001"], borderwidth=0)

        self.UIObject["label_mode_note"] = tkinter.Label(
            self.UIObject["frame_mode_root"],
            text="游戏模式列表：点击模式查看完整说明",
            bg=self.UIConfig["color_001"],
            fg=self.UIConfig["color_004"],
            font=("等线", 12),
        )
        self.UIObject["label_mode_note"].grid(row=0, column=0, columnspan=2, sticky="nw", padx=15, pady=(10, 5))

        # 左侧模式列表
        self.UIObject["tree_mode"] = ttk.Treeview(self.UIObject["frame_mode_root"])
        self.UIObject["tree_mode"]["show"] = "headings"
        self.UIObject["tree_mode"]["columns"] = ("NAME",)
        self.UIObject["tree_mode"].column("NAME", width=150, anchor="w")
        self.UIObject["tree_mode"].heading("NAME", text="模式")
        self.UIObject["tree_mode"].grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        self.UIObject["tree_mode"].bind("<<TreeviewSelect>>", lambda x: self.tree_mode_select())

        self.UIObject["tree_mode_yscroll"] = ttk.Scrollbar(
            self.UIObject["frame_mode_root"],
            orient="vertical",
            command=self.UIObject["tree_mode"].yview,
        )
        self.UIObject["tree_mode"].configure(yscrollcommand=self.UIObject["tree_mode_yscroll"].set)
        self.UIObject["tree_mode_yscroll"].grid(row=1, column=0, sticky="nse", padx=0, pady=5)

        # 右侧三列列表
        self.UIObject["tree_mode_detail"] = ttk.Treeview(
            self.UIObject["frame_mode_root"],
            columns=("NOTE", "VALUE"),
            show="tree headings",
        )
        self.UIObject["tree_mode_detail"].heading("#0", text="条目")
        self.UIObject["tree_mode_detail"].heading("NOTE", text="说明")
        self.UIObject["tree_mode_detail"].heading("VALUE", text="内容")
        self.UIObject["tree_mode_detail"].column("#0", width=160, anchor="w")
        self.UIObject["tree_mode_detail"].column("NOTE", width=180, anchor="w")
        self.UIObject["tree_mode_detail"].column("VALUE", width=280, anchor="w")
        self.UIObject["tree_mode_detail"].grid(row=1, column=1, sticky="nsew", padx=15, pady=5)

        self.UIObject["tree_mode_detail_yscroll"] = ttk.Scrollbar(
            self.UIObject["frame_mode_root"],
            orient="vertical",
            command=self.UIObject["tree_mode_detail"].yview,
        )
        self.UIObject["tree_mode_detail"].configure(yscrollcommand=self.UIObject["tree_mode_detail_yscroll"].set)
        self.UIObject["tree_mode_detail_yscroll"].grid(row=1, column=1, sticky="nse", padx=0, pady=5)

        # 按钮栏
        self.UIObject["button_frame_mode"] = tkinter.Frame(self.UIObject["frame_mode_root"])
        self.UIObject["button_frame_mode"].configure(bg=self.UIConfig["color_001"])
        self.UIObject["button_frame_mode"].grid(row=2, column=0, columnspan=2, sticky="nsew", padx=15, pady=8)

        button_configs = [
            ("button_reset_mode_default", "恢复默认", self.reset_mode_default),
            ("button_import_mode", "导入模式", self.import_mode_config),
            ("button_export_mode", "导出模式", self.export_mode_config),
            ("button_refresh_mode", "刷新模式", self.refresh_mode_config),
            ("button_reset_mode_config", "恢复模式", self.reset_mode_config),
            ("button_reset_mode_detail", "恢复模式详情", self.reset_mode_detail_config, 14),
            ("button_edit_mode_detail", "编辑", self.tree_mode_detail_edit),
        ]
        for config in button_configs:
            name, text, command = config[0], config[1], config[2]
            width = config[3] if len(config) > 3 else 12
            self.UIObject[name] = tkinter.Button(
                self.UIObject["button_frame_mode"],
                text=text,
                command=command,
                bd=0,
                activebackground=self.UIConfig["color_002"],
                activeforeground=self.UIConfig["color_001"],
                bg=self.UIConfig["color_003"],
                fg=self.UIConfig["color_004"],
                relief="groove",
                height=2,
                width=width,
            )
            self.UIObject[name].bind("<Enter>", lambda x: self.button_action(name, "<Enter>"))
            self.UIObject[name].bind("<Leave>", lambda x: self.button_action(name, "<Leave>"))
        # 按钮布局
        # 左侧按钮：恢复默认、导入、导出、刷新
        for name in ["button_reset_mode_default", "button_import_mode", "button_export_mode", "button_refresh_mode"]:
            self.UIObject[name].pack(side=tkinter.LEFT, padx=(0, 5))
        # 右侧按钮：恢复模式、恢复模式详情、编辑（从右到左）
        for name in ["button_edit_mode_detail", "button_reset_mode_detail", "button_reset_mode_config"]:
            self.UIObject[name].pack(side=tkinter.RIGHT, padx=(0, 5))

    def tree_mode_select(self):
        """模式选择事件"""
        for child in self.UIObject["tree_mode_detail"].get_children():
            self.UIObject["tree_mode_detail"].delete(child)

        selection = self.UIObject["tree_mode"].selection()
        if not selection:
            return
        item = self.UIObject["tree_mode"].item(selection[0])
        mode_name = item["values"][0]
        source_data = dictDefsMode["default"] if self.UIData["hash_now"] == "unity" else dictDefsMode[self.UIData["hash_now"]]
        mode_data = source_data.get(mode_name)
        if not mode_data:
            return

        # 字段配置
        field_configs = [
            ("brief", "strModeBrief"),
            ("points", "strModePoints"),
            ("seats_default", "strModeSeatsDefault"),
            ("seats_min", "strModeSeatsMin"),
            ("seats_max", "strModeSeatsMax"),
            ("props_pool", "strModePropsPool"),
            ("props_limit", "strModePropsLimit"),
            ("props_ban", "strModePropsBan"),
            ("modify_dmg", "strModeModifyDmg"),
            ("modify_ammo_show", "strModeModifyAmmoShow"),
            ("modify_bullet_show", "strModeModifyBulletShow"),
        ]

        for field_key, note_key in field_configs:
            value = ""
            note_text = dictDefsNote.get(note_key, "")
            if field_key == "brief":
                value = mode_data.get("brief", "").replace("\n", "\\n")
            elif field_key == "points":
                value = str(mode_data.get("points", 0))
            elif field_key.startswith("seats_"):
                seats = mode_data.get("seats", {})
                if field_key == "seats_default":
                    value = str(seats.get("default", 2))
                elif field_key == "seats_min":
                    value = str(seats.get("min", 2))
                elif field_key == "seats_max":
                    value = str(seats.get("max", 8))
            elif field_key.startswith("props_"):
                props = mode_data.get("props", {})
                if field_key == "props_pool":
                    lst = props.get("pool", [])
                    value = ", ".join(lst) if lst else "（空）"
                elif field_key == "props_ban":
                    lst = props.get("ban", [])
                    value = ", ".join(lst) if lst else "（空）"
                elif field_key == "props_limit":
                    value = str(props.get("limit", 0))
            elif field_key.startswith("modify_"):
                modify = mode_data.get("modify", {})
                if field_key == "modify_dmg":
                    value = str(modify.get("dmg", 1))
                elif field_key == "modify_ammo_show":
                    value = str(int(modify.get("ammo_show", 1)))
                elif field_key == "modify_bullet_show":
                    value = str(int(modify.get("bullet_show", 0)))
            self.UIObject["tree_mode_detail"].insert(
                "",
                "end",
                text=note_key,
                values=(note_text, value),
                tags=(field_key,),
            )

    def update_mode_helpdoc(self, mode_name, mode_data):
        """更新帮助文档"""
        current_hash = self.UIData["hash_now"]
        OlivaDiceCore.helpDocData.dictHelpDoc[current_hash][f"恶赌模式 {mode_name}"] = mode_data["brief"]

    def reset_mode_default(self):
        """恢复模式默认值"""
        if not messagebox.askyesno(
            "确认恢复",
            f"确定要恢复当前账号的模式配置为默认值吗？这将覆盖所有自定义修改。",
            parent=self.UIObject["root"],
        ):
            return

        current_hash = self.UIData["hash_now"]
        default_modes = copy.deepcopy(dictDefsMode["default"])
        dictDefsMode[current_hash] = default_modes
        # 更新帮助文档
        for mode_name, mode_data in default_modes.items():
            self.update_mode_helpdoc(mode_name, mode_data)
        # 保存到文件
        file_path = config.dataDirRoot + "/" + current_hash + "/customMode.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default_modes, f, ensure_ascii=False, indent=4)
        self.init_data_total()
        messagebox.showinfo("完成", "模式配置已恢复为默认值", parent=self.UIObject["root"])

    def import_mode_config(self):
        """导入模式配置"""
        file_path = filedialog.askopenfilename(
            title="选择模式配置文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            parent=self.UIObject["root"],
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                import_data = json.load(f)
            if not isinstance(import_data, dict):
                raise ValueError("配置文件格式不正确，必须是一个JSON文件")
            if not messagebox.askyesno(
                "确认导入",
                f"确定要导入模式配置吗？这将覆盖当前账号的所有模式配置。",
                parent=self.UIObject["root"],
            ):
                return
            current_hash = self.UIData["hash_now"]
            # 备份当前数据（用于失败回滚）
            backup = copy.deepcopy(dictDefsMode.get(current_hash, {}))
            try:
                # 更新全局
                dictDefsMode[current_hash] = import_data
                # 更新帮助文档
                for mode_name, mode_data in import_data.items():
                    self.update_mode_helpdoc(mode_name, mode_data)
                # 保存文件
                file_path = config.dataDirRoot + "/" + current_hash + "/customMode.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(import_data, f, ensure_ascii=False, indent=4)
                self.init_data_total()
                messagebox.showinfo("完成", "模式配置导入成功", parent=self.UIObject["root"])
            except Exception as e:
                # 回滚
                dictDefsMode[current_hash] = backup
                for mode_name, mode_data in backup.items():
                    self.update_mode_helpdoc(mode_name, mode_data)
                raise
        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {str(e)}\n配置未更改", parent=self.UIObject["root"])

    def export_mode_config(self):
        """导出模式配置"""
        file_path = filedialog.asksaveasfilename(
            title="保存模式配置文件",
            defaultextension=".json",
            initialfile="customMode.json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            parent=self.UIObject["root"],
        )
        if not file_path:
            return
        try:
            current_hash = self.UIData["hash_now"]
            export_data = dictDefsMode.get(current_hash, {})
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("完成", "模式配置导出成功", parent=self.UIObject["root"])
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}", parent=self.UIObject["root"])

    def refresh_mode_config(self):
        """刷新模式配置"""
        if not messagebox.askyesno(
            "确认刷新",
            "确定要从文件重新加载模式配置吗？这将覆盖当前内存中的修改。",
            parent=self.UIObject["root"],
        ):
            return
        current_hash = self.UIData["hash_now"]
        file_path = config.dataDirRoot + "/" + current_hash + "/customMode.json"
        backup = copy.deepcopy(dictDefsMode.get(current_hash, {}))
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if not isinstance(loaded, dict):
                    raise ValueError("自定义模式配置文件格式不正确")
                dictDefsMode[current_hash] = loaded
            else:
                dictDefsMode[current_hash] = copy.deepcopy(dictDefsMode["default"])
            # 更新帮助文档
            for mode_name, mode_data in loaded.items():
                self.update_mode_helpdoc(mode_name, mode_data)
            self.init_data_total()
            messagebox.showinfo("完成", "模式配置刷新成功", parent=self.UIObject["root"])
        except Exception as e:
            # 回滚
            dictDefsMode[current_hash] = backup
            for mode_name, mode_data in backup.items():
                self.update_mode_helpdoc(mode_name, mode_data)
            messagebox.showerror("错误", f"刷新失败: {str(e)}\n配置未更改", parent=self.UIObject["root"])

    def reset_mode_config(self):
        """恢复模式配置"""
        current_hash = self.UIData["hash_now"]
        root = self.UIObject["root"]
        mode_selection = self.UIObject["tree_mode"].selection()
        if not mode_selection:
            messagebox.showwarning("警告", "请先选择要操作的模式", parent=root)
            return

        mode_item = self.UIObject["tree_mode"].item(mode_selection[0])
        mode_name = mode_item["values"][0]
        if not messagebox.askyesno(
            "确认恢复",
            f"确定要恢复'{mode_name}'模式为默认值吗？",
            parent=root,
        ):
            return
        dictDefsMode[current_hash][mode_name] = copy.deepcopy(dictDefsMode["default"][mode_name])
        self.update_mode_helpdoc(mode_name, dictDefsMode[current_hash][mode_name])
        file_path = config.dataDirRoot + "/" + current_hash + "/customMode.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(dictDefsMode[current_hash], f, ensure_ascii=False, indent=4)
        self.init_data_total()

    def reset_mode_detail_config(self):
        """恢复模式字段配置"""
        current_hash = self.UIData["hash_now"]
        root = self.UIObject["root"]

        mode_selection = self.UIObject["tree_mode"].selection()
        if not mode_selection:
            messagebox.showwarning("警告", "请先选择要操作的模式", parent=root)
            return
        mode_item = self.UIObject["tree_mode"].item(mode_selection[0])
        mode_name = mode_item["values"][0]

        detail_selection = self.UIObject["tree_mode_detail"].selection()
        if not detail_selection:
            messagebox.showwarning("警告", "请先选择要操作的字段", parent=root)
            return

        item = self.UIObject["tree_mode_detail"].item(detail_selection[0])
        field_key = item["tags"][0] if item["tags"] else None

        if not messagebox.askyesno(
            "确认恢复",
            f"确定要将恢复'{mode_name}'的'{field_key}'字段为默认值吗？",
            parent=root,
        ):
            return

        default_modes = copy.deepcopy(dictDefsMode["default"][mode_name])
        current_data = dictDefsMode[current_hash][mode_name]
        # 根据字段类型更新数据
        if field_key in ("brief", "points"):
            current_data[field_key] = default_modes[field_key]
            if field_key == "brief":
                self.update_mode_helpdoc(mode_name, current_data)
        elif field_key in ("seats_default", "seats_min", "seats_max"):
            key_map = {
                "seats_default": "default",
                "seats_min": "min",
                "seats_max": "max",
            }
            field_key = key_map[field_key]
            current_data["seats"][field_key] = default_modes["seats"][field_key]
        elif field_key in ("props_pool", "props_limit", "props_ban"):
            if field_key == "props_pool":
                current_data["props"]["pool"] = default_modes["props"]["pool"]
            elif field_key == "props_limit":
                current_data["props"]["limit"] = default_modes["props"]["limit"]
            elif field_key == "props_ban":
                current_data["props"]["ban"] = default_modes["props"]["ban"]
        elif field_key in ("modify_dmg", "modify_ammo_show", "modify_bullet_show"):
            key_map = {
                "modify_dmg": "dmg",
                "modify_ammo_show": "ammo_show",
                "modify_bullet_show": "bullet_show",
            }
            field_key = key_map[field_key]
            current_data["modify"][field_key] = default_modes["modify"][field_key]
        # 保存并刷新
        file_path = config.dataDirRoot + "/" + current_hash + "/customMode.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(dictDefsMode[current_hash], f, ensure_ascii=False, indent=4)
        self.init_data_total()

    def tree_mode_detail_edit(self):
        """模式字段编辑事件"""
        selection = self.UIObject["tree_mode_detail"].selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要编辑的字段", parent=self.UIObject["root"])
            return
        item = self.UIObject["tree_mode_detail"].item(selection[0])
        tags = item["tags"]
        if not tags:
            messagebox.showwarning("警告", "无法识别选中的字段", parent=self.UIObject["root"])
            return
        field_key = tags[0]
        display_name = item["text"]  # 条目名（即 note_key）
        note_text = item["values"][0] if item["values"] else ""

        mode_selection = self.UIObject["tree_mode"].selection()
        if not mode_selection:
            return
        mode_item = self.UIObject["tree_mode"].item(mode_selection[0])
        mode_name = mode_item["values"][0]
        mode_data = dictDefsMode[self.UIData["hash_now"]].get(mode_name)
        if not mode_data:
            return

        if field_key == "brief":
            current_value = mode_data.get("brief", "")
        elif field_key == "points":
            current_value = str(mode_data.get("points", 0))
        elif field_key.startswith("seats_"):
            seats = mode_data.get("seats", {})
            if field_key == "seats_default":
                current_value = str(seats.get("default", 2))
            elif field_key == "seats_min":
                current_value = str(seats.get("min", 2))
            elif field_key == "seats_max":
                current_value = str(seats.get("max", 8))
        elif field_key.startswith("props_"):
            props = mode_data.get("props", {})
            if field_key == "props_pool":
                lst = props.get("pool", [])
                current_value = ", ".join(lst) if lst else ""
            elif field_key == "props_ban":
                lst = props.get("ban", [])
                current_value = ", ".join(lst) if lst else ""
            elif field_key == "props_limit":
                current_value = str(props.get("limit", 0))
        elif field_key.startswith("modify_"):
            modify = mode_data.get("modify", {})
            if field_key == "modify_dmg":
                current_value = str(modify.get("dmg", 1))
            elif field_key == "modify_ammo_show":
                current_value = bool(modify.get("ammo_show", 1))
            elif field_key == "modify_bullet_show":
                current_value = bool(modify.get("bullet_show", 0))

        self.edit_mode_UI(
            root_class=self,
            mode_name=mode_name,
            field_key=field_key,
            display_name=display_name,
            note_text=note_text,
            current_value=current_value,
            mode_data=mode_data,
        ).start()

    class edit_mode_UI(object):
        def __init__(
            self,
            root_class,
            mode_name,
            field_key,
            display_name,
            note_text,
            current_value,
            mode_data,
        ):
            self.root_class = root_class
            self.mode_name = mode_name
            self.field_key = field_key
            self.display_name = display_name
            self.note_text = note_text
            self.current_value = current_value
            self.mode_data = mode_data
            self.UIObject = {}
            self.UIConfig = {}
            self.UIConfig.update(dictColorContext)

        def start(self):
            self.UIObject["root"] = tkinter.Toplevel(self.root_class.UIObject["root"])
            self.UIObject["root"].title("修改设置 - %s" % self.display_name)
            self.UIObject["root"].geometry("400x300")
            self.UIObject["root"].minsize(400, 300)
            self.UIObject["root"].resizable(True, True)
            self.UIObject["root"].grid_rowconfigure(0, weight=0)
            self.UIObject["root"].grid_rowconfigure(1, weight=15)
            self.UIObject["root"].grid_columnconfigure(0, weight=15)
            self.UIObject["root"].configure(bg=self.UIConfig["color_001"])

            # 编辑窗口标签显示说明（note_text），即对应的中文解释
            label_text = self.note_text if self.note_text else self.display_name
            label_note = tkinter.Label(
                self.UIObject["root"],
                text=label_text,
                font=("等线", 12, "bold"),
                bg=self.UIConfig["color_001"],
                fg=self.UIConfig["color_004"],
                justify="left",
                anchor="nw",
            )
            label_note.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)

            self.UIObject["text_edit"] = tkinter.Text(
                self.UIObject["root"],
                wrap=tkinter.WORD,
                bg=self.UIConfig["color_004"],
                fg=self.UIConfig["color_005"],
                bd=0,
                font=(None, 10),  # type: ignore
                padx=4,
                pady=8,
            )
            self.UIObject["text_edit"].grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
            self.UIObject["text_edit"].insert("1.0", self.current_value)

            self.UIObject["root"].iconbitmap("./resource/tmp_favoricon.ico")
            self.UIObject["root"].protocol("WM_DELETE_WINDOW", self.quit)
            self.UIObject["root"].mainloop()

        def quit(self):
            self.save()
            self.UIObject["root"].destroy()

        def save(self):
            new_value = self.UIObject["text_edit"].get("1.0", tkinter.END)
            if new_value.endswith("\n"):
                new_value = new_value[:-1]
            self.root_class.save_mode_detail(self.mode_name, self.field_key, new_value)
            self.root_class.init_data_total()

    def save_mode_detail(self, mode_name, field_key, new_value):
        """保存模式字段配置"""
        current_hash = self.UIData["hash_now"]
        mode_dict = dictDefsMode.get(current_hash, {})
        if mode_name not in mode_dict:
            return
        mode_data = mode_dict[mode_name]

        try:
            if field_key == "brief":
                mode_data["brief"] = new_value
                self.update_mode_helpdoc(mode_name, mode_data)
            elif field_key == "points":
                mode_data["points"] = int(new_value)
            elif field_key.startswith("seats_"):
                seats = mode_data.setdefault("seats", {})
                if field_key == "seats_default":
                    seats["default"] = int(new_value)
                elif field_key == "seats_min":
                    seats["min"] = int(new_value)
                elif field_key == "seats_max":
                    seats["max"] = int(new_value)
            elif field_key.startswith("props_"):
                props = mode_data.setdefault("props", {})
                if field_key == "props_limit":
                    props["limit"] = int(new_value)
                elif field_key == "props_pool":
                    lst = [item.strip() for item in new_value.split(",") if item.strip()]
                    props["pool"] = lst
                elif field_key == "props_ban":
                    lst = [item.strip() for item in new_value.split(",") if item.strip()]
                    props["ban"] = lst
            elif field_key.startswith("modify_"):
                modify = mode_data.setdefault("modify", {})
                if field_key == "modify_dmg":
                    modify["dmg"] = int(new_value)
                elif field_key == "modify_ammo_show":
                    modify["ammo_show"] = bool(int(new_value))
                elif field_key == "modify_bullet_show":
                    modify["bullet_show"] = bool(int(new_value))
        except ValueError:
            messagebox.showerror("错误", "请输入正确的数值", parent=self.UIObject["root"])
            return
        file_path = config.dataDirRoot + "/" + current_hash + "/customMode.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(dictDefsMode[current_hash], f, ensure_ascii=False, indent=4)

    # endregion
