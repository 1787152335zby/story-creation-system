import re
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, STORY_TYPES, VIDEO_PLATFORMS
from core.workflow_loader import WorkflowLoader
from core.cli import console, notify_complete, wait_for_approval, show_progress, select_option, select_version
from core.back_to_menu import BackToMenu
from rich.prompt import Prompt


def _split_sort_key(filename: str) -> int:
    import re
    nums = re.findall(r'[一二三四五六七八九十\d]+', filename)
    if nums:
        raw = nums[0]
        if raw.isdigit():
            return int(raw)
        total = 0
        _CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        for ch in raw:
            total = total * 10 + _CN.get(ch, 0)
        return total if total > 0 else 99
    return 0


class Orchestrator(AgentBase):
    def run(self, project: ProjectManager, style: StyleConfig, start_phase_idx: int = 0):
        console.print(f"\n[bold cyan]🧠 总指挥官启动[/bold cyan]")
        story_type_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")
        console.print(f"项目: {project.name} | 类型: {story_type_name}")

        phases = WorkflowLoader.load()
        total = len(phases)

        for idx, phase in enumerate(phases):
            try:
                if idx < start_phase_idx:
                    continue

                if not phase.should_run(style.story_type):
                    console.print(f"[dim]⏭️ 跳过 [{phase.name}]（当前故事类型不适用）[/dim]")
                    continue

                show_progress(f"阶段{idx+1}/{total}：{phase.name}", idx / total)

                extra_kwargs = {}
                if phase.agent == "prompt_engineer":
                    platform_id = select_option(
                        "🎯 请选择AI视频生成平台：",
                        [(k, f"{v['name']} - {v['desc']}") for k, v in VIDEO_PLATFORMS.items()]
                    )
                    selected_platform = VIDEO_PLATFORMS[platform_id]["name"]
                    console.print(f"[green]选定平台：{selected_platform}[/green]")
                    extra_kwargs["platform"] = selected_platform

                if phase.agent == "outline_designer":
                    self._run_agent_phase(
                        project, style, "outline_designer",
                        phase, idx, input_source=None,
                        extra_kwargs=extra_kwargs
                    )
                elif phase.agent == "plot_expander":
                    self._run_agent_phase(
                        project, style, "plot_expander",
                        phase, idx, input_source="01_故事大纲/故事大纲.md",
                        extra_kwargs=extra_kwargs
                    )
                    # ---- 内容量校验 ----
                    plot_content = project.read_output("02_完整剧情/完整剧情.md") or ""
                    if plot_content:
                        total_chars = len(plot_content.replace(" ", "").replace("\n", ""))
                        scene_count = len(re.findall(r'### 第\d+场', plot_content))
                        console.print(f"\n[dim]📊 剧情统计：{total_chars}字 / {scene_count}场[/dim]")
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
                            if char_ratio > 1.3:
                                console.print(f"[yellow]⚠️ 字数超限 {int((char_ratio-1)*100)}%（目标{target_chars}字，实际{total_chars}字）[/yellow]")
                                should_trim = Prompt.ask("[yellow]是否让AI精简内容？(y/n)[/yellow]", default="n")
                                if should_trim.lower() == 'y':
                                    trim_prompt = (
                                        f"以下是一段剧情，请将其精简到约{target_chars}字，"
                                        f"保留所有核心事件和关键对白，裁剪修饰性描写：\n\n{plot_content}"
                                    )
                                    trimmed = ""
                                    from agents.plot_expander import PlotExpander
                                    trim_agent = PlotExpander(self.llm)
                                    for token in trim_agent.call_llm_stream(trim_prompt, "", temperature=0.4):
                                        trimmed += token
                                    if trimmed:
                                        project.write_output("02_完整剧情/完整剧情.md", trimmed)
                                        console.print("[green]✅ 已精简完成[/green]")
                            elif char_ratio < 0.7:
                                console.print(f"[yellow]⚠️ 字数不足（仅为标准的{int(char_ratio*100)}%），建议调整时长设定[/yellow]")
                    # ---- 承诺清单 + 质量自检 ----
                    if plot_content:
                        from agents.plot_expander import PlotExpander as Expander
                        expander = Expander(self.llm)
                        outline_content = project.read_output("01_故事大纲/故事大纲.md") or ""
                        promise_list = expander._extract_promise_list(outline_content)
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
                        plot_with_audit = plot_content + "\n\n---\n\n" + quality_report
                        project.write_output("02_完整剧情/完整剧情.md", plot_with_audit)
                        console.print("[green]✅ 质量自检 + 承诺清单检查已追加[/green]")
                elif phase.agent == "screenplay_writer":
                    self._run_agent_phase(
                        project, style, "screenplay_writer",
                        phase, idx, input_source="02_完整剧情/完整剧情.md",
                        extra_kwargs=extra_kwargs
                    )
                elif phase.agent == "storyboarder":
                    skwargs = dict(extra_kwargs) if extra_kwargs else {}
                    # Load visual bible variant references and pass to storyboarder
                    from core.visual_bible import VisualBibleExtractor
                    chars = VisualBibleExtractor.list_characters(project)
                    scenes_list = VisualBibleExtractor.list_scenes(project)
                    skwargs["visual_chars"] = chars
                    skwargs["visual_scenes"] = scenes_list
                    self._run_agent_phase(
                        project, style, "storyboarder",
                        phase, idx, input_source="03_完整剧本/完整剧本.md",
                        extra_kwargs=skwargs
                    )
                elif phase.agent == "prompt_engineer":
                    self._run_agent_phase(
                        project, style, "prompt_engineer",
                        phase, idx, input_source="04_分镜脚本/分镜脚本.md",
                        extra_kwargs=extra_kwargs
                    )
                elif phase.agent == "video_producer":
                    console.print("[yellow]⏳ 视频生成模块即将到来，敬请期待！[/yellow]")

                project.mark_phase_done(idx)
            except BackToMenu:
                console.print("[dim]已保存当前进度，返回主菜单[/dim]")
                return

        console.print("\n[bold green]🎉 所有阶段已完成！[/bold green]")

    def _snake_to_pascal(self, name: str) -> str:
        return "".join(word.capitalize() for word in name.split("_"))

    def _get_output_path(self, phase) -> str:
        output = phase.output
        if output.endswith("/"):
            filename_map = {
                "01_故事大纲/": "故事大纲.md",
                "02_完整剧情/": "完整剧情.md",
                "03_完整剧本/": "完整剧本.md",
                "04_角色场景/": "角色场景.md",
                "05_分镜脚本/": "分镜脚本.md",
                "06_提示词/": "提示词.md",
            }
            return output + filename_map.get(output, "产出.md")
        return output

    def _cleanse_outline_version(self, project: ProjectManager, version: str):
        path = "01_故事大纲/故事大纲.md"
        content = project.read_output(path)
        if not content:
            return

        import re
        # 提取版本差异摘要
        diff_summary = ""
        try:
            # 分别提取版本A和B的文本
            a_match = re.search(r'(?<=版本A)[\s\S]*?(?=版本B|\Z)', content)
            b_match = re.search(r'(?<=版本B)[\s\S]*?(?=\Z)', content)
            if a_match and b_match:
                a_text = a_match.group()[:500].strip()
                b_text = b_match.group()[:500].strip()
                if a_text and b_text:
                    diff_prompt = (
                        f"以下是一个故事大纲的两个版本。请用一句话总结版本{version}的核心特征（区别于另一版本的关键差异）。\n\n"
                        f"版本A：{a_text}\n\n版本B：{b_text}"
                    )
                    diff_text = ""
                    try:
                        for token in self.call_llm_stream(diff_prompt, "", temperature=0.3):
                            diff_text += token
                    except:
                        pass
                    diff_summary = diff_text.strip()[:200] if diff_text.strip() else "（未设置）"
                else:
                    diff_summary = "（未设置）"
            else:
                diff_summary = "（未设置）"
        except:
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

    def _run_agent_phase(
        self,
        project: ProjectManager,
        style: StyleConfig,
        agent_name: str,
        phase,
        phase_index: int,
        input_source: str = None,
        extra_kwargs: dict = None,
    ):
        import importlib
        module = importlib.import_module(f"agents.{agent_name}")
        class_name = self._snake_to_pascal(agent_name)
        agent_class = getattr(module, class_name)
        agent = agent_class(self.llm)

        input_content = ""
        if input_source:
            dir_path = project.project_dir / PPath(input_source).parent
            split_files = sorted(dir_path.glob("*_[0-9][0-9]_*.md"), key=lambda f: _split_sort_key(f.name))
            if split_files:
                parts = []
                for sf in split_files:
                    c = project.read_output(str(sf.relative_to(project.project_dir)))
                    if c:
                        parts.append(c)
                input_content = "\n\n---\n\n".join(parts) if parts else ""
                if input_content:
                    console.print(f"  [dim]自动合并 {len(split_files)} 个分幕文件作为输入[/dim]")
            else:
                input_content = project.read_output(input_source) or ""

        if not input_content:
            console.print(f"[red]错误：找不到 {input_source}[/red]")
            return

        console.print(f"\n[cyan]{phase.name} 正在创作...[/cyan]")
        kwargs = {"project": project, "style": style, "input_content": input_content}
        if extra_kwargs:
            kwargs.update(extra_kwargs)
        result = agent.run(**kwargs)

        # ---- 方向卡确认（仅限大纲阶段） ----
        direction_card_sentinel = "【方向卡完毕，请确认】"
        if agent_name == "outline_designer" and direction_card_sentinel in result:
            card_end = result.find(direction_card_sentinel)
            direction_card = result[:card_end].strip()
            console.print("\n[bold cyan]📋 故事方向卡已生成，请确认：[/bold cyan]")
            console.print(direction_card)
            proceed = Prompt.ask("\n[bold yellow]确认方向？输入 'y' 继续到大纲，或 'n' 重新生成[/bold yellow]", default="y")
            if proceed.lower() != 'y':
                new_result = agent.run(**kwargs)
                result = new_result
            else:
                direction_kwargs = dict(kwargs)
                direction_kwargs["input_content"] = direction_card
                second_result = agent.run(**direction_kwargs)
                result = direction_card + "\n\n---\n\n" + second_result
            console.print(f"\n[cyan]{phase.name} 正在生成完整大纲...[/cyan]")

        output_path = self._get_output_path(phase)

        if phase.split:
            path = project.write_output(output_path, result)
            from tools.content_splitter import split_by_headings, make_split_filename
            split_parts = split_by_headings(result)
            saved_files = []
            for title, section in split_parts:
                if not section.strip():
                    continue
                if not title:
                    fname_clean = str(output_path).replace(str(project.project_dir) + "\\", "").replace(str(project.project_dir) + "/", "")
                    split_path = project.write_output(fname_clean, section)
                    saved_files.append(str(split_path))
                else:
                    fname = make_split_filename(str(output_path), title)
                    fname_clean = fname.replace(str(project.project_dir) + "\\", "").replace(str(project.project_dir) + "/", "")
                    split_path = project.write_output(fname_clean, section)
                    saved_files.append(str(split_path))
            console.print(f"  [dim]已拆分为 {len(saved_files)} 个文件[/dim]")
            for f in saved_files:
                console.print(f"    📄 {f}")
            path = project.project_dir / PPath(output_path).parent
        else:
            path = project.write_output(output_path, result)

        notify_complete(phase.name, str(path))

        if agent_name == "outline_designer":
            version_choice = select_version()
            if version_choice in ("1", "2"):
                version_letter = "A" if version_choice == "1" else "B"
                self._cleanse_outline_version(project, version_letter)
                console.print(f"[green]✅ 已选择版本{version_letter}，继续后续流程[/green]")
                phase.auto_skip = True
            elif version_choice == "3":
                feedback_text = Prompt.ask("[yellow]请说明你想如何混合版本A和B[/yellow]").strip()
                feedback_kwargs = dict(kwargs)
                feedback_kwargs["input_content"] = input_content + f"\n\n## 修改意见\n请混合版本A和版本B：{feedback_text}"
                result = agent.run(**feedback_kwargs)
                path = project.write_output(output_path, result)
                notify_complete(f"{phase.name}（已混合）", str(path))

        if not phase.auto_skip:
            approved, feedback = wait_for_approval()
            iterations = 0
            while not approved and iterations < 5:
                if feedback:
                    feedback_kwargs = dict(kwargs)
                    feedback_kwargs["input_content"] = input_content + "\n\n## 修改意见\n" + feedback
                    result = agent.run(**feedback_kwargs)
                    path = project.write_output(output_path, result)
                    notify_complete(f"{phase.name}（已修改）", str(path))
                    approved, feedback = wait_for_approval()
                    iterations += 1
                else:
                    approved = True
