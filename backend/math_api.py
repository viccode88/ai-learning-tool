from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional

# 導入數學解題模塊
from math_solver import (
    MathProblem, MathSolution, ConceptRequest, ConceptExplanation, 
    QuestionRequest, MathDomain, DifficultyLevel, ImageMathProblem,
    math_solver, get_available_concepts, search_concepts,
    list_conversations, ConversationInfo, MathSolutionResponse
)

# --- API 端點定義 ---

def register_math_endpoints(app: FastAPI):
    """將數學解題端點註冊到主應用"""
    
    @app.get("/api/v1/math/conversations", response_model=List[ConversationInfo], tags=["Math"])
    async def list_math_conversations():
        """
        獲取所有已保存的數學解題對話列表，按更新時間降序排序。
        """
        try:
            return list_conversations()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"獲取對話列表失敗: {str(e)}")

    @app.post("/api/v1/math/solve", response_model=MathSolutionResponse, tags=["Math"])
    async def solve_math_problem(problem: MathProblem):
        """
        解決數學問題
        
        功能特點：
        - 統一使用 gpt-o4-mini 模型
        - 高思考努力程度
        - 條列式輸出解題步驟
        - 詳細解釋推理過程
        - 避免硬算，使用巧妙方法
        - 提供關鍵洞察
        """
        try:
            response = await math_solver.solve_problem(problem)
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"解題失敗: {str(e)}")
    
    @app.post("/api/v1/math/concept", response_model=ConceptExplanation, tags=["Math"])
    async def explain_concept(request: ConceptRequest):
        """
        解釋數學概念
        
        根據高中數學核心概念系統，提供詳細的概念解釋
        """
        try:
            explanation = await math_solver.get_concept_explanation(request)
            return explanation
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"概念解釋失敗: {str(e)}")
    
    @app.post("/api/v1/math/question", tags=["Math"])
    async def ask_question(request: QuestionRequest):
        """
        針對解題過程提問
        
        可以針對特定步驟或整體解題過程提出問題
        """
        try:
            answer = await math_solver.answer_question(request)
            return {"answer": answer}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"回答問題失敗: {str(e)}")
    
    @app.post("/api/v1/math/solve-image", response_model=MathSolutionResponse, tags=["Math"])
    async def solve_image_math_problem(
        image: UploadFile,
        domain: Optional[str] = None,
        difficulty: Optional[str] = None,
        specific_concepts: Optional[str] = None,
        additional_context: Optional[str] = None
    ):
        """
        解決圖片中的數學問題
        
        功能特點：
        - 支援多種圖片格式 (JPEG, PNG, WebP)
        - 使用 gpt-4o-mini 的視覺能力
        - 自動識別圖片中的數學問題
        - 提供與文字解題相同品質的詳細解答
        - 支援幾何圖形、函數圖表等複雜數學內容
        """
        try:
            # 檢查檔案類型
            if not image.content_type or not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="請上傳有效的圖片檔案")
            
            # 讀取圖片數據
            image_data = await image.read()
            
            # 處理可選參數
            domain_enum = None
            if domain:
                try:
                    domain_enum = MathDomain(domain)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"無效的數學領域: {domain}")
            
            difficulty_enum = None
            if difficulty:
                try:
                    difficulty_enum = DifficultyLevel(difficulty)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"無效的難度等級: {difficulty}")
            
            concepts_list = None
            if specific_concepts:
                concepts_list = [c.strip() for c in specific_concepts.split(',') if c.strip()]
            
            # 構建圖片問題對象
            image_problem = ImageMathProblem(
                domain=domain_enum,
                difficulty=difficulty_enum,
                specific_concepts=concepts_list,
                additional_context=additional_context
            )
            
            # 解決圖片問題
            response = await math_solver.solve_image_problem(image_data, image_problem)
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"圖片解題失敗: {str(e)}")
    
    @app.get("/api/v1/math/concepts", tags=["Math"])
    async def list_available_concepts():
        """
        獲取所有可用的數學概念
        
        按領域分類展示高中數學核心概念
        """
        try:
            concepts = get_available_concepts()
            return {"concepts": concepts}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"獲取概念列表失敗: {str(e)}")
    
    @app.get("/api/v1/math/concepts/search", tags=["Math"])
    async def search_math_concepts(keyword: str):
        """
        搜索數學概念
        
        根據關鍵字搜索相關的數學概念
        """
        try:
            results = search_concepts(keyword)
            return {"results": results, "total": len(results)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"搜索概念失敗: {str(e)}")
    
    @app.get("/api/v1/math/domains", tags=["Math"])
    async def list_math_domains():
        """
        獲取數學領域列表
        
        返回所有支援的數學領域和難度等級
        """
        try:
            domains = [domain.value for domain in MathDomain]
            difficulties = [level.value for level in DifficultyLevel]
            return {
                "domains": domains,
                "difficulty_levels": difficulties
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"獲取領域列表失敗: {str(e)}")
    
    @app.get("/api/v1/math/status", tags=["Math"])
    async def get_solver_status():
        """
        獲取解題器狀態
        
        返回當前解題器的狀態信息
        """
        try:
            has_current_solution = math_solver.current_solution is not None
            current_problem = None
            if has_current_solution:
                current_problem = {
                    "problem": math_solver.current_solution.problem,
                    "domain": math_solver.current_solution.domain,
                    "steps_count": len(math_solver.current_solution.steps)
                }
            
            return {
                "model": math_solver.model,
                "has_current_solution": has_current_solution,
                "current_problem": current_problem
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"獲取狀態失敗: {str(e)}")
    
    @app.get("/api/v1/math/info", tags=["Math"])
    async def get_api_info():
        """
        獲取數學解題API資訊
        
        返回API的詳細資訊，包括功能特點、支援領域等
        """
        try:
            return get_math_api_info()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"獲取API資訊失敗: {str(e)}")

# --- 使用範例 ---
class MathAPIUsageExample:
    """數學API使用範例"""
    
    @staticmethod
    def example_solve_problem():
        """解題範例"""
        return {
            "problem": "求解方程式 x² - 5x + 6 = 0",
            "domain": "代數與函數",
            "difficulty": "中等",
            "specific_concepts": ["一元二次方程式", "因式分解"]
        }
    
    @staticmethod
    def example_concept_request():
        """概念解釋範例"""
        return {
            "concept_name": "判別式",
            "domain": "代數與函數"
        }
    
    @staticmethod
    def example_question():
        """提問範例"""
        return {
            "question": "為什麼要使用判別式來判斷根的性質？",
            "step_number": 2,
            "context": "在解一元二次方程式的過程中"
        }

# --- 輔助函數 ---
def get_math_api_info():
    """獲取數學API資訊"""
    return {
        "name": "數學解題API",
        "version": "1.1.0",
        "description": "專業的高中數學問題解決系統",
        "features": [
            "使用 gpt-4o-mini 模型",
            "高思考努力程度",
            "條列式解題步驟",
            "詳細推理解釋",
            "智能解題方法",
            "概念查詢功能",
            "互動式問答",
            "圖片解題功能",
            "問題描述清晰度檢查"
        ],
        "supported_domains": [domain.value for domain in MathDomain],
        "supported_difficulties": [level.value for level in DifficultyLevel],
        "endpoints": [
            "POST /api/v1/math/solve - 解決數學問題（附描述清晰度檢查）",
            "POST /api/v1/math/solve-image - 解決圖片中的數學問題",
            "POST /api/v1/math/concept - 解釋數學概念", 
            "POST /api/v1/math/question - 針對解題過程提問",
            "GET /api/v1/math/conversations - 獲取數學解題對話列表",
            "GET /api/v1/math/concepts - 獲取所有概念",
            "GET /api/v1/math/concepts/search - 搜索概念",
            "GET /api/v1/math/domains - 獲取領域列表",
            "GET /api/v1/math/status - 獲取解題器狀態"
        ]
    } 