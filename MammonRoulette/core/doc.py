class helpdoc:
    doc = {
        "mod": "恶魔轮盘帮助文档",
        "author": "星瑚",
        "brief": "恶魔轮盘模式、道具、指令查询",
        "comment": "恶赌",
        "helpdoc": {},
    }
    _cmd_doc = {}

    @classmethod
    def append_cmd(cls, cmd_type: str, content: str):
        cls._cmd_doc.setdefault(cmd_type, []).append(content)

        def decorator(handler):
            return handler

        return decorator

    @classmethod
    def update_cmd(cls):
        cmd_doc = "[游戏命令](支持部分繁體字)\n"
        cls.doc["helpdoc"]["恶赌命令"] = cmd_doc + "\n".join(
            [
                f"〔{cat}〕\n{chr(10).join(content_list)}"
                for cat, content_list in cls._cmd_doc.items()
            ]
        )
        return
