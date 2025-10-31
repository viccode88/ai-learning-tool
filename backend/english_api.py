from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, Literal
from datetime import datetime, timezone

from english_solver import english_core, store
from openai import OpenAI as SyncOpenAI
from pydantic import BaseModel
import os
import openai
from model_registry import model_registry
from config_loader import config_loader
import hashlib


def register_english_endpoints(app: FastAPI):
    """將英文學習端點註冊到主應用"""
    
    # 健康檢查
    @app.get("/api/v1/meta/health", tags=["Meta"])
    async def health_check():
        return {"status": "ok"}

    # 版本資訊
    @app.get("/api/v1/meta/version", tags=["Meta"]) 
    async def version_info():
        return {
            "version": "v1",
            "deployment_time": datetime.now(timezone.utc).isoformat(),
        }

    # 發音
    @app.get("/api/v1/pronounce", tags=["Pronounce"])
    async def get_pronunciation(
        text: str,
        voice: Optional[str] = None,
        speed: Optional[Literal["slow", "normal"]] = "normal",
        model: Optional[str] = None
    ):
        # TTS 檔案快取
        try:
            cache_dir = os.path.join(os.path.dirname(__file__), "tts_cache")
            os.makedirs(cache_dir, exist_ok=True)

            text_key = (text or "").strip()
            voice_key = voice or "default"
            speed_key = speed or "normal"
            # 若未指定，嘗試使用目前選定的 TTS 模型，否則退回設定檔預設
            default_tts = config_loader.get_defaults("english").get("tts", "gpt-4o-mini-tts")
            selected_tts_model = model or model_registry.get("english", "tts", default_tts)

            key_str = f"text={text_key}|voice={voice_key}|speed={speed_key}|model={selected_tts_model}"
            digest = hashlib.sha256(key_str.encode("utf-8")).hexdigest()
            cache_path = os.path.join(cache_dir, f"{digest}.mp3")

            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "rb") as f:
                        cached_bytes = f.read()
                    return StreamingResponse(iter([cached_bytes]), media_type="audio/mpeg")
                except Exception:
                    # 讀檔失敗則忽略，改為重新生成
                    pass

            # 快取未命中或讀檔失敗，生成並寫入快取
            audio_bytes = await english_core.tts(text=text_key, voice=voice, speed=speed_key, model=selected_tts_model)
            try:
                with open(cache_path, "wb") as f:
                    f.write(audio_bytes)
            except Exception:
                # 寫檔失敗不影響回應
                pass
            return StreamingResponse(iter([audio_bytes]), media_type="audio/mpeg")
        except Exception:
            # 快取流程意外，退回原本流程
            default_tts = config_loader.get_defaults("english").get("tts", "gpt-4o-mini-tts")
            fallback_model = model or model_registry.get("english", "tts", default_tts)
            audio_bytes = await english_core.tts(text=text, voice=voice, speed=speed, model=fallback_model)
            return StreamingResponse(iter([audio_bytes]), media_type="audio/mpeg")

    # 模型清單
    @app.get("/api/v1/models", tags=["Meta"]) 
    async def list_models():
        """從配置檔案取得可用模型清單"""
        
        
        # 取得 LLM 模型
        llm_models = config_loader.get_models("llm")
        llm = {m["id"]: {"name": m["name"], "endpoint": m["endpoint"]} for m in llm_models}
        
        # 取得 TTS 模型
        tts_models = config_loader.get_models("tts")
        tts_map = {}
        for m in tts_models:
            tts_map[m["id"]] = {
                "name": m["name"],
                "endpoint": m["endpoint"],
                "voices": m.get("voices", [])
            }

        return {
            "llm": llm,
            "tts": tts_map,
            "current": model_registry.get_all(),
        }

    # 模型選擇
    @app.get("/api/v1/models/selection", tags=["Meta"]) 
    async def get_model_selection(feature: Optional[str] = None):
        if feature:
            return model_registry.get_feature_config(feature)
        return model_registry.get_all()

    # 最後一次選擇的模型
    @app.get("/api/v1/models/last", tags=["Meta"]) 
    async def get_last_selected_models(feature: Optional[str] = "english"):
        """回傳最後一次選擇的模型；若無，回傳設定檔預設。"""
        selected_feature = feature or "english"
        defaults = config_loader.get_defaults(selected_feature) or {}
        last = config_loader.get_last_selected(selected_feature) or {}
        merged = dict(defaults)
        merged.update(last)
        return merged

    class StartConversationRequest(BaseModel):
        topic: str
        level: str
        model: Optional[str] = None
        title: Optional[str] = None
        user_prompt: Optional[str] = None

    class NextTurnRequest(BaseModel):
        user: str

    class SelectModelsRequest(BaseModel):
        feature: Optional[str] = "english"
        llm: Optional[str] = None
        tts: Optional[str] = None
        tts_voice: Optional[str] = None

    @app.post("/api/v1/models/select", tags=["Meta"]) 
    async def select_models(req: SelectModelsRequest):
        feature = req.feature or "english"
        valid_llm = req.llm
        if req.llm and not config_loader.get_model(req.llm, "llm"):
            valid_llm = None
        valid_tts = req.tts
        valid_voice = req.tts_voice
        if req.tts and not config_loader.get_model(req.tts, "tts"):
            valid_tts = None
            valid_voice = None
        else:
            if req.tts and req.tts_voice:
                tts_model = config_loader.get_model(req.tts, "tts") or {}
                voices = set((tts_model or {}).get("voices", []) or [])
                if req.tts_voice not in voices:
                    valid_voice = None

        cfg = model_registry.set_models(feature, llm=valid_llm, tts=valid_tts, tts_voice=valid_voice)
        try:
            for sid, meta in english_core.store.conversation_metadata.items():
                if feature == "english":
                    if req.llm:
                        meta["model"] = req.llm
                    if req.tts:
                        meta["tts"] = req.tts
                    if req.tts_voice:
                        meta["tts_voice"] = req.tts_voice
        except Exception:
            pass
        # 持久化最後一次選擇
        try:
            config_loader.set_last_selected(feature, {
                "llm": valid_llm,
                "tts": valid_tts,
                "tts_voice": valid_voice,
            })
        except Exception:
            pass
        return {"ok": True, "feature": feature, "config": cfg}

    @app.get("/api/v1/query", tags=["Query"]) 
    async def smart_query(q: str, level: Optional[Literal["A1", "A2", "B1", "B2", "C1", "C2"]] = None, model: Optional[str] = None):
        return await english_core.smart_query(q=q, level=level, model=model)

    @app.post("/api/v1/conversation", tags=["Conversation"]) 
    async def start_conversation(req: StartConversationRequest):
        try:
            return await english_core.start_conversation(topic=req.topic, level=req.level, model=req.model, title=req.title)
        except Exception as e:
            # 後備路徑：即使 LLM 失敗也建立對話並給一段預設開場白，避免 UX 中斷
            print(f"LLM 啟動失敗，使用後備路徑: {e}")
            import uuid
            sid = str(uuid.uuid4())
            topic = req.topic or ""
            level = req.level or "A1"
            default_llm = config_loader.get_defaults("english").get("llm", "gpt-5-mini")
            selected_llm = req.model or model_registry.get("english", "llm", default_llm)
            
            # 標題生成
            current_time = datetime.now().strftime("%m-%d %H:%M")
            base_title = topic if topic and topic.strip() else "新對話"
            title = req.title if req.title else f"{base_title} ({level}) @ {current_time}"

            greeting = f"Hello! Let's talk about {topic.lower() if topic else 'something interesting'}."
            hint = f"Try to respond about {topic or 'your day'}."
            translation = f"你好！讓我們來聊聊{topic if topic else '一些有趣的事情'}。"

            # 創建完整的 metadata
            metadata = {
                "topic": topic,
                "level": level,
                "model": selected_llm,
                "title": title,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            # 以結構化格式寫入會話
            structured_greeting = {
                "ai_response": greeting,
                "hint": hint,
                "translation": translation
            }
            messages = [{"role": "assistant", "content": structured_greeting}]
            
            # 保存到內存和檔案（確保 metadata 完整傳遞）
            store.conversations_db[sid] = messages
            store.conversation_metadata[sid] = metadata
            store.archived_conversations_db[sid] = list(messages)
            store.archived_conversation_metadata[sid] = dict(metadata)
            store.save_conversation(sid, messages, metadata, is_archived=False)
            store.save_conversation(sid, list(messages), dict(metadata), is_archived=True)
            
            return {"sid": sid, "ai": greeting, "hint": hint, "translation": translation}

    @app.post("/api/v1/conversation/{sid}", tags=["Conversation"]) 
    async def next_conversation_turn(sid: str, req: NextTurnRequest):
        return await english_core.next_turn(sid=sid, user_text=req.user)

    @app.post("/api/v1/conversation/{sid}/stream", tags=["Conversation"]) 
    async def next_conversation_turn_stream(sid: str, req: NextTurnRequest):
        """串流回傳 AI 回覆（SSE），使用 Structured Outputs 格式化輸出。"""
        if sid not in store.conversations_db:
            raise HTTPException(status_code=404, detail="Session ID not found.")

        # 準備訊息（包含既有歷史 + 本次 user）
        messages = list(store.conversations_db[sid])
        metadata = store.conversation_metadata.get(sid, {})
        default_llm = config_loader.get_defaults("english").get("llm", english_core.default_llm_model)
        selected_llm = metadata.get("model") or model_registry.get("english", "llm", default_llm)
        level = metadata.get("level", "B1")
        
        # 為 Structured Outputs 添加特定的系統提示
        structured_system_prompt = f"""You are an English conversation partner. Please respond with:
1. A natural response to the user's message (ai_response)
2. A helpful hint for their next reply in English (hint)
3. A Chinese translation of your response (translation)

Keep responses appropriate for CEFR level {level}.
Always provide all three fields."""
        
        # 構建包含系統提示的訊息列表
        full_messages = [{"role": "system", "content": structured_system_prompt}]
        full_messages.extend(messages)
        full_messages.append({"role": "user", "content": req.user})

        # 先把本次使用者訊息寫入對話記錄
        try:
            store.conversations_db[sid].append({"role": "user", "content": req.user})
            store.archived_conversations_db[sid] = list(store.conversations_db[sid])
            store.archived_conversation_metadata[sid] = dict(store.conversation_metadata.get(sid, {}))
            store.save_conversation(sid, store.conversations_db[sid], store.conversation_metadata.get(sid, {}), is_archived=False)
            store.save_conversation(sid, list(store.conversations_db[sid]), dict(store.conversation_metadata.get(sid, {})), is_archived=True)
        except Exception:
            pass

        # 轉換為 Responses API 輸入格式
        input_payload = []
        for m in full_messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            converted_role = "developer" if role == "system" else role
            if converted_role not in ("user", "assistant", "developer", "tool"):
                converted_role = "user"

            if isinstance(content, list):
                parts = []
                for item in content:
                    if not isinstance(item, dict):
                        text_type = "output_text" if converted_role == "assistant" else "input_text"
                        parts.append({
                            "type": text_type,
                            "text": str(item)
                        })
                        continue
                    t = item.get("type")
                    if t in ("text", "input_text", "output_text"):
                        text_type = "output_text" if converted_role == "assistant" else "input_text"
                        parts.append({
                            "type": text_type,
                            "text": item.get("text", "")
                        })
                    elif t == "image_url":
                        parts.append({"type": "input_image", "image_url": item.get("image_url")})
                input_payload.append({"role": converted_role, "content": parts})
            else:
                text_type = "output_text" if converted_role == "assistant" else "input_text"
                input_payload.append({
                    "role": converted_role,
                    "content": [{
                        "type": text_type,
                        "text": str(content)
                    }]
                })

        # 定義 Structured Outputs 的 JSON Schema
        conversation_schema = {
            "type": "object",
            "properties": {
                "ai_response": {
                    "type": "string",
                    "description": "The AI's natural response in English"
                },
                "hint": {
                    "type": "string",
                    "description": "A helpful hint for the user's next reply in English"
                },
                "translation": {
                    "type": "string",
                    "description": "Traditional Chinese translation of the AI's response"
                }
            },
            "required": ["ai_response", "hint", "translation"],
            "additionalProperties": False
        }

        def sse_event_generator():
            import json
            client = SyncOpenAI()
            full_text = []
            try:
                with client.responses.stream(
                    model=selected_llm,
                    input=input_payload,
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "conversation_response",
                            "schema": conversation_schema,
                            "strict": True
                        }
                    }
                ) as stream:
                    for event in stream:
                        etype = getattr(event, "type", "") or getattr(event, "event", "")
                        if etype == "response.output_text.delta":
                            delta = getattr(event, "delta", "")
                            if delta:
                                full_text.append(delta)
                                # 串流傳送 JSON 片段
                                yield f"data: {json.dumps({'type': 'delta', 'content': delta})}\n\n"
                        elif etype == "response.completed":
                            break
            except Exception as e:
                # 將錯誤以 SSE 回傳
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                return

            # 串流結束後，解析並保存完整的結構化回覆
            try:
                ai_full_json = "".join(full_text)
                parsed_response = json.loads(ai_full_json)
                
                # 從 store 獲取最新的 messages 和 metadata，確保一致性
                current_messages = store.conversations_db.get(sid, [])
                current_metadata = store.conversation_metadata.get(sid, {})

                # 保存完整的結構化回覆到對話記錄
                current_messages.append({"role": "assistant", "content": parsed_response})
                store.save_conversation(sid, current_messages, current_metadata, is_archived=False)
                store.save_conversation(sid, current_messages, current_metadata, is_archived=True)
                
                # 發送完整的結構化數據
                yield f"data: {json.dumps({'type': 'complete', 'data': parsed_response})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'解析回應失敗: {str(e)}'})}\n\n"

            yield "data: [DONE]\n\n"

        return StreamingResponse(
            sse_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    @app.delete("/api/v1/conversation/{sid}", tags=["Conversation"]) 
    async def delete_conversation(sid: str):
        """刪除指定對話（active 與 archived 檔案一併清理），並從索引移除。"""
        try:
            from english_solver import CONVERSATIONS_DIR, ARCHIVED_DIR, INDEX_FILE
            
            # 清理內存資料
            store.conversations_db.pop(sid, None)
            store.conversation_metadata.pop(sid, None)
            store.archived_conversations_db.pop(sid, None)
            store.archived_conversation_metadata.pop(sid, None)

            # 移除檔案
            import os, json
            for is_archived in (False, True):
                target_dir = ARCHIVED_DIR if is_archived else CONVERSATIONS_DIR
                path = os.path.join(target_dir, f"{sid}.json")
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
            # 更新索引
            if os.path.exists(INDEX_FILE):
                try:
                    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                        index = json.load(f)
                except Exception:
                    index = {"active": {}, "archived": {}}
                index.get("active", {}).pop(sid, None)
                index.get("archived", {}).pop(sid, None)
                try:
                    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                        json.dump(index, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            return {"ok": True, "sid": sid}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"刪除對話失敗: {e}")

    # 列出已歸檔的對話
    @app.get("/api/v1/conversations/archived", tags=["Conversation"]) 
    async def list_archived_conversations():
        archives = english_core.list_archives()
        return {"archives": archives}

    # 建立空白對話
    @app.post("/api/v1/conversations/new", tags=["Conversation"]) 
    async def create_empty_conversation(topic: str = "Practice", level: str = "A1", model: Optional[str] = None, title: Optional[str] = None):
        """建立空白對話（不觸發 LLM），回傳 sid 與基本中繼資料。"""
        import uuid
        sid = str(uuid.uuid4())
        
        # 標題生成
        current_time = datetime.now().strftime("%m-%d %H:%M")
        base_title = topic if topic != "Practice" else "新對話"
        conversation_title = title if title else f"{base_title} ({level}) @ {current_time}"

        default_llm = config_loader.get_defaults("english").get("llm", english_core.default_llm_model)
        selected_model = model or model_registry.get("english", "llm", default_llm)
        store.conversations_db[sid] = []
        store.conversation_metadata[sid] = {
            "topic": topic if topic != "Practice" else "",
            "level": level,
            "model": selected_model,
            "title": conversation_title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        store.save_conversation(sid, [], store.conversation_metadata[sid], is_archived=False)
        store.save_conversation(sid, [], dict(store.conversation_metadata[sid]), is_archived=True)
        return {"sid": sid, "title": conversation_title, "topic": topic, "level": level}

    # 獲取已歸檔的對話記錄
    @app.get("/api/v1/conversations/archived/{sid}", tags=["Conversation"]) 
    async def get_archived_conversation_transcript(sid: str):
        return english_core.get_archive_transcript(sid)

    # 搜尋對話
    @app.get("/api/v1/conversations/search", tags=["Conversation"]) 
    async def search_conversations_api(query: Optional[str] = None, topic: Optional[str] = None, level: Optional[str] = None, limit: int = 10):
        results = store.search_conversations(query=query or "", topic=topic or "", level=level or "", limit=limit)
        return {"results": results, "total": len(results)}


