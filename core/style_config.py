from typing import Dict


STORY_TYPES = {
    "1": {"name": "短剧", "desc": "适合AI视频生成，多集"},
    "2": {"name": "电影", "desc": "完整三幕结构"},
    "3": {"name": "电视剧", "desc": "多集/多季"},
    "4": {"name": "小说/网文", "desc": "纯文字，按章节"},
    "5": {"name": "舞台剧/话剧", "desc": "幕场结构"},
    "6": {"name": "广播剧/有声书", "desc": "声音驱动，无画面"},
}

GENRE_TAGS = [
    "科幻", "奇幻", "悬疑", "古装", "现代", "都市", "爱情", "动作",
    "冒险", "武侠", "仙侠", "历史", "战争", "犯罪", "谍战", "警匪",
    "喜剧", "末世", "恐怖", "灵异", "家庭", "伦理", "校园", "青春",
    "职场", "音乐", "传记",
]

WRITING_STYLES = {
    "1": {"name": "精炼实用", "desc": "干净利落，适合短剧/快节奏"},
    "2": {"name": "文学质感", "desc": "细腻生动，适合小说/文艺片"},
    "3": {"name": "对白优先", "desc": "对话驱动，适合舞台剧/广播剧"},
    "4": {"name": "画面感强", "desc": "视觉化描写，适合电影"},
    "5": {"name": "自动适配", "desc": "根据故事类型自动选择最优风格"},
}

VISUAL_STYLES = {
    "1": {"name": "好莱坞大片风", "desc": "三幕结构、视觉冲击、电影感镜头语言"},
    "2": {"name": "竖屏短剧风", "desc": "快节奏、强反转、情绪密集"},
    "3": {"name": "文艺/独立风", "desc": "慢节奏、长镜头、情绪留白"},
    "4": {"name": "日韩生活风", "desc": "细腻日常、温暖治愈、轻节奏"},
    "5": {"name": "电视剧风", "desc": "多线叙事、人物群像"},
    "6": {"name": "自动适配", "desc": "让AI根据故事类型和题材自动选择最优视觉风格"},
}

SCREEN_ASPECTS = {
    "1": {"name": "9:16 竖屏", "desc": "强调人物近景/纵深"},
    "2": {"name": "16:9 横屏", "desc": "强调横向调度"},
    "3": {"name": "自适应", "desc": "让Agent根据故事类型自动选择"},
}

SCRIPT_STYLES = {
    "1": {"name": "视觉化写作", "desc": "动作描写先行，对白精炼，show dont tell"},
    "2": {"name": "对白驱动型", "desc": "大量对白驱动剧情，轻描写重对话"},
    "3": {"name": "文学剧本型", "desc": "细腻动作/心理描写+对白，文体接近文学"},
    "4": {"name": "自动适配", "desc": "让AI根据故事类型和题材自动选择剧本写作风格"},
}

MOOD_TAGS = [
    "悬疑紧张", "轻松治愈", "热血激昂", "阴冷压抑", "温暖感人",
    "幽默诙谐", "黑暗深沉", "文艺清新", "史诗宏大", "诡异迷幻",
    "简约克制", "华丽张扬",
]

RENDER_STYLES = {
    "1": {"name": "写实/真人", "desc": "接近真实摄影质感，适合悬疑/剧情/动作"},
    "2": {"name": "2D 动画", "desc": "手绘动画质感，适合动漫风格"},
    "3": {"name": "3D CG", "desc": "三维渲染质感，适合科幻/奇幻"},
    "4": {"name": "卡通/风格化", "desc": "夸张造型，色彩鲜明，适合喜剧/儿童"},
    "5": {"name": "水墨/国风", "desc": "中国传统绘画风格，适合古装/武侠"},
    "6": {"name": "像素/复古", "desc": "低分辨率游戏像素风，适合怀旧"},
    "7": {"name": "自动适配", "desc": "让 AI 根据故事类型和题材自动选择画风"},
}

VIDEO_PLATFORMS = {
    "1": {"name": "Seedance 2.0", "desc": "推荐 - 人物表情自然"},
    "2": {"name": "可灵 Kling", "desc": "短剧常用，国风效果好"},
    "3": {"name": "Runway Gen-3", "desc": "电影感画面"},
    "4": {"name": "Sora", "desc": "物理模拟强"},
}

IMAGE_PLATFORMS = {
    "1": {"name": "Seedream", "desc": "火山引擎文生图，与Seedance同生态"},
    "2": {"name": "DALL-E 3", "desc": "OpenAI 图像生成"},
    "3": {"name": "Midjourney", "desc": "高质量艺术风格"},
}

DURATION_OPTIONS = {
    "1": {"name": "自动时长", "desc": "让Agent根据故事类型和内容自动推荐时长"},
    "2": {"name": "自定义时长", "desc": "手动输入单集时长和总集数"},
}

SCRIPT_FORMATS = {
    "1": {"name": "系统格式", "desc": "适合内部创作和AI分镜生成"},
    "2": {"name": "市场格式", "desc": "适合对外交付和专业合作，符合行业标准"},
}


class StyleConfig:
    def __init__(self):
        self.story_type: str = ""
        self.genre: str = ""
        self.writing_style: str = ""
        self.visual_style: str = ""
        self.art_style: str = ""
        self.screen_aspect: str = ""
        self.script_style: str = ""
        self.script_format: str = ""
        self.duration_mode: str = ""
        self.episode_count: str = ""
        self.episode_duration: str = ""
        self.mood: str = ""
        self.custom_requirements: str = ""
        self.visual_reference: str = ""
        self.action_reference: str = ""

    def to_dict(self) -> Dict:
        return {
            "story_type": self.story_type,
            "genre": self.genre,
            "writing_style": self.writing_style,
            "visual_style": self.visual_style,
            "art_style": self.art_style,
            "screen_aspect": self.screen_aspect,
            "script_style": self.script_style,
            "script_format": self.script_format,
            "duration_mode": self.duration_mode,
            "episode_count": self.episode_count,
            "episode_duration": self.episode_duration,
            "mood": self.mood,
            "custom_requirements": self.custom_requirements,
            "visual_reference": self.visual_reference,
            "action_reference": self.action_reference,
        }

    def to_yaml_string(self) -> str:
        _name = lambda m, k: m.get(k, {}).get("name", k) if k else k
        lines = [
            "# 风格配置文件（自动生成）",
            f"story_type: {_name(STORY_TYPES, self.story_type)}",
            f"genre: {self.genre}",
            f"writing_style: {_name(WRITING_STYLES, self.writing_style)}",
            f"visual_style: {_name(VISUAL_STYLES, self.visual_style)}",
            f"art_style: {_name(RENDER_STYLES, self.art_style)}",
            f"screen_aspect: {_name(SCREEN_ASPECTS, self.screen_aspect)}",
            f"script_style: {_name(SCRIPT_STYLES, self.script_style)}",
            f"script_format: {_name(SCRIPT_FORMATS, self.script_format)}",
            f"duration_mode: {self.duration_mode}",
        ]
        if self.episode_count:
            lines.append(f"episode_count: {self.episode_count}")
        if self.episode_duration:
            lines.append(f"episode_duration: {self.episode_duration}")
        if self.mood:
            lines.append(f"mood: {self.mood}")
        if self.custom_requirements:
            lines.append(f"custom_requirements: {self.custom_requirements}")
        if self.visual_reference:
            lines.append(f"visual_reference: {self.visual_reference}")
        if self.action_reference:
            lines.append(f"action_reference: {self.action_reference}")
        return "\n".join(lines)

    @classmethod
    def from_mapping(cls, data: Dict) -> "StyleConfig":
        config = cls()
        config.story_type = data.get("story_type", "")
        config.genre = data.get("genre", "")
        config.writing_style = data.get("writing_style", "")
        config.visual_style = data.get("visual_style", "")
        config.art_style = data.get("art_style", "")
        config.screen_aspect = data.get("screen_aspect", "")
        config.script_style = data.get("script_style", "")
        config.script_format = data.get("script_format", "")
        config.duration_mode = data.get("duration_mode", "")
        config.episode_count = data.get("episode_count", "")
        config.episode_duration = data.get("episode_duration", "")
        config.mood = data.get("mood", "")
        config.custom_requirements = data.get("custom_requirements", "")
        config.visual_reference = data.get("visual_reference", "")
        config.action_reference = data.get("action_reference", "")
        return config

    def resolve_art_style(self) -> str:
        if self.art_style != "7":
            return self.art_style
        rules = {
            ("科幻",): "3",
            ("奇幻",): "3",
            ("悬疑",): "1",
            ("剧情",): "1",
            ("动作",): "1",
            ("日韩生活",): "2",
            ("治愈",): "2",
            ("日常",): "2",
            ("古装",): "5",
            ("仙侠",): "5",
            ("国风",): "5",
            ("爱情",): "1",
            ("喜剧",): "4",
        }
        keywords = [k.strip() for k in self.genre.replace("，", ",").split(",") if k.strip()]
        for rule_tags, style_id in rules.items():
            for kw in keywords:
                if kw in rule_tags:
                    return style_id
        return "1"

    def resolve_render_style_name(self) -> str:
        resolved = self.resolve_art_style()
        return RENDER_STYLES.get(resolved, {}).get("name", "写实/真人")
