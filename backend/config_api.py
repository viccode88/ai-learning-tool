from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from config_loader import config_loader


def register_config_endpoints(app: FastAPI):
    """註冊配置管理 API 端點"""

    # ===== 端點管理 =====
    
    @app.get("/api/v1/config/endpoints", tags=["Config"])
    async def get_endpoints():
        """取得所有端點"""
        return {"endpoints": config_loader.get_endpoints()}

    class EndpointRequest(BaseModel):
        id: str
        name: str
        base_url: str
        api_key_env: str = ""
        enabled: bool = True

    @app.post("/api/v1/config/endpoints", tags=["Config"])
    async def add_endpoint(req: EndpointRequest):
        """新增端點"""
        endpoint = req.dict()
        success = config_loader.add_endpoint(endpoint)
        if not success:
            raise HTTPException(status_code=400, detail="端點 ID 已存在")
        return {"ok": True, "endpoint": endpoint}

    @app.put("/api/v1/config/endpoints/{endpoint_id}", tags=["Config"])
    async def update_endpoint(endpoint_id: str, req: EndpointRequest):
        """更新端點"""
        success = config_loader.update_endpoint(endpoint_id, req.dict(exclude_unset=True))
        if not success:
            raise HTTPException(status_code=404, detail="端點不存在")
        return {"ok": True}

    @app.delete("/api/v1/config/endpoints/{endpoint_id}", tags=["Config"])
    async def delete_endpoint(endpoint_id: str):
        """刪除端點"""
        success = config_loader.delete_endpoint(endpoint_id)
        if not success:
            raise HTTPException(status_code=404, detail="端點不存在")
        return {"ok": True}

    # ===== 模型管理 =====
    
    @app.get("/api/v1/config/models/{model_type}", tags=["Config"])
    async def get_models(model_type: str):
        """取得特定類型的所有模型"""
        return {"models": config_loader.get_models(model_type)}

    class ModelRequest(BaseModel):
        id: str
        name: str
        endpoint: str
        enabled: bool = True
        voices: Optional[List[str]] = None

    @app.post("/api/v1/config/models/{model_type}", tags=["Config"])
    async def add_model(model_type: str, req: ModelRequest):
        """新增模型"""
        model = req.dict(exclude_none=True)
        success = config_loader.add_model(model_type, model)
        if not success:
            raise HTTPException(status_code=400, detail="模型 ID 已存在")
        return {"ok": True, "model": model}

    @app.put("/api/v1/config/models/{model_type}/{model_id}", tags=["Config"])
    async def update_model(model_type: str, model_id: str, req: ModelRequest):
        """更新模型"""
        success = config_loader.update_model(model_type, model_id, req.dict(exclude_unset=True))
        if not success:
            raise HTTPException(status_code=404, detail="模型不存在")
        return {"ok": True}

    @app.delete("/api/v1/config/models/{model_type}/{model_id}", tags=["Config"])
    async def delete_model(model_type: str, model_id: str):
        """刪除模型"""
        success = config_loader.delete_model(model_type, model_id)
        if not success:
            raise HTTPException(status_code=404, detail="模型不存在")
        return {"ok": True}

    # ===== 預設值管理 =====
    
    @app.get("/api/v1/config/defaults/{feature}", tags=["Config"])
    async def get_defaults(feature: str):
        """取得特定功能的預設模型"""
        return {"defaults": config_loader.get_defaults(feature)}

    class DefaultsRequest(BaseModel):
        llm: Optional[str] = None
        tts: Optional[str] = None
        tts_voice: Optional[str] = None

    @app.put("/api/v1/config/defaults/{feature}", tags=["Config"])
    async def set_defaults(feature: str, req: DefaultsRequest):
        """設定特定功能的預設模型"""
        defaults = req.dict(exclude_none=True)
        success = config_loader.set_defaults(feature, defaults)
        if not success:
            raise HTTPException(status_code=500, detail="設定預設值失敗")
        return {"ok": True, "defaults": defaults}

    # ===== 配置重載 =====
    
    @app.post("/api/v1/config/reload", tags=["Config"])
    async def reload_config():
        """重新載入配置檔案"""
        config_loader.reload()
        return {"ok": True, "message": "配置已重新載入"}

