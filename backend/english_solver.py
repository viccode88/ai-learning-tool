import os
import uuid
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

import openai
from fastapi import HTTPException


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
        self.conversations_db: Dict[str, List[Dict[str, str]]] = {}
        self.conversation_metadata: Dict[str, Dict[str, Any]] = {}
        self.archived_conversations_db: Dict[str, List[Dict[str, str]]] = {}
        self.archived_conversation_metadata: Dict[str, Dict[str, Any]] = {}
        self.load_conversations()

    # --- 檔案 I/O ---
    def save_conversation(self, sid: str, messages: List[Dict[str, str]], metadata: Dict[str, Any], is_archived: bool = False):
        try:
            target_dir = ARCHIVED_DIR if is_archived else CONVERSATIONS_DIR
            conversation_file = os.path.join(target_dir, f"{sid}.json")
            conversation_data = {
                "sid": sid,
                "metadata": metadata,
                "messages": messages,
                "created_at": metadata.get("created_at", datetime.now().isoformat()),
                "updated_at": datetime.now().isoformat()
            }
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)

            self.update_conversation_index(sid, metadata, is_archived)
        except Exception as e:
            print(f"保存會話 {sid} 時發生錯誤: {e}")

    def update_conversation_index(self, sid: str, metadata: Dict[str, Any], is_archived: bool = False):
        try:
            if os.path.exists(INDEX_FILE):
                with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                    index = json.load(f)
            else:
                index = {"active": {}, "archived": {}}

            index_entry = {
                "title": metadata.get("title", "Unknown"),
                "topic": metadata.get("topic", ""),
                "level": metadata.get("level", ""),
                "created_at": metadata.get("created_at", datetime.now().isoformat()),
                "updated_at": datetime.now().isoformat(),
                "message_count": len(self.conversations_db.get(sid, [])) if not is_archived else len(self.archived_conversations_db.get(sid, []))
            }

            if is_archived:
                index["archived"][sid] = index_entry
                index["active"].pop(sid, None)
            else:
                index["active"][sid] = index_entry

            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"更新索引時發生錯誤: {e}")

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
        self.default_llm_model = "gpt-4o-mini"
        self.default_tts_model = "tts-1"
        self.default_tts_voice = "alloy"
        self.available_llm_models_info = {
            "gpt-4o": {"version": "latest", "rate_limit": "standard"},
            "gpt-4.1": {"version": "latest", "rate_limit": "standard"},
            "gpt-o4-mini": {"version": "latest", "rate_limit": "standard"},
            "gpt-3.5-turbo": {"version": "latest", "rate_limit": "standard"},
        }
        self.available_tts_models_info = {
            "tts-1": {"version": "latest", "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"], "speeds": ["slow", "normal"]},
            "tts-1-hd": {"version": "latest", "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"], "speeds": ["slow", "normal"]},
        }

    # --- 對外暴露的操作邏輯（供 API 呼叫） ---
    async def tts(self, text: str, voice: Optional[Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]] = None, speed: Optional[Literal["slow", "normal"]] = "normal", model: Optional[str] = None) -> bytes:
        if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            raise HTTPException(status_code=500, detail="OpenAI API Key not configured.")
        selected_tts_model = model if model and model in self.available_tts_models_info else self.default_tts_model
        selected_voice = voice if voice else self.default_tts_voice
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
        selected_llm = model if model and model in self.available_llm_models_info else self.default_llm_model
        messages = [
            {"role": "system", "content": f"""You are an English learning assistant. Analyze the user's query and provide detailed information.
Determine if the query is a single word, a phrase, a sentence, or a grammar question.
Target CEFR level for examples and explanations: {level if level else 'B1 (default)'}.
Respond in the JSON format specified by the 'english_query_tool' function.
If providing IPA, use standard IPA notation.
If providing an audio_url, it should be a placeholder or a link to a pre-generated audio for common words if available (for this demo, always return null for audio_url from this endpoint).
For 'grammar_tips', provide concise and useful information related to the query.
If the query is a sentence, provide its translation into Traditional Chinese and highlight grammar points.
If the query is a phrase, explain its meaning and usage.
If the query is a word, provide definitions (with part of speech), IPA, and example sentences.
If unsure about the type, classify as 'unknown' and provide a general helpful response or ask for clarification.
"""},
            {"role": "user", "content": q}
        ]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "english_query_tool",
                    "description": "Processes an English learning query and returns structured information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["word", "phrase", "sentence", "grammar_explanation", "unknown"]},
                            "query": {"type": "string"},
                            "definitions": {"type": "array", "items": {"type": "object", "properties": {"pos": {"type": "string"}, "text": {"type": "string"}}, "required": ["text"]}},
                            "ipa": {"type": "string"},
                            "examples": {"type": "array", "items": {"type": "object", "properties": {"text": {"type": "string"}, "level": {"type": "string"}}, "required": ["text"]}},
                            "translation": {"type": "string"},
                            "grammar_tips": {"type": "string"},
                            "audio_url": {"type": "string"}
                        },
                        "required": ["type", "query"]
                    }
                }
            }
        ]
        try:
            completion = await client.chat.completions.create(
                model=selected_llm,
                messages=messages,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "english_query_tool"}},
                temperature=0.3,
            )
            response_message = completion.choices[0].message
            tool_calls = response_message.tool_calls
            if tool_calls:
                function_args = json.loads(tool_calls[0].function.arguments)
                function_args.setdefault("audio_url", None)
                return function_args
            return {"type": "unknown", "query": q, "grammar_tips": "Could not process the query as expected. The LLM did not return a structured response."}
        except openai.APIError as e:
            print(f"OpenAI API error during query: {e}")
            raise HTTPException(status_code=500, detail=f"LLM query failed: {e.message}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error from LLM response: {e}")
            raise HTTPException(status_code=500, detail="Error decoding LLM response.")
        except Exception as e:
            print(f"Error in smart_query: {e}")
            raise HTTPException(status_code=500, detail="Internal server error during query processing.")

    async def start_conversation(self, topic: str, level: str, model: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
        if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            raise HTTPException(status_code=500, detail="OpenAI API Key not configured.")
        sid = str(uuid.uuid4())
        selected_llm = model if model and model in self.available_llm_models_info else self.default_llm_model
        conversation_title = title if title else f"{topic} ({level}) - Practice"
        initial_system_prompt = f"""You are an AI English conversation partner.
The user wants to practice a conversation about "{topic}" at CEFR level {level}.
Start the conversation with a welcoming message and a first question or statement related to the topic.
Provide a brief, one-sentence hint for the user's first response.
Keep your responses concise and appropriate for the {level} level.
Avoid complex vocabulary or grammar unless specifically requested or appropriate for a higher level practice.
Your goal is to help the user practice speaking English in a natural way.
"""
        messages = [{"role": "system", "content": initial_system_prompt}]
        try:
            completion = await client.chat.completions.create(
                model=selected_llm,
                messages=messages,
                temperature=0.7,
                max_completion_tokens=150
            )
            ai_response_content = completion.choices[0].message.content.strip()
            ai_greeting = ai_response_content
            initial_hint = f"Try to respond to the AI's greeting about {topic}."
            messages.append({"role": "assistant", "content": ai_greeting})
            store.conversations_db[sid] = messages
            store.conversation_metadata[sid] = {"topic": topic, "level": level, "model": selected_llm, "title": conversation_title, "created_at": datetime.now().isoformat()}
            store.archived_conversations_db[sid] = list(messages)
            store.archived_conversation_metadata[sid] = dict(store.conversation_metadata[sid])
            store.save_conversation(sid, messages, store.conversation_metadata[sid], is_archived=False)
            store.save_conversation(sid, list(messages), dict(store.conversation_metadata[sid]), is_archived=True)
            return {"sid": sid, "ai": ai_greeting, "hint": initial_hint}
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
            raise HTTPException(status_code=404, detail="Session ID not found.")
        messages = store.conversations_db[sid]
        metadata = store.conversation_metadata[sid]
        selected_llm = metadata.get("model", self.default_llm_model)
        messages.append({"role": "user", "content": user_text})
        try:
            completion = await client.chat.completions.create(
                model=selected_llm,
                messages=list(messages),
                temperature=0.7,
                max_completion_tokens=200
            )
            ai_full_response = completion.choices[0].message.content.strip()
            ai_response_text = ai_full_response
            next_hint = "Think about what to say next."
            if "HINT:" in ai_full_response:
                parts = ai_full_response.split("HINT:", 1)
                ai_response_text = parts[0].strip()
                next_hint = parts[1].strip()
            elif "\nHint:" in ai_full_response:
                parts = ai_full_response.split("\nHint:", 1)
                ai_response_text = parts[0].strip()
                next_hint = parts[1].strip()
            messages.append({"role": "assistant", "content": ai_response_text})
            store.conversations_db[sid] = messages
            store.archived_conversations_db[sid] = list(messages)
            store.archived_conversation_metadata[sid] = dict(store.conversation_metadata[sid])
            store.save_conversation(sid, messages, store.conversation_metadata[sid], is_archived=False)
            store.save_conversation(sid, list(messages), dict(store.conversation_metadata[sid]), is_archived=True)
            return {"ai": ai_response_text, "hint": next_hint, "feedback": None}
        except openai.APIError as e:
            print(f"OpenAI API error during conversation turn: {e}")
            raise HTTPException(status_code=500, detail=f"LLM conversation turn failed: {e.message}")
        except Exception as e:
            print(f"Error in conversation turn: {e}")
            raise HTTPException(status_code=500, detail="Internal server error during conversation turn.")

    def list_archives(self) -> List[Dict[str, Any]]:
        archives = []
        for sid, metadata in store.archived_conversation_metadata.items():
            archives.append({
                "sid": sid,
                "title": metadata.get("title", "N/A"),
                "topic": metadata.get("topic"),
                "level": metadata.get("level"),
            })
        return archives

    def get_archive_transcript(self, sid: str) -> Dict[str, Any]:
        if sid not in store.archived_conversation_metadata:
            raise HTTPException(status_code=404, detail="Archived session ID not found.")
        messages, metadata = store.load_conversation(sid, is_archived=True)
        if not messages and not metadata:
            raise HTTPException(status_code=404, detail="Archived conversation data not found.")
        transcript = []
        for message in messages:
            role = message.get("role")
            content = message.get("content")
            if role in ["user", "assistant"]:
                speaker = "ai" if role == "assistant" else "user"
                transcript.append({"speaker": speaker, "text": content})
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


