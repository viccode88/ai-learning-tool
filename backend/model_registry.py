import os
from typing import Dict, Optional


class ModelRegistry:
    """簡單的記憶體模型註冊器，可按功能(feature)儲存/讀取目前選擇的模型。

    features 範例：
      - english: { llm, tts, tts_voice }
      - math: { llm }
    """

    def __init__(self) -> None:
        # 預設值，可由環境變數覆蓋
        default_llm = os.getenv("DEFAULT_LLM_MODEL", "gpt-5-mini")
        default_tts = os.getenv("DEFAULT_TTS_MODEL", "tts-1")
        default_voice = os.getenv("DEFAULT_TTS_VOICE", "alloy")

        self._by_feature: Dict[str, Dict[str, str]] = {
            "english": {
                "llm": default_llm,
                "tts": default_tts,
                "tts_voice": default_voice,
            },
            "math": {
                "llm": default_llm,
            },
        }

    # --- 查詢 ---
    def get(self, feature: str, key: str, fallback: Optional[str] = None) -> Optional[str]:
        return self._by_feature.get(feature, {}).get(key, fallback)

    def get_feature_config(self, feature: str) -> Dict[str, str]:
        return dict(self._by_feature.get(feature, {}))

    def get_all(self) -> Dict[str, Dict[str, str]]:
        return {
            feature: dict(cfg) for feature, cfg in self._by_feature.items()
        }

    # --- 設定 ---
    def set_models(
        self,
        feature: str,
        llm: Optional[str] = None,
        tts: Optional[str] = None,
        tts_voice: Optional[str] = None,
    ) -> Dict[str, str]:
        if feature not in self._by_feature:
            self._by_feature[feature] = {}
        if llm:
            self._by_feature[feature]["llm"] = llm
        if tts:
            self._by_feature[feature]["tts"] = tts
        if tts_voice:
            self._by_feature[feature]["tts_voice"] = tts_voice
        return dict(self._by_feature[feature])


model_registry = ModelRegistry()



