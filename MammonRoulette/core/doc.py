class helpdoc:
    doc = {
        "mod": "恶魔轮盘帮助文档",
        "author": "星瑚",
        "brief": "恶魔轮盘模式、道具、指令查询",
        "comment": "恶赌",
        "helpdoc": {"恶赌命令": ("[命令](支持繁体字)")},
    }

    @classmethod
    def append_cmd(cls, content):
        cls.doc["helpdoc"]["恶赌命令"] += f"\n{content}"
        return
