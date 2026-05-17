"""
setup_env.py - 一键环境检测与自动安装
在其他设备上运行此脚本可自动安装所有依赖（已有则跳过）
单独运行: python setup_env.py
"""
import subprocess
import sys
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")


def info(msg):
    print(f"  {CYAN}→{RESET} {msg}")


def warn(msg):
    print(f"  {YELLOW}⚠{RESET} {msg}")


def fail(msg):
    print(f"  {RED}✗{RESET} {msg}")


def check_python():
    print(f"\n{CYAN}[1/5] 检查 Python 环境...{RESET}")
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 10):
        fail(f"Python 版本过低: {major}.{minor}，需要 >= 3.10")
        print("  请从 https://www.python.org/downloads/ 下载安装 Python 3.10+")
        return False
    ok(f"Python {major}.{minor}.{sys.version_info[2]}")
    return True


def _get_missing_packages(req_file: Path):
    """读取 requirements.txt 并返回缺失的包列表（幂等：已有则跳过）"""
    with open(req_file, encoding="utf-8") as f:
        required = []
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                required.append(line)

    installed = {}
    try:
        from importlib.metadata import distributions
        for dist in distributions():
            installed[dist.metadata["Name"].lower()] = dist.version
    except ImportError:
        pass

    missing = []
    for req_str in required:
        name = re.split(r"[>=<~!\[;]", req_str)[0].strip().lower()
        if name not in installed:
            missing.append(req_str)

    return missing


def install_python_deps():
    print(f"\n{CYAN}[2/5] 检查 Python 依赖...{RESET}")
    req_file = ROOT / "requirements.txt"
    if not req_file.exists():
        warn("requirements.txt 不存在，跳过")
        return True

    missing = _get_missing_packages(req_file)

    if not missing:
        ok("所有 Python 依赖已就绪")
        return True

    # Try pip install, inform user what's needed
    info(f"安装 {len(missing)} 个缺失的 Python 包...")

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install"] + missing,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        ok("Python 依赖安装完成")
        return True
    except subprocess.CalledProcessError:
        fail("自动安装失败，尝试备选方法...")
        for pkg in missing:
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pkg],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.STDOUT,
                )
                ok(f"  {pkg} 安装成功")
            except subprocess.CalledProcessError:
                fail(f"  {pkg} 安装失败")
        return False


def _find_node():
    """查找可用的 Node.js，优先便携版"""
    portable_dir = ROOT / ".node"
    if portable_dir.exists():
        for item in portable_dir.iterdir():
            if item.is_dir():
                node_exe = item / "node.exe"
                if node_exe.exists():
                    return str(node_exe)

    try:
        result = subprocess.run(
            ["where", "node"], capture_output=True, text=True, shell=True
        )
        if result.returncode == 0:
            lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
            if lines:
                return lines[0]
    except Exception:
        pass

    candidates = [
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
        os.path.expandvars(r"%APPDATA%\npm\node.exe"),
        os.path.expandvars(r"%ProgramFiles%\nodejs\node.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _get_npm_from_node(node_path):
    """从 node.exe 路径推算 npm.cmd 路径"""
    node_dir = Path(node_path).parent
    npm_cmd = node_dir / "npm.cmd"
    if npm_cmd.exists():
        return str(npm_cmd)
    npm_exe = node_dir / "npm"
    if npm_exe.exists():
        return str(npm_exe)
    return None


def _download_portable_node():
    """自动下载便携版 Node.js"""
    import urllib.request
    import zipfile

    node_dir = ROOT / ".node"
    node_dir.mkdir(exist_ok=True)

    version = "v20.18.0"
    url = f"https://nodejs.org/dist/{version}/node-{version}-win-x64.zip"
    zip_path = node_dir / "node.zip"

    info(f"正在下载 Node.js {version} 便携版...")
    try:
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(node_dir)
        zip_path.unlink()
        return True
    except Exception as e:
        fail(f"下载失败: {e}")
        return False


def check_nodejs():
    print(f"\n{CYAN}[3/5] 检查 Node.js 环境...{RESET}")
    node_path = _find_node()

    if node_path:
        try:
            ver = subprocess.run(
                [node_path, "--version"], capture_output=True, text=True
            ).stdout.strip()
            ok(f"Node.js {ver}")
            return True
        except Exception:
            pass

    warn("未检测到 Node.js")
    download = input("  → 是否自动下载便携版 Node.js？(y/N): ").strip().lower()
    if download == 'y':
        if _download_portable_node():
            return check_nodejs()
        else:
            return False

    print("  如果只需要 CLI 模式，可以正常运行: python main.py")
    print("  如果需要 Web 界面，可以稍后重新运行此设置")
    return False


def _run_npm(args, cwd=None):
    """使用找到的 Node.js 运行 npm"""
    node_path = _find_node()
    if not node_path:
        return False
    npm = _get_npm_from_node(node_path)
    if not npm:
        exe = node_path
        p = subprocess.run(
            [exe, Path(node_path).parent / "node_modules" / "npm" / "bin" / "npm-cli.js"] + args,
            cwd=cwd or str(ROOT),
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )
        return p.returncode == 0

    try:
        subprocess.check_call(
            [npm] + args,
            cwd=cwd or str(ROOT),
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def install_npm_deps():
    print(f"\n{CYAN}[4/5] 检查前端依赖...{RESET}")

    node_modules = ROOT / "node_modules"
    has_lock = (ROOT / "package-lock.json").exists()

    if node_modules.exists():
        ok("node_modules 已存在")
        return True

    if not has_lock:
        warn("package-lock.json 不存在，跳过前端构建")
        return False

    info("安装 npm 依赖...")
    if _run_npm(["install"]):
        ok("npm 依赖安装完成")
        return True
    warn("npm install 失败，跳过前端构建")
    return False


def build_frontend():
    print(f"\n{CYAN}[5/5] 检查前端构建...{RESET}")

    dist = ROOT / "dist"
    if dist.exists() and any(dist.iterdir()):
        ok("前端已构建")
        return True

    node_modules = ROOT / "node_modules"
    if not node_modules.exists():
        warn("node_modules 不存在，跳过前端构建（使用已有 dist 或仅 API 模式）")
        return False

    info("构建前端...")
    if _run_npm(["run", "build"]):
        ok("前端构建完成")
        return True
    warn("前端构建失败，使用已有 dist（如有）")
    return False


def check_env_file():
    env_file = ROOT / ".env"
    env_example = ROOT / ".env.example"

    if env_file.exists():
        ok(".env 配置文件已存在")
        return True

    if env_example.exists():
        import shutil
        shutil.copy2(env_example, env_file)
        print()
        warn(".env 已从 .env.example 自动创建")
        print(f"\n  {YELLOW}⚠ 重要：请编辑 .env 文件，填入你的 API Key！{RESET}")
        print(f"  文件位置: {env_file}")
        return True

    warn(".env 和 .env.example 都不存在")
    return True


def fix_old_project_configs():
    """修复旧项目的阶段索引对齐"""
    projects_dir = ROOT / "projects"
    if not projects_dir.exists():
        return
    required = ["story_outline", "full_plot", "full_script", "storyboard", "prompts", "video"]
    fixed = 0
    for item in projects_dir.iterdir():
        if not item.is_dir():
            continue
        config_file = item / "project_config.json"
        if not config_file.exists():
            continue
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
            phases = config.get("phases", [])
            names = [p["name"] for p in phases]
            if names == required:
                continue
            new_phases = []
            for rn in required:
                if rn in names:
                    new_phases.append(phases[names.index(rn)])
                else:
                    new_phases.append({"name": rn, "done": True})
            config["phases"] = new_phases
            config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            fixed += 1
        except Exception:
            pass
    if fixed:
        ok(f"已修复 {fixed} 个旧项目的阶段配置")


def main():
    print(f"\n{'='*55}")
    print(f"  {CYAN}🎬 故事创作系统 - 环境检测与自动安装{RESET}")
    print(f"{'='*55}")

    steps = [
        ("Python 版本", check_python),
        ("Python 依赖", install_python_deps),
        ("Node.js", check_nodejs),
        ("npm 依赖", install_npm_deps),
        ("前端构建", build_frontend),
    ]

    all_ok = True
    non_critical_ok = True
    for name, func in steps:
        try:
            result = func()
            if name in ("Node.js", "npm 依赖", "前端构建"):
                if not result:
                    non_critical_ok = False
            else:
                if not result:
                    all_ok = False
        except Exception as e:
            fail(f"{name}: {e}")
            if name in ("Python 版本", "Python 依赖"):
                all_ok = False

    check_env_file()
    fix_old_project_configs()

    print(f"\n{'='*55}")
    if all_ok and non_critical_ok:
        ok("环境检测全部通过！准备就绪 🚀")
        return True
    elif all_ok:
        warn("核心依赖就绪，前端环境未完全配置")
        print("  Web 界面可能不可用，但 CLI 模式可正常工作")
        print(f"  → 运行 {CYAN}python main.py{RESET} 使用命令行模式")
        return True
    else:
        fail("环境检测未通过，请根据以上提示修复")
        return False


if __name__ == "__main__":
    print(f"\n{CYAN}提示: 这是独立运行模式，启动系统时会自动调用此检查{RESET}")
    ready = main()
    sys.exit(0 if ready else 1)
