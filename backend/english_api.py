from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, Literal
from datetime import datetime

from english_solver import english_core, store


def register_english_endpoints(app: FastAPI):
    """將英文學習端點註冊到主應用"""

    @app.get("/api/v1/meta/health", tags=["Meta"])
    async def health_check():
        return {"status": "ok"}

    @app.get("/api/v1/meta/version", tags=["Meta"]) 
    async def version_info():
        return {
            "version": "v1",
            "deployment_time": datetime.utcnow().isoformat() + "Z",
        }

    @app.get("/api/v1/pronounce", tags=["Pronounce"])
    async def get_pronunciation(
        text: str,
        voice: Optional[Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]] = None,
        speed: Optional[Literal["slow", "normal"]] = "normal",
        model: Optional[str] = None
    ):
        audio_bytes = await english_core.tts(text=text, voice=voice, speed=speed, model=model)
        return StreamingResponse(iter([audio_bytes]), media_type="audio/mpeg")

    @app.get("/api/v1/models", tags=["Meta"]) 
    async def list_models():
        # 提供前端所需的 llm 與 tts 選單
        return {
            "llm": {
                "gpt-4o": {},
                "gpt-4o-mini": {},
                "gpt-o4-mini": {},
            },
            "tts": {
                "tts-1": {"voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]},
                "tts-1-hd": {"voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]},
            },
        }

    @app.post("/api/v1/models/select", tags=["Meta"]) 
    async def select_models(llm: Optional[str] = None, tts: Optional[str] = None, tts_voice: Optional[str] = None):
        # 在此可掛接實際模型切換邏輯；暫以回傳確認為主
        return {"ok": True, "llm": llm, "tts": tts, "tts_voice": tts_voice}

    @app.get("/api/v1/query", tags=["Query"]) 
    async def smart_query(q: str, level: Optional[Literal["A1", "A2", "B1", "B2", "C1", "C2"]] = None, model: Optional[str] = None):
        return await english_core.smart_query(q=q, level=level, model=model)

    @app.post("/api/v1/conversation", tags=["Conversation"]) 
    async def start_conversation(topic: str, level: str, model: Optional[str] = None, title: Optional[str] = None):
        return await english_core.start_conversation(topic=topic, level=level, model=model, title=title)

    @app.post("/api/v1/conversation/{sid}", tags=["Conversation"]) 
    async def next_conversation_turn(sid: str, user: str):
        return await english_core.next_turn(sid=sid, user_text=user)

    @app.delete("/api/v1/conversation/{sid}", tags=["Conversation"]) 
    async def end_conversation(sid: str):
        return english_core.end_conversation(sid)

    @app.get("/api/v1/conversations/archived", tags=["Conversation"]) 
    async def list_archived_conversations():
        archives = english_core.list_archives()
        return {"archives": archives}

    @app.get("/api/v1/conversations/archived/{sid}", tags=["Conversation"]) 
    async def get_archived_conversation_transcript(sid: str):
        return english_core.get_archive_transcript(sid)

    @app.get("/api/v1/conversations/search", tags=["Conversation"]) 
    async def search_conversations_api(query: Optional[str] = None, topic: Optional[str] = None, level: Optional[str] = None, limit: int = 10):
        results = store.search_conversations(query=query or "", topic=topic or "", level=level or "", limit=limit)
        return {"results": results, "total": len(results)}


