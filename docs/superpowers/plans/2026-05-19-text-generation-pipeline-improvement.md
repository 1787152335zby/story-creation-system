# 文本生成管线优化 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化故事创作前两个阶段（故事大纲 + 完整剧情），解决版本选择丢失、质量无检查、分块切割粗糙、内容量失控等问题

**Architecture:** 不改整体架构，只增强提示词策略 + 增加后处理校验。阶段一改为两轮制（方向卡 → 完整大纲），阶段二增加自检、承诺清单、内容量校验

**Tech Stack:** Python (agents + core modules), Markdown prompt templates

---

### Task 1: 阶段一方向卡 — 修改 outline_designer.txt 提示词

**Files:**
- Modify: `prompts/outline_designer.txt`

- [ ] **Step 1: 在现有 prompt 最前面增加方向卡指令**

在 `prompts/outline_designer.txt` 开头增加指令，使其先输出故事方向卡，然后等待确认后再输出完整大纲。

```markdown
【第一轮：故事方向卡】
你的输出分为两轮。
第一轮输出以下内容（300 字以内），不要输出完整大纲：

```
【一句话梗概】一句话概括这个故事，包含题材和核心设定。
【视角人物】主角是谁，TA 最想要什么。
【核心冲突】阻挡 TA 实现目标的最大障碍是什么。
【情绪基调】故事的整体情绪氛围（冷峻/温暖/悬疑/热血/治愈……）。
【类型对标】类似哪部作品的感觉。
【两个方向】
  方向A：【一句话说明走向】
  方向B：【一句话说明走向（与A的核心差异点）】
```

输出完方向卡后，用以下标记结束：
**【方向卡完毕，请确认】**
```

保留现有的全部内容作为第二轮指令。

- [ ] **Step 2: 将现有内容改为"第二轮"指令**

在方向卡指令后、原有 prompt 内容前，增加：

```markdown

【第二轮：完整大纲】
接收到方向确认信号后，才输出以下完整大纲内容。

```

```

---

### Task 2: 阶段一方向卡 — 修改 orchestrator.py 增加确认步骤

**Files:**
- Modify: `agents/orchestrator.py`

- [ ] **Step 1: 在 outline_designer 阶段的 `_run_agent_phase` 调用后，增加方向卡确认**

找到 `if agent_name == "outline_designer":` 区块（约第 202 行），在其前面增加方向卡确认逻辑：

```python
if agent_name == "outline_designer":
    # 检查输出是否处于"方向卡阶段"
    direction_card_sentinel = "【方向卡完毕，请确认】"
    if direction_card_sentinel in result:
        console.print("\n[bold cyan]📋 故事方向卡已生成，请确认：[/bold cyan]")
        # 提取方向卡内容（只显示方向卡部分）
        card_end = result.find("【方向卡完毕，请确认】")
        direction_card = result[:card_end].strip()
        console.print(direction_card)
        proceed = Prompt.ask("\n[bold yellow]确认方向？输入 'y' 继续到大纲，或 'n' 重新生成方向卡[/bold yellow]", default="y")
        if proceed.lower() != 'y':
            # 重新生成方向卡
            new_result = agent.run(**feedback_kwargs if 'feedback_kwargs' in locals() else kwargs)
            result = new_result
            project.write_output(output_path, result)
            notify_complete(f"{phase.name}（方向卡已更新）", str(path))
        else:
            # 用户确认，移除方向卡标记，保留后续完整大纲
            # AI 需要在第二轮输出完整大纲
            # 简单做法：重新 call agent，传入已确认的信号
            direction_kwargs = dict(kwargs)
            direction_kwargs["input_content"] = direction_card  # 把方向卡作为输入传给第二轮
            second_result = agent.run(**direction_kwargs)
            # 合并方向卡 + 完整大纲
            combined = direction_card + "\n\n---\n\n" + second_result
            project.write_output(output_path, combined)
            result = combined
    # 继续现有的版本选择逻辑
    version_choice = select_version()
    ...
```

- [ ] **Step 2: 在 `_cleanse_outline_version` 中增加版本差异总结**

```python
def _cleanse_outline_version(self, project: ProjectManager, version: str):
    path = "01_故事大纲/故事大纲.md"
    content = project.read_output(path)
    if not content:
        return

    import re
    # 提取版本A和B的差异
    version_a_match = re.search(r'(?<=版本A).*?(?=版本B|\Z)', content, re.DOTALL)
    version_b_match = re.search(r'(?<=版本B).*?(?=\Z)', content, re.DOTALL)
    diff_summary = ""
    if version_a_match and version_b_match:
        diff_prompt = (
            f"以下是一个故事大纲的两个版本。请用一句话总结版本{version}的核心特征（区别于另一版本的关键差异）。\n\n"
            f"版本A：{version_a_match.group()[:500]}\n\n版本B：{version_b_match.group()[:500]}"
        )
        try:
            diff_text = ""
            for token in self.call_llm_stream(diff_prompt, "", temperature=0.3):
                diff_text += token
            diff_summary = diff_text.strip()[:200]
        except:
            diff_summary = "（未设置）"
    else:
        diff_summary = "（未设置）"

    if version == "A":
        pattern = r"^(#{1,4}\s*\*{0,2}版本B\s*\*{0,2}.*?)(?=^#{1,4}|\Z)"
        cleaned = re.sub(pattern, "", content, flags=re.MULTILINE | re.DOTALL)
        cleaned = cleaned.rstrip() + f"\n\n---\n\n> ✅ 已选中版本A。差异摘要：{diff_summary}"
    elif version == "B":
        pattern = r"^(#{1,4}\s*\*{0,2}版本A\s*\*{0,2}.*?)(?=^#{1,4}|\Z)"
        cleaned = re.sub(pattern, "", content, flags=re.MULTILINE | re.DOTALL)
        cleaned = cleaned.rstrip() + f"\n\n---\n\n> ✅ 已选中版本B。差异摘要：{diff_summary}"
    else:
        return

    project.write_output(path, cleaned)
    console.print(f"[green]大纲文件已清理：仅保留版本{version}，差异摘要已记录[/green]")
```

---

### Task 3: 阶段二承诺清单 — 修改 plot_expander.txt 增加承诺清单指令

**Files:**
- Modify: `prompts/plot_expander.txt`

- [ ] **Step 1: 大纲内容前插入版本方向信息**

在大纲内容 `{outline}` 前增加：

```markdown

【方向确认】
{confirmed_direction}

```

- [ ] **Step 2: 在输出要求中增加承诺清单提取指令**

在"【重要：输出完整性】"前增加：

```markdown
【承诺清单 — 生成前必做】
在生成剧情之前，先分析大纲并输出以下「承诺清单」。承诺清单放在剧情文件的开头。

```
【本故事承诺】
- 必须出场的角色：角色A、角色B、角色C
- 必须发生的关键事件：事件1、事件2
- 必须解决的核心冲突：冲突描述
```

逐项检查承诺清单是否在剧情中全部兑现。如有遗漏，在剧情末尾标注**未兑现项**。
```

- [ ] **Step 3: 在末尾增加质量自检指令**

在结尾前增加：

```markdown

【质量自检 — 生成后必做】
剧情生成完毕后，请逐条对照以下标准进行自检，输出检查报告放在文件末尾：

```
【质量自检】
1. 禁止前重后轻 — 通过/违反（前30%字数 vs 后30%字数比：XX:XX）
2. 禁止过渡跳跃 — 通过/违反（相邻场次间是否有衔接：第X场→第Y场）
3. 配角不是工具人 — 通过/违反（每个配角是否有"人味儿"瞬间）
4. 关键反转需要铺垫 — 通过/违反（反转前是否有伏笔）
5. 最终反派的重量 — 通过/违反（反派出场篇幅是否匹配）
6. 每场一句记忆点 — 通过/违反（第X场缺少记忆点）
```

如有违反项，在自检报告后附上修改建议。
```

---

### Task 4: 阶段二版本方向传递 — 修改 plot_expander.py

**Files:**
- Modify: `agents/plot_expander.py`

- [ ] **Step 1: 从大纲文件中读取版本方向信息**

在 `run_stream` 方法中，读取大纲文件后，提取 `confirmed_direction`：

```python
def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
    template = self.load_prompt_template("plot_expander.txt")

    # 从大纲中提取版本方向信息
    confirmed_direction = ""
    outline_content = project.read_output("01_故事大纲/故事大纲.md") or ""
    direction_match = re.search(r'> ✅ 已选中版本[AB]。(差异摘要.*?)$', outline_content, re.MULTILINE)
    if direction_match:
        confirmed_direction = direction_match.group(1).strip()
    if not confirmed_direction:
        confirmed_direction = "（未设置）"
```

- [ ] **Step 2: 将 `{confirmed_direction}` 替换到 prompt 中**

在所有 `template.replace` 调用的地方，增加：

```python
prompt = prompt.replace("{confirmed_direction}", confirmed_direction)
```

在 `_resolve_auto_chunks` 方法中也同样增加。

- [ ] **Step 3: 增加字数统计和内容量校验**

在方法末尾（生成完成后），增加校验逻辑：

```python
# 字数统计和内容量校验
def _check_content_volume(self, content: str, style: StyleConfig) -> str:
    """检查内容量是否在约束范围内，返回检查报告"""
    total_chars = len(content.replace(" ", "").replace("\n", ""))
    # 统计场次数
    scenes = re.findall(r'### 第\d+场', content)
    scene_count = len(scenes)

    # 从时长推算期望量
    try:
        count = int(style.episode_count) if style.episode_count else 1
        dur = style.episode_duration.replace("分钟", "").replace("分", "").strip()
        per = int(dur) if dur.isdigit() else 0
        total_min = count * per
    except:
        total_min = 0

    # 对照约束表
    limits = [
        (60, 6, 800),
        (180, 12, 2000),
        (600, 20, 4000),
        (1800, 40, 8000),
        (3600, 60, 15000),
        (5400, 80, 20000),
    ]
    target_scenes = scene_count
    target_chars = total_chars
    for limit_min, limit_scenes, limit_chars in limits:
        if total_min <= limit_min:
            target_scenes = limit_scenes
            target_chars = limit_chars
            break

    scene_ratio = scene_count / target_scenes if target_scenes > 0 else 1
    char_ratio = total_chars / target_chars if target_chars > 0 else 1

    report = f"\n\n---\n【内容量校验】目标: 约{target_chars}字/{target_scenes}场 | 实际: {total_chars}字/{scene_count}场\n"
    if char_ratio > 1.3:
        report += f"⚠️ 字数超限 {int((char_ratio-1)*100)}%，建议精简或调整时长设定\n"
    elif char_ratio < 0.7:
        report += f"⚠️ 字数不足（仅为标准的{int(char_ratio*100)}%），建议补充或调整时长设定\n"
    else:
        report += "✅ 内容量在合理范围内\n"

    return report
```

在 `run_stream` 末尾（所有 yield 之后），将检查报告追加到最终内容：

```python
# 在方法结束时
# 由于是 stream 方式，需要收集所有输出后在 orchestrator 层面追加
# 这里不做改动，在 orchestrator 里处理
```

- [ ] **Step 4: 增加承诺清单提取方法**

```python
def _extract_promise_list(self, outline_content: str) -> str:
    """从大纲中提取承诺清单"""
    if not outline_content:
        return "（无大纲内容）"

    prompt = (
        "以下是一个故事大纲。请分析并输出该故事必须包含的角色、关键事件和核心冲突。\n"
        "格式如下，不要额外内容：\n"
        "```\n"
        "【本故事承诺】\n"
        "- 必须出场的角色：XXX、XXX\n"
        "- 必须发生的关键事件：XXX、XXX\n"
        "- 必须解决的核心冲突：XXX\n"
        "```\n\n"
        f"{outline_content[:4000]}"
    )
    result = ""
    for token in self.call_llm_stream(prompt, "", temperature=0.3):
        result += token
    # 提取承诺清单部分
    match = re.search(r'【本故事承诺】.*?(?=\n\n|\Z)', result, re.DOTALL)
    return match.group(0) if match else "（未能提取承诺清单）"
```

---

### Task 5: 阶段二 orchestrator 层校验 — 修改 orchestrator.py

**Files:**
- Modify: `agents/orchestrator.py`

- [ ] **Step 1: 在 plot_expander 阶段完成后追加内容和校验**

找到 plot_expander 的调用分支（`elif phase.agent == "plot_expander":`），在其后面增加：

```python
elif phase.agent == "plot_expander":
    self._run_agent_phase(
        project, style, "plot_expander",
        phase, idx, input_source="01_故事大纲/故事大纲.md",
        extra_kwargs=extra_kwargs
    )
    # ---- 追加内容量校验 ----
    plot_content = project.read_output("02_完整剧情/完整剧情.md") or ""
    if plot_content:
        # 统计
        total_chars = len(plot_content.replace(" ", "").replace("\n", ""))
        scene_count = len(re.findall(r'### 第\d+场', plot_content))
        console.print(f"\n[dim]📊 剧情统计：{total_chars}字 / {scene_count}场[/dim]")

        # 从 style 推算期望量
        try:
            count = int(style.episode_count) if style.episode_count else 1
            dur = style.episode_duration.replace("分钟", "").replace("分", "").strip()
            per = int(dur) if dur.isdigit() else 0
            total_min = count * per
        except:
            total_min = 0

        if total_min > 0:
            limits = [
                (60, 6, 800), (180, 12, 2000), (600, 20, 4000),
                (1800, 40, 8000), (3600, 60, 15000), (5400, 80, 20000),
            ]
            target_scenes = scene_count
            target_chars = total_chars
            for limit_min, limit_scenes, limit_chars in limits:
                if total_min <= limit_min:
                    target_scenes = limit_scenes
                    target_chars = limit_chars
                    break
            char_ratio = total_chars / target_chars if target_chars > 0 else 1
            scene_ratio = scene_count / target_scenes if target_scenes > 0 else 1

            if char_ratio > 1.3:
                console.print(f"[yellow]⚠️ 字数超限 {int((char_ratio-1)*100)}%（目标{target_chars}字，实际{total_chars}字）[/yellow]")
                should_trim = Prompt.ask("[yellow]是否让AI精简内容？(y/n)[/yellow]", default="n")
                if should_trim.lower() == 'y':
                    trim_prompt = (
                        f"以下是一段剧情，请将其精简到约{target_chars}字，"
                        f"保留所有核心事件和关键对白，裁剪修饰性描写：\n\n{plot_content}"
                    )
                    trimmed = ""
                    # 临时用 LLM 精简
                    from agents.plot_expander import PlotExpander
                    trim_agent = PlotExpander(self.llm)
                    for token in trim_agent.call_llm_stream(trim_prompt, "", temperature=0.4):
                        trimmed += token
                    if trimmed:
                        project.write_output("02_完整剧情/完整剧情.md", trimmed)
                        console.print("[green]✅ 已精简完成[/green]")
            elif char_ratio < 0.7:
                console.print(f"[yellow]⚠️ 字数不足（仅为标准的{int(char_ratio*100)}%），建议调整时长设定[/yellow]")

- [ ] **Step 2: 增加承诺清单和自检**

同上一步，在内容量校验之后追加承诺清单和自检：

```python
    # ---- 追加承诺清单 + 质量自检 ----
    if plot_content:
        from agents.plot_expander import PlotExpander
        expander = PlotExpander(self.llm)
        outline_content = project.read_output("01_故事大纲/故事大纲.md") or ""
        promise_list = expander._extract_promise_list(outline_content)

        # 质量自检
        quality_prompt = (
            f"以下是一段剧情。请作为质量审核员逐条检查以下6条标准，输出检查报告：\n\n"
            f"1. 禁止前重后轻（检查前30%和后30%字数比）\n"
            f"2. 禁止过渡跳跃（相邻场次间是否有衔接）\n"
            f"3. 配角不是工具人（每个配角是否有'人味儿'瞬间）\n"
            f"4. 关键反转需要铺垫（反转前是否有伏笔）\n"
            f"5. 最终反派的重量（反派出场篇幅是否充足）\n"
            f"6. 每场一句记忆点（每场是否有金句或记忆点）\n\n"
            f"【承诺清单】对照检查以下承诺是否兑现：\n{promise_list}\n\n"
            f"剧情内容：\n{plot_content[:8000]}"
        )
        quality_report = ""
        for token in expander.call_llm_stream(quality_prompt, "", temperature=0.3):
            quality_report += token

        # 追加到剧情文件末尾
        plot_content_with_audit = plot_content + "\n\n---\n\n" + quality_report
        project.write_output("02_完整剧情/完整剧情.md", plot_content_with_audit)
        console.print("[green]✅ 质量自检 + 承诺清单检查已追加[/green]")
```

需要在文件顶部增加 import：

```python
import re
```

---

### Task 6: 分块预分析 — 修改 chunk_strategy.py

**Files:**
- Modify: `core/chunk_strategy.py`

- [ ] **Step 1: 增加预分析方法**

```python
class ChunkStrategy:
    @staticmethod
    def pre_analyze_split_points(outline: str, llm_stream_callable) -> list:
        """预分析大纲的最佳分割点，返回分割点标签列表"""
        if not outline or len(outline) < 500:
            return None  # 内容太少，不分割

        prompt = (
            "以下是一个故事大纲。请判断它最适合按什么结构分割。\n\n"
            "如果故事有明确的幕/集/章标题，按原结构输出分割点。\n"
            "如果故事没有明确标题，请分析故事情节中的自然断点（重大事件转折、时间跳转、场景切换），推荐分割方案。\n\n"
            "输出格式：每行一个分割点，格式为「分割点N：标签名」。\n"
            "只输出分割点列表，不要解释。\n\n"
            f"{outline[:4000]}"
        )
        result = ""
        for token in llm_stream_callable(prompt, "", temperature=0.3):
            result += token

        split_points = []
        for line in result.strip().split("\n"):
            line = line.strip()
            if "：" in line:
                label = line.split("：", 1)[1].strip()
                split_points.append(label)
            elif ":" in line:
                label = line.split(":", 1)[1].strip()
                split_points.append(label)
        return split_points if len(split_points) >= 2 else None
```

- [ ] **Step 2: 在 ChunkIter 中使用预分析结果**

在 `__init__` 方法中，如果 `plan.chunk_count > 0` 且 `self.blocks` 为空（未找到标题），则尝试使用预分析结果：

```python
class ChunkIter:
    def __init__(self, plan: ChunkPlan, outline: str, pre_analyzed: list = None):
        self.plan = plan
        if plan.chunk_count > 0:
            self.blocks = self._parse_fixed(outline, plan)
            if not self.blocks and pre_analyzed:
                # 使用预分析结果
                per_chunk = len(outline) // len(pre_analyzed)
                plan.chunk_count = len(pre_analyzed)
                plan.chunk_names = pre_analyzed
                self.blocks = []
                for i, name in enumerate(pre_analyzed):
                    start = i * per_chunk
                    end = (i + 1) * per_chunk if i < len(pre_analyzed) - 1 else len(outline)
                    self.blocks.append({"index": i, "name": name, "content": outline[start:end]})
        else:
            self.blocks = []
```

---

### Task 7: 集成测试 — plot_expander 功能验证

**Files:**
- Test: `agents/tests/test_plot_expander.py` (新建)

- [ ] **Step 1: 编写测试**

```python
import pytest
from unittest.mock import MagicMock, patch
from agents.plot_expander import PlotExpander


def test_extract_promise_list():
    """测试从大纲中提取承诺清单"""
    expander = PlotExpander(MagicMock())
    outline = """
    # 测试故事
    
    ## 角色
    - 林深：主角，侦探
    - 天眼：配角，黑客
    
    ## 剧情
    第一幕：林深接到案件
    第二幕：调查发现真相
    第三幕：对决
    """
    # mock LLM call
    expander.call_llm_stream = MagicMock(return_value=iter([
        "【本故事承诺】\n- 必须出场的角色：林深、天眼\n- 必须发生的关键事件：接到案件、发现真相、对决\n- 必须解决的核心冲突：真相 vs 谎言"
    ]))
    result = expander._extract_promise_list(outline)
    assert "林深" in result
    assert "天眼" in result
    assert "必须出场的角色" in result
```

- [ ] **Step 2: 运行测试**

Run: `pytest agents/tests/test_plot_expander.py -v`
Expected: PASS

---

### Task 8: 端到端验证

- [ ] **Step 1: 启动服务**

```bash
python run_web.py
```

- [ ] **Step 2: 新建一个测试项目，选择短剧/电影类型**

通过前端新建项目，触发管线运行。

- [ ] **Step 3: 验证阶段一方向卡**

确认第一轮输出的是方向卡（300 字左右），不是完整大纲。确认选择版本后，文件末尾有差异摘要。

- [ ] **Step 4: 验证阶段二**

确认剧情文件末尾包含：
- 承诺清单
- 质量自检报告
- 内容量校验

- [ ] **Step 5: 如果发现问题**

```bash
# 查看日志
python -c "import server.app"
```

---
