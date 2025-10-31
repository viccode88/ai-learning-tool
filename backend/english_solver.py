import os
import uuid
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

import openai
from prompt_loader import get_prompt
from fastapi import HTTPException
from model_registry import model_registry


# --- OpenAI 客戶端與設定 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)


# --- 英文學習服務的核心狀態與存取 ---
DATA_DIR = "conversation_data"
CONVERSATIONS_DIR = os.path.join(DATA_DIR, "conversations")
ARCHIVED_DIR = os.path.join(DATA_DIR, "archived")
INDEX_FILE = os.path.join(DATA_DIR, "index.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
os.makedirs(ARCHIVED_DIR, exist_ok=True)


class EnglishStore:
    def __init__(self):
        self.conversations_db: Dict[str, List[Dict[str, Any]]] = {}
        self.conversation_metadata: Dict[str, Dict[str, Any]] = {}
        # archived DB 只用於內存快取，主要數據源是檔案
        self.archived_conversations_db: Dict[str, List[Dict[str, Any]]] = {}
        self.archived_conversation_metadata: Dict[str, Dict[str, Any]] = {}
        self.load_conversations()

    # --- 檔案 I/O (重構後的核心保存邏輯) ---
    def save_conversation(self, sid: str, messages: List[Dict[str, Any]], metadata: Dict[str, Any], is_archived: bool = False):
        """
        將單個對話保存到對應的檔案（conversations 或 archived），並更新全局索引。
        這是唯一的寫入點，以確保數據一致性。
        """
        try:
            # 1. 準備和驗證 Metadata
            meta_to_save = metadata.copy()
            meta_to_save["updated_at"] = datetime.now().isoformat()

            # 如果 title 無效，則生成一個
            if not meta_to_save.get("title") or meta_to_save["title"] == "Unknown":
                topic = meta_to_save.get("topic", "")
                level = meta_to_save.get("level", "A1")
                try:
                    created_dt = datetime.fromisoformat(meta_to_save.get("created_at", "").replace("Z", "+00:00"))
                    time_str = created_dt.strftime("%m-%d %H:%M")
                except:
                    time_str = datetime.now().strftime("%m-%d %H:%M")
                
                base_title = topic if topic and topic.strip() else "新對話"
                meta_to_save["title"] = f"{base_title} ({level}) @ {time_str}"

            # 2. 準備寫入檔案的完整數據結構
            conversation_data = {
                "sid": sid,
                "metadata": meta_to_save,
                "messages": messages,
                "created_at": meta_to_save.get("created_at"),
                "updated_at": meta_to_save.get("updated_at")
            }

            # 3. 寫入對話檔案 (conversations 或 archived)
            target_dir = ARCHIVED_DIR if is_archived else CONVERSATIONS_DIR
            os.makedirs(target_dir, exist_ok=True)
            conversation_file = os.path.join(target_dir, f"{sid}.json")
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)

            # 4. 更新全局索引 (index.json)
            self._update_index_file(sid, messages, meta_to_save, is_archived)

        except Exception as e:
            print(f"❌ 保存會話 {sid} 時發生嚴重錯誤: {e}")

    def _update_index_file(self, sid: str, messages: List[Dict[str, Any]], metadata: Dict[str, Any], is_archived: bool):
        """獨立函數，專門負責讀寫 index.json，由 save_conversation 調用"""
        try:
            # 讀取現有索引
            if os.path.exists(INDEX_FILE):
                with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                    index = json.load(f)
            else:
                index = {"active": {}, "archived": {}}
            
            # 創建或更新索引條目
            index_entry = {
                "title": metadata.get("title"),
                "topic": metadata.get("topic", ""),
                "level": metadata.get("level", ""),
                "created_at": metadata.get("created_at"),
                "updated_at": metadata.get("updated_at"),
                "message_count": len(messages)
            }

            # 將條目放入 active 或 archived
            if is_archived:
                index["archived"][sid] = index_entry
                if sid in index["active"]:
                    del index["active"][sid]
            else:
                index["active"][sid] = index_entry

            # 寫回索引檔案
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"❌ 更新索引檔案時發生錯誤: {e}")

    def load_conversation(self, sid: str, is_archived: bool = False) -> tuple:
        try:
            target_dir = ARCHIVED_DIR if is_archived else CONVERSATIONS_DIR
            conversation_file = os.path.join(target_dir, f"{sid}.json")
            if os.path.exists(conversation_file):
                with open(conversation_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("messages", []), data.get("metadata", {})
            return [], {}
        except Exception as e:
            print(f"加載會話 {sid} 時發生錯誤: {e}")
            return [], {}

    def search_conversations(self, query: str = "", topic: str = "", level: str = "", limit: int = 10) -> List[Dict]:
        try:
            if not os.path.exists(INDEX_FILE):
                return []
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                index = json.load(f)

            results = []
            all_conversations = {**index.get("active", {}), **index.get("archived", {})}
            for sid, meta in all_conversations.items():
                if topic and topic.lower() not in meta.get("topic", "").lower():
                    continue
                if level and level.upper() != meta.get("level", "").upper():
                    continue
                if query and query.lower() not in meta.get("title", "").lower():
                    continue
                results.append({
                    "sid": sid,
                    "title": meta.get("title"),
                    "topic": meta.get("topic"),
                    "level": meta.get("level"),
                    "created_at": meta.get("created_at"),
                    "updated_at": meta.get("updated_at"),
                    "message_count": meta.get("message_count", 0),
                    "is_archived": sid in index.get("archived", {})
                })

            results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return results[:limit]
        except Exception as e:
            print(f"搜索會話時發生錯誤: {e}")
            return []

    def load_conversations(self):
        try:
            if os.path.exists(INDEX_FILE):
                with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                for sid in index.get("active", {}):
                    messages, metadata = self.load_conversation(sid, is_archived=False)
                    if messages or metadata:
                        self.conversations_db[sid] = messages
                        self.conversation_metadata[sid] = metadata
                for sid, idx_metadata in index.get("archived", {}).items():
                    self.archived_conversation_metadata[sid] = idx_metadata
            else:
                print("沒有找到索引文件，開始新的會話存儲")
        except Exception as e:
            print(f"加載會話數據時發生錯誤: {e}")


store = EnglishStore()


class EnglishCore:
    def __init__(self):
        # 預設 LLM 改為 gpt-5，可由 registry 或環境變數覆蓋
        self.default_llm_model = os.getenv("DEFAULT_LLM_MODEL", "gpt-5-mini")
        self.default_tts_model = "tts-1"
        self.default_tts_voice = "alloy"
        # 本地 TTS 選項保留，以利前端下拉
        self.available_tts_models_info = {
            "tts-1": {"version": "latest", "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"], "speeds": ["slow", "normal"]},
            "tts-1-hd": {"version": "latest", "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"], "speeds": ["slow", "normal"]},
        }

    # --- Responses API 包裝 ---
    async def _responses_create(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        text_format: Optional[Dict[str, Any]] = None,
    ) -> Any:
        # 轉換 chat 格式為 responses input
        input_payload: List[Dict[str, Any]] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content")
            converted_role = "developer" if role == "system" else role
            if converted_role not in ("user", "assistant", "developer", "tool"):
                converted_role = "user"

            if isinstance(content, dict):
                # 假設 dict 格式的 content 是為 Responses API 準備的結構化 JSON
                # 直接將其轉換為 input_text/output_text 的格式
                text_content = json.dumps(content, ensure_ascii=False)
                text_type = "output_text" if converted_role == "assistant" else "input_text"
                input_payload.append({
                    "role": converted_role,
                    "content": [{"type": text_type, "text": text_content}]
                })
            elif isinstance(content, list):
                # 轉換多模態 content 列表
                converted_items = []
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get("type")
                        if item_type in ("text", "input_text", "output_text"):
                            text_type = "output_text" if converted_role == "assistant" else "input_text"
                            converted_items.append({"type": text_type, "text": item.get("text", "")})
                        elif item_type in ("image_url", "input_image"):
                            converted_items.append({"type": "input_image", "image_url": item.get("image_url")})
                        else:
                            converted_items.append(item) # 其他類型直接傳遞
                    else: # 非 dict 的 item 視為純文字
                        text_type = "output_text" if converted_role == "assistant" else "input_text"
                        converted_items.append({"type": text_type, "text": str(item)})
                input_payload.append({"role": converted_role, "content": converted_items})
            else: # 純文字 content
                text_type = "output_text" if converted_role == "assistant" else "input_text"
                input_payload.append({
                    "role": converted_role,
                    "content": [{"type": text_type, "text": str(content)}]
                })
        
        kwargs: Dict[str, Any] = {
            "model": model,
            "input": input_payload,
        }
        if tools:
            # Normalize tools to Responses API expected shape:
            # [{"type": "function", "name": str, "description": str, "parameters": {...}}]
            normalized_tools: List[Dict[str, Any]] = []
            for t in tools:
                try:
                    if t.get("type") == "function" and isinstance(t.get("function"), dict):
                        fn = t["function"]
                        normalized_tools.append({
                            "type": "function",
                            "name": fn.get("name"),
                            "description": fn.get("description"),
                            "parameters": fn.get("parameters")
                        })
                    else:
                        # already in responses format or other built-in tools
                        normalized_tools.append(t)
                except Exception:
                    normalized_tools.append(t)
            kwargs["tools"] = normalized_tools
        try:
            debug_tools = kwargs.get("tools", None)
            if debug_tools is not None:
                print(f"[english_solver] Calling Responses with tools: {json.dumps(debug_tools)[:200]}")
            else:
                print("[english_solver] Calling Responses with no tools")
        except Exception:
            pass
        if text_format is not None:
            kwargs["text"] = text_format
        # 注意：部分模型不支援 temperature 於 Responses API，為相容性省略
        if max_output_tokens is not None:
            kwargs["max_output_tokens"] = max_output_tokens

        return await client.responses.create(**kwargs)

    def _extract_json_output(self, response: Any) -> Optional[Dict[str, Any]]:
        """Best-effort extraction of a single JSON object from a Responses API response.

        Some models may not populate `output_text`. This function will look into
        `response.output` and concatenate any segments with type 'message' → content items
        of type 'output_text', then attempt to json.loads the result.
        """
        try:
            # Try direct text first
            raw_text = getattr(response, "output_text", None)
            if isinstance(raw_text, str) and raw_text.strip():
                return json.loads(raw_text)

            # Fallback: aggregate from output list
            output = getattr(response, "output", None)
            if output and isinstance(output, list):
                collected: List[str] = []
                for item in output:
                    if getattr(item, "type", None) == "message":
                        contents = getattr(item, "content", [])
                        for c in contents:
                            if getattr(c, "type", None) == "output_text":
                                txt = getattr(c, "text", "")
                                if isinstance(txt, str):
                                    collected.append(txt)
                if collected:
                    joined = "".join(collected).strip()
                    if joined:
                        return json.loads(joined)
        except Exception:
            return None
        return None

    def _extract_plain_text(self, response: Any) -> str:
        """Extract plain text from Responses API response regardless of schema."""
        # Prefer output_text
        raw_text = getattr(response, "output_text", None)
        if isinstance(raw_text, str) and raw_text.strip():
            return raw_text
        # Fallback to concatenating message output_text parts
        output = getattr(response, "output", None)
        if output and isinstance(output, list):
            parts: List[str] = []
            for item in output:
                if getattr(item, "type", None) == "message":
                    contents = getattr(item, "content", [])
                    for c in contents:
                        if getattr(c, "type", None) == "output_text":
                            txt = getattr(c, "text", "")
                            if isinstance(txt, str):
                                parts.append(txt)
            if parts:
                return "".join(parts)
        return ""

    def _extract_tool_args_from_responses(self, response: Any, tool_name: str) -> Optional[Dict[str, Any]]:
        # 嘗試從 Responses API 的輸出中提取 tool call 參數
        try:
            output = getattr(response, "output", None)
            if output and isinstance(output, list):
                for item in output:
                    item_type = getattr(item, "type", None)
                    if item_type == "tool_call":
                        if getattr(item, "tool_name", None) == tool_name:
                            args = getattr(item, "arguments", None)
                            if isinstance(args, (str, bytes)):
                                import json as _json
                                return _json.loads(args)
                            if isinstance(args, dict):
                                return args
            # 部分 SDK 提供 output_text，若模型已直接輸出 JSON
            output_text = getattr(response, "output_text", None)
            if output_text:
                import json as _json
                try:
                    return _json.loads(output_text)
                except Exception:
                    return None
        except Exception:
            return None
        return None

    # --- 對外暴露的操作邏輯（供 API 呼叫） ---
    async def tts(self, text: str, voice: Optional[Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]] = None, speed: Optional[Literal["slow", "normal"]] = "normal", model: Optional[str] = None) -> bytes:
        if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            raise HTTPException(status_code=500, detail="OpenAI API Key not configured.")
        selected_tts_model = model if model and model in self.available_tts_models_info else model_registry.get("english", "tts", self.default_tts_model)
        selected_voice = voice if voice else model_registry.get("english", "tts_voice", self.default_tts_voice)
        tts_speed_value = 0.85 if speed == "slow" else 1.0
        try:
            response = await client.audio.speech.create(
                model=selected_tts_model,
                voice=selected_voice,
                input=text,
                response_format="mp3",
                speed=tts_speed_value
            )
            audio_bytes = await response.aread()
            return audio_bytes
        except openai.APIError as e:
            print(f"OpenAI API error: {e}")
            raise HTTPException(status_code=500, detail=f"TTS generation failed: {e.message}")
        except Exception as e:
            print(f"Error in tts: {e}")
            raise HTTPException(status_code=500, detail="Internal server error during TTS generation.")

    async def smart_query(self, q: str, level: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            raise HTTPException(status_code=500, detail="OpenAI API Key not configured.")
        # 強制採用支援 Structured Outputs 的模型，忽略前端傳入的不相容模型
        requested_llm = model or model_registry.get("english", "llm", self.default_llm_model)
        supported_llms = {
            "gpt-4o-mini",
            "gpt-4o-mini-2024-07-18",
            "gpt-4o-2024-08-06",
        }
        selected_llm = requested_llm if requested_llm in supported_llms else "gpt-4o-mini"
        level_text = level if level else 'B1 (default)'
        messages = [
            {"role": "system", "content": get_prompt("english.smart_query_system", level=level_text, default=f"""You are an English learning assistant. Analyze the user's query and provide detailed information.
Determine if the query is a single word, a phrase, a sentence, or a grammar question.
Target CEFR level for examples and explanations: {level_text}.
Respond in valid JSON strictly matching the provided schema.
If providing IPA, use standard IPA notation.
If providing an audio_url, return null unless you have a known audio.
For 'grammar_tips', provide concise and useful information related to the query.
If the query is a sentence, provide its translation into Traditional Chinese and highlight grammar points.
If the query is a phrase, explain its meaning and usage.
If the query is a word, provide definitions (with part of speech), IPA, and example sentences.
If unsure about the type, classify as 'unknown' and provide a helpful response or ask for clarification.
""")},
            {"role": "user", "content": q}
        ]

        # Structured Outputs: JSON Schema
        schema: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["word", "phrase", "sentence", "grammar_explanation", "unknown"]
                },
                "query": {"type": "string"},
                "definitions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pos": {"type": ["string", "null"]},
                            "text": {"type": "string"}
                        },
                        "required": ["pos", "text"],
                        "additionalProperties": False
                    }
                },
                "ipa": {"type": "string"},
                "examples": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "level": {"type": ["string", "null"]}
                        },
                        "required": ["text", "level"],
                        "additionalProperties": False
                    }
                },
                "translation": {"type": "string"},
                "grammar_tips": {"type": "string"},
                "audio_url": {"type": ["string", "null"]}
            },
            "required": [
                "type",
                "query",
                "definitions",
                "ipa",
                "examples",
                "translation",
                "grammar_tips",
                "audio_url"
            ],
            "additionalProperties": False
        }

        try:
            # 使用 Structured Outputs（JSON Schema）
            resp = await self._responses_create(
                model=selected_llm,
                messages=messages,
                text_format={
                    "format": {
                        "type": "json_schema",
                        "name": "english_query",
                        "schema": schema,
                        "strict": True,
                    }
                },
                max_output_tokens=800,
            )
            # Best-effort extraction (no chat completions fallback)
            parsed = self._extract_json_output(resp)
            if parsed is None:
                # Plain-text fallback (still using Responses API, no schema)
                resp2 = await self._responses_create(
                    model=selected_llm,
                    messages=messages,
                    max_output_tokens=600,
                )
                text_out = self._extract_plain_text(resp2).strip()
                # Build minimal structured response from plain text (even if empty)
                fallback_text = text_out if text_out else "No structured output from LLM. Please try another query."
                return {
                    "type": "unknown",
                    "query": q,
                    "definitions": [],
                    "ipa": "",
                    "examples": [],
                    "translation": "",
                    "grammar_tips": fallback_text[:2000],
                    "audio_url": None,
                }
            return parsed
        except openai.APIError as e:
            print(f"OpenAI API error during query: {e}")
            # Soft fallback to avoid 500 to frontend
            return {
                "type": "unknown",
                "query": q,
                "definitions": [],
                "ipa": "",
                "examples": [],
                "translation": "",
                "grammar_tips": f"Service error: {getattr(e, 'message', str(e))}",
                "audio_url": None,
            }
        except json.JSONDecodeError as e:
            print(f"JSON decode error from LLM response: {e}")
            return {
                "type": "unknown",
                "query": q,
                "definitions": [],
                "ipa": "",
                "examples": [],
                "translation": "",
                "grammar_tips": "Could not decode model response. Please try again.",
                "audio_url": None,
            }
        except Exception as e:
            print(f"Error in smart_query: {e}")
            return {
                "type": "unknown",
                "query": q,
                "definitions": [],
                "ipa": "",
                "examples": [],
                "translation": "",
                "grammar_tips": "Internal server error during query processing.",
                "audio_url": None,
            }

    async def start_conversation(self, topic: str, level: str, model: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
        if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            raise HTTPException(status_code=500, detail="OpenAI API Key not configured.")
        
        sid = str(uuid.uuid4())
        selected_llm = model or model_registry.get("english", "llm", self.default_llm_model)
        
        # 創建一個完整的、初始的 metadata 物件
        # 這個物件將在整個對話生命週期中被傳遞和更新
        now_iso = datetime.now().isoformat()
        metadata = {
            "sid": sid,
            "topic": topic,
            "level": level,
            "model": selected_llm,
            "title": title or "", # title 將在 save_conversation 中被妥善處理
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        initial_system_prompt = get_prompt("english.start_conversation_system", topic=topic, level=level, default=f"""You are an AI English conversation partner.
The user wants to practice a conversation about \"{topic}\" at CEFR level {level}.
Start the conversation with a welcoming message and a first question or statement related to the topic.
Provide a brief, one-sentence hint for the user's first response.
Keep your responses concise and appropriate for the {level} level.
Avoid complex vocabulary or grammar unless specifically requested or appropriate for a higher level practice.
Your goal is to help the user practice speaking English in a natural way.
""")
        messages: List[Dict[str, Any]] = [{"role": "system", "content": initial_system_prompt}]
        
        # 定義結構化輸出 schema
        greeting_schema = {
            "type": "object",
            "properties": {
                "ai_response": {"type": "string", "description": "The AI's greeting message in English"},
                "hint": {"type": "string", "description": "A helpful hint for the user's first reply in English"},
                "translation": {"type": "string", "description": "Traditional Chinese translation of the greeting"}
            },
            "required": ["ai_response", "hint", "translation"],
            "additionalProperties": False
        }
        
        try:
            # 使用 Responses API 產生結構化開場白
            resp = await self._responses_create(
                model=selected_llm,
                messages=messages,
                text_format={
                    "format": {
                        "type": "json_schema",
                        "name": "conversation_greeting",
                        "schema": greeting_schema,
                        "strict": True
                    }
                },
                max_output_tokens=300,
            )
            output_text = getattr(resp, "output_text", None)
            if not output_text:
                raise HTTPException(status_code=500, detail="LLM did not return output_text.")
            
            structured_greeting = json.loads(output_text)
            ai_greeting = structured_greeting.get("ai_response")
            initial_hint = structured_greeting.get("hint")
            translation = structured_greeting.get("translation")
            
            # 保存完整的結構化回覆
            messages.append({"role": "assistant", "content": structured_greeting})
            
            # 更新內存
            store.conversations_db[sid] = messages
            store.conversation_metadata[sid] = metadata
            
            # 使用新的保存邏輯
            store.save_conversation(sid, messages, metadata, is_archived=False)
            store.save_conversation(sid, messages, metadata, is_archived=True) # 同步 archived
            
            return {"sid": sid, "ai": ai_greeting, "hint": initial_hint, "translation": translation}
        except openai.APIError as e:
            print(f"OpenAI API error during conversation start: {e}")
            raise HTTPException(status_code=500, detail=f"LLM conversation start failed: {e.message}")
        except Exception as e:
            print(f"Error starting conversation: {e}")
            raise HTTPException(status_code=500, detail="Internal server error starting conversation.")

    async def next_turn(self, sid: str, user_text: str) -> Dict[str, Any]:
        if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            raise HTTPException(status_code=500, detail="OpenAI API Key not configured.")
        if sid not in store.conversations_db:
            # 嘗試從存檔加載
            messages, metadata = store.load_conversation(sid, is_archived=True)
            if not messages:
                raise HTTPException(status_code=404, detail="Session ID not found.")
            store.conversations_db[sid] = messages
            store.conversation_metadata[sid] = metadata
        
        messages = store.conversations_db[sid]
        metadata = store.conversation_metadata[sid]
        selected_llm = metadata.get("model") or model_registry.get("english", "llm", self.default_llm_model)
        level = metadata.get("level", "B1")
        
        messages.append({"role": "user", "content": user_text})

        # 為 Structured Outputs 添加特定的系統提示
        structured_system_prompt = f"""You are an English conversation partner. Please respond with:
1. A natural response to the user's message (ai_response)
2. A helpful hint for their next reply in English (hint)
3. A Chinese translation of your response (translation)

Keep responses appropriate for CEFR level {level}.
Always provide all three fields."""
        
        full_messages = [{"role": "system", "content": structured_system_prompt}]
        full_messages.extend(messages)
        
        conversation_schema = {
            "type": "object",
            "properties": {
                "ai_response": {"type": "string"},
                "hint": {"type": "string"},
                "translation": {"type": "string"}
            },
            "required": ["ai_response", "hint", "translation"],
        }
        
        try:
            resp = await self._responses_create(
                model=selected_llm,
                messages=full_messages,
                text_format={
                    "format": {
                        "type": "json_schema",
                        "name": "conversation_response",
                        "schema": conversation_schema,
                        "strict": True
                    }
                },
                max_output_tokens=400,
            )
            
            output_text = getattr(resp, "output_text", None)
            if not output_text:
                raise Exception("LLM did not return output_text.")
                
            parsed_response = json.loads(output_text)
            
            messages.append({"role": "assistant", "content": parsed_response})

            # 更新內存並使用新的保存邏輯
            store.conversations_db[sid] = messages
            store.conversation_metadata[sid] = metadata # metadata 在這裡是舊的，但 save 會更新 updated_at
            store.save_conversation(sid, messages, metadata, is_archived=False)
            store.save_conversation(sid, messages, metadata, is_archived=True)
            
            return parsed_response # 直接回傳整個結構化物件

        except Exception as e:
            print(f"Error in conversation turn (next_turn): {e}")
            raise HTTPException(status_code=500, detail=f"Conversation turn failed: {str(e)}")

    def list_archives(self) -> List[Dict[str, Any]]:
        # 改為直接從索引讀取，更可靠
        try:
            if not os.path.exists(INDEX_FILE):
                return []
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                index = json.load(f)
            
            archives = []
            all_conversations = index.get("archived", {})
            for sid, meta in all_conversations.items():
                 archives.append({
                    "sid": sid,
                    "title": meta.get("title", "N/A"),
                    "topic": meta.get("topic"),
                    "level": meta.get("level"),
                    "message_count": meta.get("message_count", 0),
                    "updated_at": meta.get("updated_at"),
                 })
            # 按更新時間排序
            archives.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return archives
        except Exception as e:
            print(f"Error listing archives from index: {e}")
            return []

    def get_archive_transcript(self, sid: str) -> Dict[str, Any]:
        if not os.path.exists(os.path.join(ARCHIVED_DIR, f"{sid}.json")):
            raise HTTPException(status_code=404, detail="Archived session ID not found.")
        
        messages, metadata = store.load_conversation(sid, is_archived=True)
        if not metadata:
            raise HTTPException(status_code=404, detail="Archived conversation data is corrupted or missing metadata.")
        
        # 提取結構化資訊
        transcript = []
        for i, message in enumerate(messages):
            role = message.get("role")
            content = message.get("content")
            if role not in ["user", "assistant"]:
                continue

            entry = {
                "speaker": "ai" if role == "assistant" else "user",
                "text": content, # 預設為原始 content
                "hint": None,
                "translation": None,
                "structured": False
            }
            
            # 檢查是否為結構化助理訊息
            if role == "assistant" and isinstance(content, dict) and "ai_response" in content:
                entry["text"] = content.get("ai_response", str(content)) # 確保 text 永遠是字串
                entry["hint"] = content.get("hint")
                entry["translation"] = content.get("translation")
                entry["structured"] = True
            
            transcript.append(entry)

        return {
            "sid": sid,
            "topic": metadata.get("topic"),
            "level": metadata.get("level"),
            "title": metadata.get("title"),
            "transcript": transcript
        }

    def end_conversation(self, sid: str) -> Dict[str, Any]:
        if sid not in store.archived_conversations_db:
            raise HTTPException(status_code=404, detail="Session ID not found in active or archived records.")
        transcript_entries = []
        history = store.archived_conversations_db.get(sid, [])
        for message in history:
            role = message.get("role")
            content = message.get("content")
            if role in ["user", "assistant"]:
                speaker = "ai" if role == "assistant" else "user"
                transcript_entries.append({"speaker": speaker, "text": content})
        metadata = store.archived_conversation_metadata.get(sid, {})
        response = {
            "sid": sid,
            "topic": metadata.get("topic"),
            "level": metadata.get("level"),
            "title": metadata.get("title"),
            "transcript": transcript_entries
        }
        if sid in store.conversations_db:
            store.conversations_db.pop(sid)
        if sid in store.conversation_metadata:
            store.conversation_metadata.pop(sid)
        if history and metadata:
            store.save_conversation(sid, history, metadata, is_archived=True)
        return response


english_core = EnglishCore()