"""
故事创作系统 - Web 服务器启动入口
启动前自动运行环境检测，确保所有依赖就绪
"""
import sys
import os
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent


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
        import time
        time.sleep(2)
        try:
            os.system("start http://localhost:8000")
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    os.chdir(str(ROOT))
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / ".pkg"))

    run_setup()
    start_server()
