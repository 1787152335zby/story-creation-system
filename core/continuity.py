"""ContinuityLog — 跨集状态追踪器
在每集剧情/剧本生成后提取关键状态，供下一集注入前情提要。
"""
import json
import re
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def extract_continuity(episode_text: str, prev_log: dict | None = None) -> dict:
    """从本集文本中提取连续性状态。

    返回：
    {
        "positions": {"角色名": "位置描述"},
        "props": {"角色名": ["道具1", "道具2"]},
        "relationships": {"角色A-角色B": "关系状态"},
        "unresolved": ["未解决的冲突1", "未解决的冲突2"],
        "key_events": ["本集关键事件1", "关键事件2"]
    }
    """
    result = {
        "positions": {},
        "props": {},
        "relationships": {},
        "unresolved": [],
        "key_events": []
    }

    for m in re.finditer(r'(\S{1,4})(?:站|坐|靠|躺|蹲|走)在(\S{1,15})', episode_text):
        name = m.group(1)
        loc = m.group(2)
        if name not in result["positions"]:
            result["positions"][name] = loc

    for m in re.finditer(r'(\S{1,4})(?:手持|拿起|握住|掏出|拔出|收起|丢下|放下|递给|接过)(\S{1,10})', episode_text):
        name = m.group(1)
        prop = m.group(2)
        if name not in result["props"]:
            result["props"][name] = []
        if prop not in result["props"][name]:
            result["props"][name].append(prop)

    return result


def generate_continuity_injection(current_log: dict, prev_log: dict | None = None) -> str:
    """生成注入到下一集 prompt 的前情提要文本"""
    parts = []
    if current_log.get("positions"):
        parts.append("人物位置：")
        for name, loc in current_log["positions"].items():
            parts.append(f"  - {name} 在{loc}")
    if current_log.get("props"):
        parts.append("持有物品：")
        for name, props in current_log["props"].items():
            parts.append(f"  - {name} 持有 {'、'.join(props)}")
    if current_log.get("key_events"):
        parts.append("本集关键事件：")
        for ev in current_log["key_events"][:5]:
            parts.append(f"  - {ev}")
    return "\n".join(parts)


def save_continuity(project_dir: Path, episode_name: str, log: dict):
    """保存连续性日志"""
    log_dir = project_dir / "_continuity"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{episode_name}.json"
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"ContinuityLog 已保存: {log_path}")


def load_continuity(project_dir: Path, episode_name: str) -> dict | None:
    """加载连续性日志"""
    log_path = project_dir / "_continuity" / f"{episode_name}.json"
    if log_path.exists():
        return json.loads(log_path.read_text(encoding="utf-8"))
    return None


def load_last_continuity(project_dir: Path) -> dict | None:
    """加载最近一次的连续性日志"""
    log_dir = project_dir / "_continuity"
    if not log_dir.exists():
        return None
    files = sorted(log_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files:
        return json.loads(f.read_text(encoding="utf-8"))
    return None
