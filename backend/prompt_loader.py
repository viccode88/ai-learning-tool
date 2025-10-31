import os
import json
from typing import Any, Dict, Optional

_PROMPTS_CACHE: Dict[str, Any] = {}
_PROMPTS_MTIME: Optional[float] = None

def _get_prompts_path() -> str:
    base_dir = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(base_dir, "..", "prompts", "prompts.json"))
    return path

def _load_prompts_if_changed() -> None:
    global _PROMPTS_CACHE, _PROMPTS_MTIME
    path = _get_prompts_path()
    try:
        mtime = os.path.getmtime(path)
        if _PROMPTS_MTIME is None or mtime != _PROMPTS_MTIME or not _PROMPTS_CACHE:
            with open(path, 'r', encoding='utf-8') as f:
                _PROMPTS_CACHE = json.load(f)
            _PROMPTS_MTIME = mtime
    except FileNotFoundError:
        # 若找不到檔案，保持快取為空，呼叫者可提供 default
        _PROMPTS_CACHE = {}
        _PROMPTS_MTIME = None

def get_prompts() -> Dict[str, Any]:
    _load_prompts_if_changed()
    return _PROMPTS_CACHE

def _get_by_path(data: Dict[str, Any], path: str) -> Optional[Any]:
    cur: Any = data
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur

def get_prompt(path: str, default: Optional[str] = None, **kwargs: Any) -> str:
    """取得提示詞字串，支援 dot-path 與 format 參數替換。

    例如：get_prompt("math.solver_system", concepts_text="...")
    
    如果找不到提示詞且沒有提供 default 參數，會拋出 ValueError。
    """
    _load_prompts_if_changed()
    value = _get_by_path(_PROMPTS_CACHE, path)
    if value is None:
        if default is None:
            raise ValueError(f"Missing prompt: {path}")
        value = default
    if isinstance(value, str) and kwargs:
        try:
            return value.format(**kwargs)
        except Exception:
            # 若替換失敗，回退原字串避免中斷
            return value
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


