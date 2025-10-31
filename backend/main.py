from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from config_loader import config_loader
from model_registry import model_registry

# Load environment variables from .env file
load_dotenv()

# 拆分後的 API 註冊器
from english_api import register_english_endpoints
from math_api import register_math_endpoints
from config_api import register_config_endpoints

# 建立fastapi 實例
def create_app() -> FastAPI:
    app = FastAPI(title="api", version="v1")

    allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 註冊端點
    register_english_endpoints(app)
    register_math_endpoints(app)
    register_config_endpoints(app)

    # 啟動時先同步 last_selected，若無則套用 defaults 至 model_registry
    try:
        for feature in ("english", "math"):
            last = config_loader.get_last_selected(feature)
            if last:
                model_registry.set_models(
                    feature,
                    llm=last.get("llm"),
                    tts=last.get("tts"),
                    tts_voice=last.get("tts_voice"),
                )
            else:
                defaults = config_loader.get_defaults(feature)
                if defaults:
                    model_registry.set_models(
                        feature,
                        llm=defaults.get("llm"),
                        tts=defaults.get("tts"),
                        tts_voice=defaults.get("tts_voice"),
                    )
    except Exception:
        # 若同步發生問題，不阻斷服務啟動
        pass

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


