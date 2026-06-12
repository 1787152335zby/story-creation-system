"""Quality Checker — AI 驱动的质量审查
替换内联的"犯人批卷子"，用独立 LLM 调用（低 temperature）对照大纲审查生成内容。
"""
import re
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CHECK_PROMPT = """你是一个严苛的故事质量审查员。对照原始大纲，检查生成内容是否兑现了所有承诺。

## 原始大纲
{outline}

## 生成内容（最近 8000 字）
{content}

## 检查清单
逐项检查以下维度，每项输出"通过 / 违反"，违反项附具体证据和修改建议。

1. 承诺角色：大纲中提到的每个主要角色是否都出场了？缺少谁？
2. 承诺事件：大纲中的每个关键事件是否都发生了？遗漏了什么？
3. 核心冲突：核心冲突是否持续贯穿？是否有被弱化或遗忘？
4. 高潮比例：最后 20% 内容是否有足够分量？是否"前重后轻"？
5. 反派/对手重量：反派或对手是否有足够篇幅和对抗张力？
6. 配角人格：每个出场配角是否至少有一次有"人味儿"的非工具人瞬间？
7. 反转铺垫：如果有反转，前面是否有可回溯的伏笔？

## 输出格式
只输出一个 JSON 对象：
{{
  "passed": true,
  "checks": [
    {{"item": "承诺角色", "result": "通过", "evidence": ""}},
    {{"item": "承诺事件", "result": "违反", "evidence": "遗漏了XX事件", "suggestion": "建议在第X场补充"}}
  ],
  "overall_feedback": "一句话总评"
}}

如果全部通过，passed 为 true。只输出 JSON，不要解释。"""


def run_ai_quality_check(llm_client, outline_text: str, generated_content: str, phase_name: str = "") -> dict | None:
    """用独立 LLM 调用做质量审查

    Args:
        llm_client: LLMClient 实例
        outline_text: 原始大纲文本（取前 4000 字）
        generated_content: 生成的内容（取最近 8000 字）
        phase_name: 阶段名称，用于日志

    Returns:
        审查结果 dict，失败返回 None
    """
    try:
        outline_snippet = outline_text[:4000]
        content_snippet = generated_content[-8000:]

        prompt = _CHECK_PROMPT.format(
            outline=outline_snippet,
            content=content_snippet,
        )

        result_text = ""
        for chunk in llm_client.backend.chat_stream(prompt, "", temperature=0.1):
            result_text += chunk

        json_start = result_text.find("{")
        json_end = result_text.rfind("}") + 1
        if json_start < 0 or json_end <= json_start:
            logger.warning(f"QC [{phase_name}]: LLM 未返回有效 JSON")
            return None

        result = json.loads(result_text[json_start:json_end])
        if not isinstance(result, dict):
            return None

        violations = [c for c in result.get("checks", []) if c.get("result") == "违反"]
        if violations:
            logger.warning(f"QC [{phase_name}]: {len(violations)} 项违反")
            for v in violations:
                logger.warning(f"  - {v.get('item')}: {v.get('evidence', '')[:80]}")

        return result

    except Exception as e:
        logger.warning(f"QC [{phase_name}]: 审查异常: {e}")
        return None


def extract_promise_list(outline_text: str) -> str:
    """从大纲中提取承诺清单"""
    match = re.search(r'【本故事承诺】.*?(?=\n\n|\Z)', outline_text, re.DOTALL)
    if match:
        return match.group(0).strip()
    return ""


def qc_result_to_warnings(result: dict | None) -> list[str]:
    """将 QC 结果转为前端可显示的警告列表"""
    if not result:
        return ["AI 质量审查未完成，建议人工审核"]
    warnings = []
    if not result.get("passed"):
        for c in result.get("checks", []):
            if c.get("result") == "违反":
                evidence = c.get("evidence", "")
                suggestion = c.get("suggestion", "")
                msg = f"[{c.get('item', '未知')}] {evidence}"
                if suggestion:
                    msg += f" → {suggestion}"
                warnings.append(msg)
        if result.get("overall_feedback"):
            warnings.append(f"总评: {result['overall_feedback']}")
    return warnings
