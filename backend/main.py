from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 拆分後的 API 註冊器
from english_api import register_english_endpoints
from math_api import register_math_endpoints


def create_app() -> FastAPI:
    app = FastAPI(title="api", version="v1")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 註冊英文與數學端點
    register_english_endpoints(app)
    register_math_endpoints(app)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


