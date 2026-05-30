import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".pkg"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import shutil

DATA_DIR = Path(os.environ.get("STORYFORGE_DATA_DIR", str(ROOT)))
RESOURCES_DIR = Path(os.environ.get("STORYFORGE_RESOURCES_DIR", str(ROOT)))
ELECTRON_PORT = os.environ.get("STORYFORGE_PORT", "")


def _init_user_data():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    dirs_to_ensure = ["prompts", "config", "memory", "memory/sessions", "projects", "generated"]
    for d in dirs_to_ensure:
        (DATA_DIR / d).mkdir(parents=True, exist_ok=True)

    files_to_seed = {
        "prompts": [
            "outline_designer.txt", "plot_expander.txt", "screenplay_writer.txt",
            "storyboarder.txt", "video_producer.txt", "visual_extractor.txt",
            "image_artist.txt", "outline_direction_card.txt", "outline_full.txt",
            "prompt_engineer.txt",
        ],
        "config": ["image_presets.json"],
        ".": ["orchestrator_router.txt"],
    }

    for subdir, filenames in files_to_seed.items():
        for fname in filenames:
            dest = DATA_DIR / subdir / fname if subdir != "." else DATA_DIR / fname
            if not dest.exists():
                src = RESOURCES_DIR / subdir / fname if subdir != "." else RESOURCES_DIR / fname
                if src.exists():
                    shutil.copy2(src, dest)

    env_dest = DATA_DIR / ".env"
    if not env_dest.exists():
        env_src = RESOURCES_DIR / ".env.example"
        if env_src.exists():
            shutil.copy2(env_src, env_dest)

    load_dotenv(DATA_DIR / ".env", override=True)


_init_user_data()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .routes.projects import router as projects_router
from .routes.settings import router as settings_router
from .routes.creation import router as creation_router
from .routes.gen import router as gen_router
from .routes.prompt_gen import router as prompt_gen_router

app = FastAPI(title="多智能体故事创作系统")

# Migrate old env-based aggregated config to new file-based storage
AGG_CONFIG_PATH = ROOT / "aggregated_configs.json"
if not AGG_CONFIG_PATH.exists():
    old_enabled = os.getenv("AGGREGATED_ENABLED", "")
    old_base = os.getenv("AGGREGATED_BASE_URL", "")
    old_key = os.getenv("AGGREGATED_API_KEY", "")
    old_llm = os.getenv("AGGREGATED_LLM_MODEL", "")
    old_img = os.getenv("AGGREGATED_IMAGE_MODEL", "")
    old_vid = os.getenv("AGGREGATED_VIDEO_MODEL", "")
    if old_enabled in ("1", "true") and old_base and old_key and "your-key" not in old_key and "****" not in old_key:
        import json
        configs = []
        types = [("llm", old_llm), ("image", old_img), ("video", old_vid)]
        for t, m in types:
            configs.append({
                "id": f"agg_{t}",
                "name": f"默认聚合({t})",
                "base_url": old_base, "api_key": old_key,
                "type": t, "model": m or "", "active": True,
            })
        AGG_CONFIG_PATH.write_text(json.dumps(configs, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[migrate] 已迁移 {len(configs)} 个聚合配置到 {AGG_CONFIG_PATH}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    tb = traceback.format_exc()
    print(f"[Unhandled Error] {request.method} {request.url.path}: {exc}")
    print(tb)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__}
    )


app.include_router(projects_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(creation_router, prefix="/api")
app.include_router(gen_router, prefix="/api")
app.include_router(prompt_gen_router)

generated_dir = DATA_DIR / "generated"
if generated_dir.exists():
    app.mount("/generated", StaticFiles(directory=str(generated_dir)), name="generated")

frontend_dist = ROOT / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index = frontend_dist / "index.html"
        if (frontend_dist / full_path).is_file():
            return FileResponse(frontend_dist / full_path)
        return FileResponse(index)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("STORYFORGE_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port)
