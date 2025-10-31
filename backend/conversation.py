import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


from math_model import MathSolution, ConversationInfo 

class ConversationManager:
    """管理長期對話紀錄，並將其保存到 JSON 檔案中"""
    def __init__(self, history_dir: str = "conversation_history"):
        self.history_dir = history_dir
        os.makedirs(self.history_dir, exist_ok=True)

    def _get_path(self, session_id: str) -> str:
        """獲取對話紀錄檔案的路徑"""
        return os.path.join(self.history_dir, f"{session_id}.json")

    def _read_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """讀取 JSON 檔案中的對話內容"""
        filepath = self._get_path(session_id)
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading conversation {session_id}: {e}")
            return None

    def _write_conversation(self, session_id: str, data: Dict[str, Any]):
        """將對話內容寫入 JSON 檔案"""
        filepath = self._get_path(session_id)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except IOError as e:
            print(f"Error writing conversation {session_id}: {e}")

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """獲取指定 session 的對話紀錄"""
        data = self._read_conversation(session_id)
        return data.get("history", []) if data else []

    def add_message(self, session_id: str, role: str, content: Any, title: Optional[str] = None):
        """向指定 session 添加一條訊息並保存"""
        data = self._read_conversation(session_id)
        now = datetime.now().isoformat()
        
        if data is None:
            # 這是新對話的第一條訊息
            data = {
                "session_id": session_id,
                "title": title or "新對話",
                "created_at": now,
                "history": []
            }

        content_to_store = content.dict() if isinstance(content, BaseModel) else content
        data["history"].append({
            "role": role,
            "content": content_to_store,
            "timestamp": now
        })
        data["updated_at"] = now
        
        self._write_conversation(session_id, data)
    
    def get_last_solution(self, session_id: str) -> Optional[MathSolution]:
        """獲取最近一次的解題方案"""
        history = self.get_history(session_id)
        for message in reversed(history):
            if message["role"] == "assistant":
                content = message["content"]
                # 檢查內容是否符合 MathSolution 的結構
                if isinstance(content, dict) and all(k in content for k in ["problem", "domain", "relevant_concepts", "steps", "final_answer"]):
                    try:
                        # 嘗試將字典轉換回 MathSolution 模型
                        return MathSolution(**content)
                    except Exception:
                        continue  # 如果轉換失敗，繼續尋找上一個
        return None

# 全局對話管理器實例
conversation_manager = ConversationManager()

# --- API 輔助函數 ---
def list_conversations() -> List[ConversationInfo]:
    """
    列出所有已保存的對話紀錄。
    """
    infos = []
    history_dir = conversation_manager.history_dir
    if not os.path.exists(history_dir):
        return []

    for filename in os.listdir(history_dir):
        if filename.endswith(".json"):
            try:
                filepath = os.path.join(history_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                infos.append(ConversationInfo(
                    session_id=data.get("session_id"),
                    title=data.get("title", "無標題"),
                    created_at=data.get("created_at"),
                    updated_at=data.get("updated_at"),
                ))
            except Exception as e:
                print(f"Error reading or parsing conversation file {filename}: {e}")
    
    # 按最後更新時間降序排序
    infos.sort(key=lambda x: x.updated_at, reverse=True)
    return infos