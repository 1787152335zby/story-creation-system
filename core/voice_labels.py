import re

VOICE_SYNONYMS = ["说话方式", "台词风格", "对白特征", "语言特点", "声线特征", "说话风格", "口吻", "对白方式"]


def _match_voice_label(text: str) -> bool:
    return any(syn in text for syn in VOICE_SYNONYMS)


def extract_voice_labels(outline_text: str) -> list[dict]:
    """从大纲文本中提取所有角色的说话方式标签"""
    labels = []
    lines = outline_text.split("\n")
    current_name = ""
    for line in lines:
        stripped = line.strip().lstrip('*').strip()
        m = re.match(r"^\**姓名[：:]\s*\**[：:\s]*(\S+)", stripped)
        if m:
            name = m.group(1).strip('*')
            name = re.sub(r'[（(][^)）]*[)）]$', '', name)
            if name and len(name) >= 2 and all('\u4e00' <= c <= '\u9fff' for c in name):
                current_name = name
        elif _match_voice_label(stripped) and current_name:
            tag = stripped.split("：", 1)[-1].strip() if "：" in stripped else stripped.split(":", 1)[-1].strip()
            tag = tag.lstrip('*').strip()
            if tag and len(tag) >= 2:
                labels.append({"name": current_name, "tag": tag})
            current_name = ""
    return labels


def format_voice_injection(labels: list[dict]) -> str:
    """将声线标签格式化为prompt注入文本"""
    if not labels:
        return ""
    lines = ["\n## 角色声音约束（以下标签来自大纲设定，必须严格遵守）"]
    for entry in labels:
        lines.append(f"- {entry['name']}：{entry['tag']}")
    lines.append("每句对白写完后自查：删掉角色名能不能看出是谁说的。看不出就重写。")
    return "\n".join(lines)


def extract_char_names(outline_text: str) -> list:
    """从大纲提取角色名列表"""
    names = []
    for m in re.finditer(r'\**姓名[：:]\s*\**[：:\s]*(\S+)', outline_text, re.MULTILINE):
        name = m.group(1).strip('*')
        name = re.sub(r'[（(][^)）]*[)）]$', '', name)
        if len(name) >= 2 and len(name) <= 3 and all('\u4e00' <= c <= '\u9fff' for c in name):
            names.append(name)
    return names


def build_hard_constraint_card(outline_text: str) -> str:
    """生成硬约束卡，追加到每批 prompt 的最末尾（LLM 对尾部注意力最高）"""
    labels = extract_voice_labels(outline_text)
    names = extract_char_names(outline_text)

    lines = [
        "\n\n## ⚠️ 硬约束卡——生成前逐条核对（本条优先级高于所有其他规则）",
        "",
    ]

    if names:
        lines.append(f"**主角白名单：** {', '.join(names)}")
        lines.append("**主角——出场角色必须写白名单内的名字，不能写标签（「新娘」「孩子」等）。这些名字是导演选角的依据。**")
        lines.append("**功能配角——可以有名字，但必须是单集出场的工具人（如「便利店老板老张」「值班护士小刘」），不能有完整人物弧线和多集戏份。**")
        lines.append("**无名过场角色——用职业标签（保安、服务员、路人甲），不需要名字。**")
        lines.append("禁止创建白名单外的、有多集戏份的新主角级角色。")

    if labels:
        lines.append("")
        lines.append("**每人说话方式（必须逐句匹配，不得例外）：**")
        for l in labels:
            lines.append(f"- {l['name']}：{l['tag']}")

    lines.append("")
    lines.append("**钩子：** 整集最后一行之前的一行，必须是纯画面动作（括号包裹），不能是对白。")
    lines.append("**自检清单：** 1)有没有自创角色名？2)有没有用标签替代角色名？3)每句对白删掉角色名还能认出是谁说的吗？4)钩子是不是对白收尾？")
    lines.append("")
    lines.append("**结构铁律（违反则全批作废）：**")
    lines.append("- 核心谜题的最终答案只能在最后5集揭晓。前面每集只是累积线索、制造悬念。")
    lines.append("- 禁止在中途说「结束了」「最后一次」「最后一面」——故事还没结束。")
    lines.append("- 每一集结束时，观众必须产生新的疑问，不能是「答案已经有了」的状态。")
    lines.append("- **全剧风格必须从头到尾一致。** 不能写着写着从悬疑变成抽象诗。第1集什么风格，第70集就是什么风格。")
    lines.append("- **禁止循环叙事。** 不能反复写「第N次重复同样的事」。每一集的事件必须不同，情节必须前进。")
    lines.append("- **禁止引入大纲中没有的超自然/超现实设定。** 大纲里没有魔法、没有种子里长镜子、没有透明血。所有道具和事件必须是真实世界里的东西——录像带、铁盒、手机、打火机、血是红色的。禁止把写实悬疑写成奇幻寓言。")

    return "\n".join(lines)
