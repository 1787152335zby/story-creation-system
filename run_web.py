"""
故事创作系统 - Web 服务器启动入口
启动前自动运行环境检测，确保所有依赖就绪
"""
import sys
import os
import time
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def kill_existing_server():
    """尝试优雅关闭已有进程，避免文件写一半被截断"""
    import subprocess
    cmd = 'netstat -ano | findstr ":8000 "'
    try:
        output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        for line in output.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 5 and "LISTENING" in parts:
                pid = parts[-1]
                try:
                    # 先尝试优雅关闭（发送 Ctrl+C 信号）
                    subprocess.run(["taskkill", "/PID", pid], capture_output=True, timeout=3)
                    # 给进程 3 秒优雅退出
                    for _ in range(6):
                        time.sleep(0.5)
                        check = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                                               capture_output=True, text=True)
                        if pid not in check.stdout:
                            return
                    # 没退出，强制 kill
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=3)
                except Exception:
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=3)
    except Exception:
        pass
    time.sleep(0.5)


def run_setup():
    """启动前运行环境检测与安装（已有则跳过）"""
    print("\n🔧 正在检测运行环境...")
    try:
        sys.path.insert(0, str(ROOT))
        import setup_env
        setup_env.main()
    except ImportError:
        print("  setup_env.py 未找到，跳过自动安装")
    except Exception as e:
        print(f"  环境检测异常: {e}")


def start_server():
    import uvicorn
    print("\n🚀 启动 Web 服务: http://localhost:8000")

    def open_browser():
        time.sleep(2)
        try:
            os.system("start http://localhost:8000")
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()
    time.sleep(0.5)
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    os.chdir(str(ROOT))
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / ".pkg"))

    kill_existing_server()
    run_setup()
    start_server()
