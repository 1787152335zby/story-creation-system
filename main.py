#!/usr/bin/env python3
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pkg"))

from dotenv import load_dotenv

load_dotenv()

from core.cli import console, print_banner, show_menu, notify_complete, wait_for_approval
from core.project_manager import ProjectManager, get_projects_list
from core.style_config import STORY_TYPES, GENRE_TAGS, MOOD_TAGS, WRITING_STYLES, VISUAL_STYLES, RENDER_STYLES, SCREEN_ASPECTS, SCRIPT_STYLES, DURATION_OPTIONS, SCRIPT_FORMATS, StyleConfig
from core.cli import select_option, show_progress
from core.back_to_menu import BackToMenu
from agents.orchestrator import Orchestrator
from rich.prompt import Prompt


def cmd_start():
    console.print("\n[bold]开始新的创作旅程！[/bold]\n")

    story_type_id = select_option(
        "📋 请选择故事类型：",
        [(k, f"{v['name']} - {v['desc']}") for k, v in STORY_TYPES.items()]
    )

    genre_choices = [(str(i+1), g) for i, g in enumerate(GENRE_TAGS)]
    genre_ids = select_option(
        "🎨 请选择题材风格（可多选，用逗号分隔编号，如 1,3,5）：",
        genre_choices,
        allow_custom=True
    )
    selected_genres = []
    for part in genre_ids.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(GENRE_TAGS):
            selected_genres.append(GENRE_TAGS[int(part)-1])
        elif part:
            selected_genres.append(part)
    genre_value = "、".join(selected_genres) if selected_genres else "未指定"

    writing_id = select_option(
        "📖 请选择文笔风格：",
        [(k, f"{v['name']} - {v['desc']}") for k, v in WRITING_STYLES.items()],
        allow_custom=True
    )

    visual_id = select_option(
        "🎬 请选择视觉/叙事风格：",
        [(k, f"{v['name']} - {v['desc']}") for k, v in VISUAL_STYLES.items()],
        allow_custom=True
    )

    art_id = select_option(
        "🎨 请选择渲染画风：",
        [(k, f"{v['name']} - {v['desc']}") for k, v in RENDER_STYLES.items()],
        allow_custom=True
    )

    script_id = select_option(
        "🎭 请选择剧本写作风格：",
        [(k, f"{v['name']} - {v['desc']}") for k, v in SCRIPT_STYLES.items()],
        allow_custom=True
    )

    script_format_id = select_option(
        "📄 请选择剧本格式：",
        [(k, f"{v['name']} - {v['desc']}") for k, v in SCRIPT_FORMATS.items()]
    )

    screen_id = select_option(
        "📏 请选择画面比例：",
        [(k, f"{v['name']} - {v['desc']}") for k, v in SCREEN_ASPECTS.items()],
        allow_custom=True
    )

    duration_id = select_option(
        "⏱️ 请选择时长设置：",
        [(k, f"{v['name']} - {v['desc']}") for k, v in DURATION_OPTIONS.items()]
    )

    episode_count = ""
    episode_duration = ""
    if duration_id == "2":
        story_type_name = STORY_TYPES[story_type_id]["name"]
        if story_type_name in ["短剧", "电视剧"]:
            episode_count = input("\n[bold yellow]总集数：[/bold yellow]").strip()
            episode_duration = input("[bold yellow]单集时长（如 2分钟、45分钟）：[/bold yellow]").strip()
        elif story_type_name in ["电影", "舞台剧/话剧"]:
            episode_duration = input("\n[bold yellow]总时长（如 120分钟）：[/bold yellow]").strip()
        elif story_type_name == "小说/网文":
            episode_count = input("\n[bold yellow]总章节数：[/bold yellow]").strip()
            console.print("[dim]（每章字数将由Agent根据文笔风格自动把握）[/dim]")

    console.print("\n[bold yellow]🎬 是否有视觉/画风参考作品？（如电影色调、动画画风，没有则输入 /skip）[/bold yellow]")
    visual_ref = input().strip()
    if visual_ref.lower() in ("", "/skip", "/s"):
        visual_ref = ""

    console.print("\n[bold yellow]⚔️ 是否有动作/打斗参考作品？（如特定电影的动作设计风格，没有则输入 /skip）[/bold yellow]")
    action_ref = input().strip()
    if action_ref.lower() in ("", "/skip", "/s"):
        action_ref = ""

    mood_choices = [(str(i+1), g) for i, g in enumerate(MOOD_TAGS)]
    mood_ids = select_option(
        "🎭 请选择情绪氛围（可多选，用逗号分隔编号，如 1,3,5）：",
        mood_choices,
        allow_custom=True
    )
    selected_moods = []
    for part in mood_ids.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(MOOD_TAGS):
            selected_moods.append(MOOD_TAGS[int(part)-1])
        elif part:
            selected_moods.append(part)
    mood_value = "、".join(selected_moods) if selected_moods else ""

    console.print("\n[bold yellow]📝 请描述你想讲的故事（一句话或一段话）：[/bold yellow]")
    story_idea = input().strip()

    console.print("\n[bold yellow]📋 还有其他要求吗？（如参考作品、情绪基调、篇幅等，没有则输入 /skip）[/bold yellow]")
    extra_req = input().strip()

    style = StyleConfig()
    style.story_type = story_type_id
    style.genre = genre_value
    style.writing_style = writing_id
    style.visual_style = visual_id
    style.art_style = art_id
    style.screen_aspect = screen_id
    style.script_style = script_id
    style.script_format = script_format_id
    style.duration_mode = "自动" if duration_id == "1" else "自定义"
    style.episode_count = episode_count
    style.episode_duration = episode_duration
    style.mood = mood_value
    style.custom_requirements = extra_req if extra_req != "/skip" else ""
    style.visual_reference = visual_ref
    style.action_reference = action_ref

    project_name = input("\n[bold yellow]给这个项目起个名字：[/bold yellow]").strip()
    if not project_name:
        project_name = "untitled"
    project = ProjectManager(project_name)

    duration_line = "自动（由Agent推荐）" if duration_id == "1" else ""
    if duration_id == "2":
        if episode_count and episode_duration:
            duration_line = f"{episode_count}集 × {episode_duration}/集"
        elif episode_duration:
            duration_line = episode_duration
        elif episode_count:
            duration_line = f"{episode_count}章节"

    task_content = f"""# 创作任务

## 故事类型
{STORY_TYPES[story_type_id]['name']}

## 题材风格
{style.genre}

## 文笔风格
{WRITING_STYLES[writing_id]['name']}

## 视觉/叙事风格
{VISUAL_STYLES[visual_id]['name']}

## 渲染画风
{RENDER_STYLES[art_id]['name']}

{f"## 视觉参考\n{visual_ref}\n" if visual_ref else ""}{f"## 动作参考\n{action_ref}\n" if action_ref else ""}## 剧本写作风格
{SCRIPT_STYLES[script_id]['name']}

## 剧本格式
{SCRIPT_FORMATS[script_format_id]['name']}

## 画面比例
{SCREEN_ASPECTS[screen_id]['name']}

## 时长
{duration_line}

## 故事描述
{story_idea}

## 额外要求
{style.custom_requirements if style.custom_requirements else "无"}
"""
    project.write_output("00_任务指令/任务指令.md", task_content)
    project.config["style_type"] = story_type_id
    project.config["genre"] = style.genre
    project.config["writing_style"] = writing_id
    project.config["visual_style"] = visual_id
    project.config["art_style"] = art_id
    project.config["screen_aspect"] = screen_id
    project.config["script_style"] = script_id
    project.config["script_format"] = script_format_id
    project.config["visual_reference"] = visual_ref
    project.config["action_reference"] = action_ref
    project.save_config()

    console.print(f"\n[bold green]✅ 项目「{project_name}」已创建！[/bold green]")

    try:
        orchestrator = Orchestrator()
        orchestrator.run(project, style)
    except BackToMenu:
        console.print("[dim]已返回主菜单[/dim]")


def cmd_list():
    projects = get_projects_list()
    if not projects:
        console.print("[yellow]暂无项目[/yellow]")
        return

    console.print("\n[bold]已有项目：[/bold]")
    for i, p in enumerate(projects, 1):
        phases_done = sum(1 for ph in p["phases"] if ph["done"])
        total_phases = len(p["phases"])
        console.print(f"  {i}. {p['name']} - [{phases_done}/{total_phases}] {p['status']}")
        console.print(f"     创建时间: {p['created_at']}")


def cmd_continue():
    projects = get_projects_list()
    if not projects:
        console.print("[yellow]暂无已有项目，请输入 /start 开始新项目[/yellow]")
        return

    console.print("\n[bold]已有项目：[/bold]")
    phase_names = ["故事大纲", "完整剧情", "完整剧本", "分镜脚本", "提示词", "视频"]
    for i, p in enumerate(projects, 1):
        progress_str = " → ".join(
            f"[green]✅ {phase_names[j]}[/green]" if j < len(p["phases"]) and p["phases"][j]["done"]
            else f"[dim]⏳ {phase_names[j]}[/dim]" if j < len(p["phases"])
            else f"[dim]⏳ {phase_names[j]}[/dim]"
            for j in range(len(phase_names))
        )
        console.print(f"  {i}. [bold]{p['name']}[/bold]")
        console.print(f"     {progress_str}")

    choice = Prompt.ask("\n[yellow]请选择项目编号，或输入 /back 返回[/yellow]").strip()
    if choice.lower() == "/back":
        return
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(projects):
        console.print(f"[red]无效选择，请输入 1-{len(projects)}[/red]")
        return cmd_continue()

    selected = projects[int(choice) - 1]
    project = ProjectManager(selected["name"])

    phases_done = [ph["done"] for ph in selected["phases"]]
    next_phase_idx = next((i for i, done in enumerate(phases_done) if not done), len(phases_done))

    console.print(f"\n[bold]项目「{selected['name']}」当前进度：[/bold]")
    for i, name in enumerate(phase_names):
        if i < len(phases_done):
            status = "[green]✅ 已完成[/green]" if phases_done[i] else "[dim]⏳ 待处理[/dim]"
            console.print(f"  {i+1}. {name}: {status}")

    start_options = [(str(i+1), f"从 {phase_names[i]} 开始" if i >= len(phases_done) or not phases_done[i] else f"{phase_names[i]} [dim]（已完成）[/dim]") for i in range(len(phase_names))]
    start_options.insert(0, ("0", f"自动从第一个未完成的阶段开始（{phase_names[next_phase_idx]}）"))
    start_choice = select_option("\n📋 选择从哪个阶段开始执行", start_options)

    if start_choice == "0":
        start_idx = next_phase_idx
    else:
        start_idx = int(start_choice) - 1

    if start_idx >= len(phase_names):
        console.print("[green]所有阶段已完成！[/green]")
        return

    console.print(f"[cyan]将从「{phase_names[start_idx]}」阶段开始执行[/cyan]")

    style = StyleConfig()
    style.story_type = selected.get("style_type", "1")
    style.genre = selected.get("genre", "")
    style.writing_style = selected.get("writing_style", "5")
    style.visual_style = selected.get("visual_style", "2")
    style.art_style = selected.get("art_style", "7")
    style.visual_reference = selected.get("visual_reference", "")
    style.action_reference = selected.get("action_reference", "")
    style.screen_aspect = selected.get("screen_aspect", "1")
    style.script_style = selected.get("script_style", "1")

    orchestrator = Orchestrator()
    try:
        orchestrator.run(project, style, start_phase_idx=start_idx)
    except BackToMenu:
        console.print("[dim]已返回主菜单[/dim]")


def cmd_help():
    help_text = """
[bold]可用命令：[/bold]
  /start    开始新的创作
  /list     查看已有项目
  /continue 继续/跳过到指定阶段
  /help     显示本帮助
  /exit     退出系统

[bold]创作流程：[/bold]
  1. 选择故事类型 → 2. 选择风格 → 3. 描述创意
  4. 大纲设计师生成大纲 → 5. 你审核选版本
  6. 剧情叙述师写出完整剧情 → 7. 你审核
  8. 剧本创作师写成完整剧本 → 9. 你审核
  10. 分镜师设计分镜 → 11. 你审核
  12. 提示词工程师写提示词 → 13. 你审核
  14. 视频生成（可选）

[bold]小技巧：[/bold]
  - 已有故事大纲？用 /continue 选项目后直接跳到"完整剧情"或"完整剧本"阶段
  - 选版本A后，版本B会自动被清理，文件只保留选中版本
    """
    console.print(help_text)


def main():
    print_banner()

    if not os.getenv("OPENAI_API_KEY") and not os.getenv("CLAUDE_API_KEY"):
        console.print("[red]⚠️ 未检测到 API Key！[/red]")
        console.print("请复制 [cyan].env.example[/cyan] 为 [cyan].env[/cyan]，填入你的 API Key 后重试")
        return

    while True:
        cmd = show_menu()

        cmd_map = {
            "1": "/start",
            "2": "/list",
            "3": "/continue",
            "4": "/help",
            "5": "/exit",
        }
        cmd = cmd_map.get(cmd, cmd)

        if cmd == "/start":
            try:
                cmd_start()
            except BackToMenu:
                console.print("[dim]已返回主菜单[/dim]")
        elif cmd == "/list":
            cmd_list()
        elif cmd == "/continue":
            try:
                cmd_continue()
            except BackToMenu:
                console.print("[dim]已返回主菜单[/dim]")
        elif cmd == "/help":
            cmd_help()
        elif cmd == "/exit":
            console.print("[cyan]再见！[/cyan]")
            break
        else:
            console.print("[red]未知命令，输入 4 或 /help 查看帮助[/red]")


if __name__ == "__main__":
    main()
