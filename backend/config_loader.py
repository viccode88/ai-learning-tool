import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path


class ConfigLoader:
    """從 JSON 檔案載入並管理模型與端點配置"""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            base_dir = Path(__file__).parent
            config_path = base_dir / "config" / "models.json"
        
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._mtime: Optional[float] = None
        self._load_config()

    def _load_config(self) -> None:
        """載入配置檔案"""
        try:
            if self.config_path.exists():
                mtime = self.config_path.stat().st_mtime
                if self._mtime is None or mtime != self._mtime:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        self._config = json.load(f)
                    self._mtime = mtime
            else:
                # 如果配置檔不存在，使用預設配置
                self._config = self._get_default_config()
                self._save_config()
        except Exception as e:
            print(f"載入配置檔案失敗: {e}")
            self._config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """取得預設配置"""
        return {
            "endpoints": [
                {
                    "id": "openai",
                    "name": "OpenAI",
                    "base_url": "https://api.openai.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "enabled": True
                }
            ],
            "models": {
                "llm": [
                    {"id": "gpt-4o", "name": "GPT-4o", "endpoint": "openai", "enabled": True},
                    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "endpoint": "openai", "enabled": True},
                    {"id": "gpt-5", "name": "GPT-5", "endpoint": "openai", "enabled": True},
                    {"id": "gpt-5-mini", "name": "GPT-5 Mini", "endpoint": "openai", "enabled": True},
                    {"id": "o1", "name": "O1", "endpoint": "openai", "enabled": True},
                    {"id": "o1-mini", "name": "O1 Mini", "endpoint": "openai", "enabled": True},
                    {"id": "o3-mini", "name": "O3 Mini", "endpoint": "openai", "enabled": True}
                ],
                "tts": [
                    {
                        "id": "tts-1",
                        "name": "TTS-1",
                        "endpoint": "openai",
                        "enabled": True,
                        "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
                    },
                    {
                        "id": "tts-1-hd",
                        "name": "TTS-1 HD",
                        "endpoint": "openai",
                        "enabled": True,
                        "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
                    }
                ]
            },
            "defaults": {
                "english": {
                    "llm": "gpt-5-mini",
                    "tts": "tts-1",
                    "tts_voice": "alloy"
                },
                "math": {
                    "llm": "gpt-5-mini"
                }
            },
            "last_selected": {}
        }

    def _save_config(self) -> None:
        """儲存配置到檔案"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            self._mtime = self.config_path.stat().st_mtime
        except Exception as e:
            print(f"儲存配置檔案失敗: {e}")

    def reload(self) -> None:
        """重新載入配置"""
        self._mtime = None
        self._load_config()

    # --- 查詢端點 ---
    def get_endpoints(self) -> List[Dict[str, Any]]:
        """取得所有端點"""
        self._load_config()
        return self._config.get("endpoints", [])

    def get_endpoint(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """取得特定端點"""
        endpoints = self.get_endpoints()
        return next((ep for ep in endpoints if ep["id"] == endpoint_id), None)

    # --- 查詢模型 ---
    def get_models(self, model_type: str = "llm") -> List[Dict[str, Any]]:
        """取得特定類型的所有模型"""
        self._load_config()
        models = self._config.get("models", {}).get(model_type, [])
        return [m for m in models if m.get("enabled", True)]

    def get_model(self, model_id: str, model_type: str = "llm") -> Optional[Dict[str, Any]]:
        """取得特定模型"""
        models = self.get_models(model_type)
        return next((m for m in models if m["id"] == model_id), None)

    # --- 查詢預設值 ---
    def get_defaults(self, feature: str) -> Dict[str, str]:
        """取得特定功能的預設模型"""
        self._load_config()
        return self._config.get("defaults", {}).get(feature, {})

    # --- 查詢/更新最後一次選擇 ---
    def get_last_selected(self, feature: str) -> Dict[str, str]:
        """取得特定功能最後一次選擇的模型（若無則回傳空 dict）"""
        self._load_config()
        return self._config.get("last_selected", {}).get(feature, {})

    def set_last_selected(self, feature: str, selection: Dict[str, str]) -> bool:
        """設定特定功能的最後一次選擇的模型（只更新提供的鍵）"""
        try:
            self._load_config()
            if "last_selected" not in self._config:
                self._config["last_selected"] = {}
            current = dict(self._config["last_selected"].get(feature, {}))
            for k, v in selection.items():
                if v is not None:
                    current[k] = v
            self._config["last_selected"][feature] = current
            self._save_config()
            return True
        except Exception as e:
            print(f"設定最後一次選擇失敗: {e}")
            return False

    # --- 更新端點 ---
    def add_endpoint(self, endpoint: Dict[str, Any]) -> bool:
        """新增端點"""
        try:
            self._load_config()
            endpoints = self._config.get("endpoints", [])
            # 檢查 ID 是否已存在
            if any(ep["id"] == endpoint["id"] for ep in endpoints):
                return False
            endpoints.append(endpoint)
            self._config["endpoints"] = endpoints
            self._save_config()
            return True
        except Exception as e:
            print(f"新增端點失敗: {e}")
            return False

    def update_endpoint(self, endpoint_id: str, endpoint_data: Dict[str, Any]) -> bool:
        """更新端點"""
        try:
            self._load_config()
            endpoints = self._config.get("endpoints", [])
            for i, ep in enumerate(endpoints):
                if ep["id"] == endpoint_id:
                    endpoints[i] = {**ep, **endpoint_data, "id": endpoint_id}
                    self._config["endpoints"] = endpoints
                    self._save_config()
                    return True
            return False
        except Exception as e:
            print(f"更新端點失敗: {e}")
            return False

    def delete_endpoint(self, endpoint_id: str) -> bool:
        """刪除端點"""
        try:
            self._load_config()
            endpoints = self._config.get("endpoints", [])
            self._config["endpoints"] = [ep for ep in endpoints if ep["id"] != endpoint_id]
            self._save_config()
            return True
        except Exception as e:
            print(f"刪除端點失敗: {e}")
            return False

    # --- 更新模型 ---
    def add_model(self, model_type: str, model: Dict[str, Any]) -> bool:
        """新增模型"""
        try:
            self._load_config()
            if "models" not in self._config:
                self._config["models"] = {}
            if model_type not in self._config["models"]:
                self._config["models"][model_type] = []
            
            models = self._config["models"][model_type]
            # 檢查 ID 是否已存在
            if any(m["id"] == model["id"] for m in models):
                return False
            models.append(model)
            self._save_config()
            return True
        except Exception as e:
            print(f"新增模型失敗: {e}")
            return False

    def update_model(self, model_type: str, model_id: str, model_data: Dict[str, Any]) -> bool:
        """更新模型"""
        try:
            self._load_config()
            models = self._config.get("models", {}).get(model_type, [])
            for i, m in enumerate(models):
                if m["id"] == model_id:
                    models[i] = {**m, **model_data, "id": model_id}
                    self._config["models"][model_type] = models
                    self._save_config()
                    return True
            return False
        except Exception as e:
            print(f"更新模型失敗: {e}")
            return False

    def delete_model(self, model_type: str, model_id: str) -> bool:
        """刪除模型"""
        try:
            self._load_config()
            models = self._config.get("models", {}).get(model_type, [])
            self._config["models"][model_type] = [m for m in models if m["id"] != model_id]
            self._save_config()
            return True
        except Exception as e:
            print(f"刪除模型失敗: {e}")
            return False

    # --- 更新預設值 ---
    def set_defaults(self, feature: str, defaults: Dict[str, str]) -> bool:
        """設定特定功能的預設模型"""
        try:
            self._load_config()
            if "defaults" not in self._config:
                self._config["defaults"] = {}
            self._config["defaults"][feature] = defaults
            self._save_config()
            return True
        except Exception as e:
            print(f"設定預設值失敗: {e}")
            return False


# 全域實例
config_loader = ConfigLoader()

