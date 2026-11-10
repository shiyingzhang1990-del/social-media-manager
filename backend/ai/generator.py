"""
Rule-based AI content generator with platform-specific patterns.
"""
import random
import re


def _sanitize(text: str) -> str:
    """Strip surrogate characters that break JSON encoding."""
    return re.sub(r'[\ud800-\udfff]', '', text)


PLATFORM_STYLES = {
    "xiaohongshu": {
        "name": "小红书",
        "max_length": 1000,
        "openings": [
            "姐妹们！今天来分享一个宝藏内容\u2728",
            "\ud83d\udd25绝绝子！必须安利给大家",
            "救命！这也太香了吧\ud83d\ude0d",
            "发现一个超棒的\ud83d\udc49",
            "不允许还有人不知道这个！",
        ],
        "closings": [
            "\u2764\ufe0f 觉得有用的话点赞收藏哦~",
            "\ud83c\udf1f 关注我，每天分享干货",
            "\ud83d\udcac 评论区告诉我你的想法",
            "\ud83d\udc47 你的支持是我更新的动力",
        ],
        "phrases": ["绝绝子", "yyds", "真香", "宝藏", "安利", "干货", "避雷", "亲测有效", "冲就完了", "入股不亏"],
        "hashtag_prefixes": ["#", "#"],
        "emoji_rate": 0.3,
    },
    "weibo": {
        "name": "微博",
        "max_length": 2000,
        "openings": [
            "\u3010重磅\u3011",
            "\u2605\u65b0\u6d88\u606f\uff01",
            "\ud83d\udce3 \u5206\u4eab\u4e00\u4e2a\u70ed\u70b9",
            "\ud83d\udd25\u70ed\u641c\u9884\u5b9a",
        ],
        "closings": [
            "\u2192\u8f6c\u53d1\u8ba9\u66f4\u591a\u4eba\u770b\u5230",
            "\u4f60\u600e\u4e48\u770b\uff1f",
            "\u8bc4\u8bba\u533a\u804a\u804a",
        ],
        "phrases": ["重磅", "官宣", "热议", "焦点", "关注", "现象级", "破圈", "刷屏"],
        "hashtag_prefixes": ["#", "#"],
        "emoji_rate": 0.1,
    },
    "bilibili": {
        "name": "B站",
        "max_length": 4000,
        "openings": [
            "\u5404\u4f4d\u5c0f\u4f19\u4f34\u4eec\uff0c\u4eca\u5929\u7ed9\u5927\u5bb6\u5e26\u6765\u4e00\u4e2a\u8d85\u7ea7\u5e72\u8d27\uff01",
            "\u54c8\u54c8\uff0c\u53c8\u5230\u4e86\u6211\u4eec\u7684\u5206\u4eab\u65f6\u95f4\uff01",
            "\u5f39\u5e55\u8d70\u8d77\u6765\uff01\u4eca\u5929\u804a\u804a...",
            "\u5927\u5bb6\u597d\uff0c\u8fd9\u671f\u89c6\u9891\u6211\u4eec\u6765\u8bf4\u8bf4...",
            "\u8fd9\u6ce2\u5c5e\u4e8e\u662f\u628a\u6211\u770b\u50bb\u4e86...",
        ],
        "closings": [
            "\ud83d\udc4d \u4e09\u8fde\u652f\u6301\u4e00\u4e0b\uff0c\u611f\u8c22\u5927\u5bb6\uff01",
            "\u89c9\u5f97\u6709\u7528\u7684\u8bdd\u4e00\u952e\u4e09\u8fde\u54e6\uff5e",
            "\u8fd8\u60f3\u770b\u4ec0\u4e48\u5185\u5bb9\uff0c\u5f39\u5e55\u544a\u8bc9\u6211\uff01",
        ],
        "phrases": ["三连", "硬币", "弹幕", "UP主", "硬核", "整活", "有料", "干货满满", "收藏比赞多"],
        "hashtag_prefixes": ["#", "#"],
        "emoji_rate": 0.15,
    },
    "douyin": {
        "name": "抖音",
        "max_length": 500,
        "openings": [
            "\u4f60\u4e0d\u4fe1\uff1f\u770b\u5b8c\u8fd9\u4e2a\u89c6\u9891\u4f60\u5c31\u77e5\u9053\u4e86",
            "\u8fd9\u4e2a\u771f\u7684\u592a\u2026\u2026",
            "\u522b\u5212\u8d70\uff01\u8fd9\u4e2a\u4f60\u4e00\u5b9a\u8981\u770b",
            "\ud83d\ude31 \u8fd9\u662f\u6211\u89c1\u8fc7\u6700\u2026\u2026",
        ],
        "closings": [
            "\u5173\u6ce8\u6211\uff0c\u6bcf\u5929\u66f4\u65b0\uff01",
            "\u8d76\u7d27\u8bd5\u8bd5\u5427\uff01",
            "\u4f60\u5b66\u4f1a\u4e86\u5417\uff1f",
        ],
        "phrases": ["绝了", "离谱", "上头", "出圈", "好玩", "必须火", "热门", "上热门", "流量密码"],
        "hashtag_prefixes": ["#", "#"],
        "emoji_rate": 0.2,
    },
    "wechat": {
        "name": "微信",
        "max_length": 20000,
        "openings": [
            "\u5728\u5f53\u4eca\u8fd9\u4e2a\u65f6\u4ee3\uff0c",
            "\u8fd1\u65e5\uff0c\u6211\u4eec\u6ce8\u610f\u5230\u2026\u2026",
            "\u4f5c\u4e3a\u4e00\u540d\u6df1\u8015\u884c\u4e1a\u7684\u4ece\u4e1a\u8005\uff0c",
            "\u968f\u7740\u6280\u672f\u7684\u53d1\u5c55\uff0c",
        ],
        "closings": [
            "\u6b22\u8fce\u5728\u8bc4\u8bba\u533a\u7559\u4e0b\u4f60\u7684\u89c2\u70b9\u3002",
            "\u671f\u5f85\u4e0e\u4f60\u7684\u4ea4\u6d41\u3002",
            "\u611f\u8c22\u60a8\u7684\u9605\u8bfb\u3002",
        ],
        "phrases": ["深度", "洞察", "趋势", "价值", "创新", "赋能", "生态", "布局", "赛道", "闭环"],
        "hashtag_prefixes": ["#", "#"],
        "emoji_rate": 0.05,
    },
}

TONE_MODIFIERS = {
    "professional": {"phrases": ["专业的", "权威", "数据", "分析", "研究"], "formality": 1.0},
    "casual": {"phrases": ["随便聊聊", "分享", "心得", "体验"], "formality": 0.3},
    "enthusiastic": {"phrases": ["太棒了", "超级", "无敌", "爆赞"], "formality": 0.2},
    "informative": {"phrases": ["干货", "教程", "指南", "步骤", "方法"], "formality": 0.7},
}

TOPIC_TEMPLATES = {
    "product": {
        "titles": ["{product}深度测评：到底值不值得买？", "{product}使用{sense}天真实体验", "全网最全{product}攻略来了！", "{product}避坑指南，这些你一定要知道"],
        "bodies": [
            "最近{product}真的太火了，今天给大家做一个全方位的分享。\n\n首先是外观/第一印象：{product}的设计真的{positive}。\n\n然后是使用体验：用了{sense}天之后，最大的感受就是{feeling}。\n\n总结来说，{conclusion}",
        ],
    },
    "knowledge": {
        "titles": ["{sense}个关于{topic}你必须知道的事", "{topic}入门指南：从零开始", "搞懂{topic}，看这一篇就够了", "为什么说{topic}是未来的趋势？"],
        "bodies": [
            "很多人都在问{topic}到底是什么？今天用最简单的话给大家讲清楚。\n\n首先，{topic}的核心就是{core}。\n\n这里分享{sense}个关键点：\n1. {point1}\n2. {point2}\n3. {point3}\n\n掌握了这些，你就能{benefit}。",
        ],
    },
    "lifestyle": {
        "titles": ["{sense}个让生活更美好的小技巧", "我的{topic}日常分享\u2728", "最近发现的{topic}好物合集", "终于找到了完美的{topic}方案"],
        "bodies": [
            "每天都在用的{topic}相关好物，真的提升幸福感！\n\n最近尝试了{point1}，效果真的{positive}。\n\n还有一个很重要的是{point2}，这可以说是{benefit}。\n\n希望这些分享对你有帮助~",
        ],
    },
    "news": {
        "titles": ["重磅！{topic}最新动态来了", "关于{topic}，你必须知道的{sense}件事", "{topic}又有了新变化"],
        "bodies": [
            "最新消息：关于{topic}，有几个重要变化值得关注。\n\n{point1}\n\n{point2}\n\n{point3}\n\n这些变化意味着{conclusion}。",
        ],
    },
}


class ContentGenerator:
    """Rule-based content generator with platform and tone awareness."""

    def __init__(self, platform: str, tone: str = "casual", category: str = "product"):
        self.platform = platform
        self.tone = tone
        self.category = category
        self.style = PLATFORM_STYLES.get(platform, PLATFORM_STYLES["weibo"])
        self.tone_mod = TONE_MODIFIERS.get(tone, TONE_MODIFIERS["casual"])
        self.template = TOPIC_TEMPLATES.get(category, TOPIC_TEMPLATES["product"])

    def _pick(self, items: list[str]) -> str:
        return random.choice(items)

    def _fill(self, template: str, **kwargs) -> str:
        result = template
        for key, value in kwargs.items():
            result = result.replace("{" + key + "}", str(value))
        return result

    def generate_title(self, topic: str, **kwargs) -> str:
        title_tpl = self._pick(self.template["titles"])
        defaults = {
            "topic": topic,
            "product": topic,
            "sense": str(random.choice([3, 5, 7, 10])),
        }
        defaults.update(kwargs)
        return self._fill(title_tpl, **defaults)

    def generate_body(self, topic: str, **kwargs) -> str:
        body_tpl = self._pick(self.template["bodies"])
        defaults = {
            "topic": topic,
            "product": topic,
            "positive": self._pick(["惊艳", "出色", "令人满意", "超出预期", "非常棒"]),
            "feeling": self._pick(["效率提升了", "体验感拉满", "真的很方便", "太舒服了"]),
            "conclusion": self._pick(["强烈推荐！", "值得入手。", "可以冲！", "建议观望一下。"]),
            "core": self._pick(["用户体验", "技术创新", "效率提升", "品质保证"]),
            "point1": self._pick(["了解基本原理", "选对工具很重要", "建立自己的方法论", "关注行业趋势"]),
            "point2": self._pick(["持续实践和反馈", "向有经验的人学习", "定期复盘总结", "保持好奇心和探索"]),
            "point3": self._pick(["形成自己的风格", "积累案例和经验", "建立长期规划", "加入社群交流"]),
            "benefit": self._pick(["事半功倍", "少走很多弯路", "更快上手", "真正掌握"]),
            "sense": str(random.choice([3, 5, 7, 10])),
        }
        defaults.update(kwargs)

        body = self._fill(body_tpl, **defaults)
        opening = self._pick(self.style["openings"])
        closing = self._pick(self.style["closings"])
        return f"{opening}\n\n{body}\n\n{closing}"

    def generate_hashtags(self, topic: str, count: int = 5) -> list[str]:
        base_tags = topic.replace("，", ",").replace("、", ",").split(",")
        base_tags = [t.strip() for t in base_tags if t.strip()]

        platform_tags = random.sample(
            self.style["phrases"], min(3, len(self.style["phrases"]))
        )
        tone_tags = random.sample(
            self.tone_mod["phrases"], min(2, len(self.tone_mod["phrases"]))
        )

        all_tags = base_tags + platform_tags + tone_tags
        seen = set()
        unique = []
        for t in all_tags:
            tag = f"#{t}"
            if tag not in seen:
                seen.add(tag)
                unique.append(tag)

        return unique[:count]

    def generate(self, topic: str, **kwargs) -> dict:
        title = self.generate_title(topic, **kwargs)
        body = self.generate_body(topic, **kwargs)
        hashtags = self.generate_hashtags(topic, kwargs.get("hashtag_count", 5))
        return {
            "title": _sanitize(title),
            "text": _sanitize(body[: self.style["max_length"]]),
            "tags": [_sanitize(t) for t in hashtags],
            "platform": self.platform,
            "content_type": kwargs.get("content_type", "text"),
        }


def generate_content(
    platform: str,
    topic: str,
    tone: str = "casual",
    category: str = "product",
    **kwargs,
) -> dict:
    gen = ContentGenerator(platform, tone, category)
    return gen.generate(topic, **kwargs)


def generate_hashtags(platform: str, topic: str, count: int = 8) -> list[str]:
    gen = ContentGenerator(platform, "casual", "product")
    return gen.generate_hashtags(topic, count)
