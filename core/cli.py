from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from typing import List, Tuple
from .back_to_menu import BackToMenu


console = Console()


def print_banner():
    banner = """
╔══════════════════════════════════════════╗
║     🎬 多智能体故事创作系统 v1.0         ║
║                                         ║
║     1) 开始新的创作     2) 查看已有项目  ║
║     3) 继续已有项目     4) 帮助          ║
║     5) 退出系统                         ║
║                                         ║
║     也支持输入 /start, /list 等命令      ║
╚══════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="bold cyan"))


def show_menu() -> str:
    return Prompt.ask("> ").strip().lower()


def select_option(title: str, options: List[Tuple[str, str]], allow_custom: bool = False) -> str:
    console.print(f"\n[bold yellow]{title}[/bold yellow]")
    if "开始新的创作" not in title:
        console.print("  [dim]输入 /menu 返回主菜单[/dim]")
    for opt_id, desc in options:
        console.print(f"  {opt_id}) {desc}")

    if allow_custom:
        console.print(f"  {len(options)+1}) ✏️ 自定义")

    while True:
        choice = Prompt.ask("请输入编号").strip()
        if choice == "/menu" and "开始新的创作" not in title:
            raise BackToMenu()
        if allow_custom and choice == str(len(options) + 1):
            return Prompt.ask("请输入自定义内容").strip()
        for opt_id, desc in options:
            if choice == opt_id:
                return choice
        console.print("[red]无效选择，请重新输入[/red]")


def show_progress(stage_name: str, progress: float):
    bar_length = 30
    filled = int(bar_length * progress)
    bar = "━" * filled + "─" * (bar_length - filled)
    console.print(f"\n[cyan]{stage_name}[/cyan]")
    console.print(f"  {bar} {int(progress * 100)}%")


def notify_complete(stage_name: str, file_path: str):
    console.print(f"\n[bold green]✅ {stage_name}已完成！[/bold green]")
    console.print(f"   请在 [cyan]{file_path}[/cyan] 中查看")


def select_version() -> str:
    console.print("\n[bold yellow]📋 请选择你要保留的版本：[/bold yellow]")
    console.print("  [dim]也可以输入 /menu 返回主菜单[/dim]")
    console.print("  1) 版本A - 经典/稳妥方向")
    console.print("  2) 版本B - 创新/反套路方向")
    console.print("  3) 混合两者（取A的某部分+B的某部分，请在修改意见中说明）")
    while True:
        choice = Prompt.ask("请输入编号 [1-3]").strip()
        if choice == "/menu":
            raise BackToMenu()
        if choice in ["1", "2", "3"]:
            return choice
        console.print("[red]无效选择，请输入 1、2 或 3[/red]")


def wait_for_approval() -> Tuple[bool, str]:
    console.print("   [dim]回车 = 通过 | 输入修改意见 = 要求修改 | /reject = 退回 | /menu = 返回主菜单[/dim]")
    feedback = Prompt.ask("[yellow]请审核[/yellow]").strip()
    if feedback.lower() == "/menu":
        raise BackToMenu()
    if not feedback or feedback.lower() == "/approve":
        return True, ""
    elif feedback.lower() == "/reject":
        reason = Prompt.ask("[red]请说明退回原因[/red]").strip()
        return False, reason
    else:
        return False, feedback
