from typing import Tuple, Callable
from .cli import notify_complete, wait_for_approval, console


def review_loop(
    stage_name: str,
    file_path: str,
    generate_fn: Callable[[str], str],
    write_fn: Callable[[str], None],
    max_iterations: int = 5,
) -> bool:
    for iteration in range(max_iterations):
        notify_complete(stage_name, file_path)
        approved, feedback = wait_for_approval()

        if approved:
            console.print(f"[green]✅ {stage_name}已通过审核！[/green]")
            return True

        if not feedback:
            console.print("[yellow]跳过修改，进入下一阶段[/yellow]")
            return True

        console.print(f"[cyan]🔄 第{iteration+1}轮修改中...[/cyan]")
        new_content = generate_fn(feedback)
        write_fn(new_content)

    console.print(f"[red]⚠️ 已达到最大修改次数({max_iterations})，强制进入下一阶段[/red]")
    return True
