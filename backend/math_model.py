from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from enum import Enum

# --- 枚舉 ---

class MathDomain(str, Enum):
    NUMBERS_OPERATIONS = "數與運算基礎"
    ALGEBRA_FUNCTIONS = "代數與函數"
    GEOMETRY_VECTORS = "幾何與向量"
    TRIGONOMETRY = "三角學"
    CALCULUS = "微積分初步"
    STATISTICS_PROBABILITY = "數據分析與機率"
    LINEAR_ALGEBRA = "線性代數初步"

class DifficultyLevel(str, Enum):
    BASIC = "基礎"
    INTERMEDIATE = "中等"
    ADVANCED = "進階"

# --- 核心資料結構 ---

class SolutionStep(BaseModel):
    step_number: int = Field(description="步驟編號")
    description: str = Field(description="步驟描述")
    reasoning: str = Field(description="推理過程")
    calculation: Optional[str] = Field(None, description="計算過程")
    key_insight: Optional[str] = Field(None, description="關鍵洞察")
    
class MathSolution(BaseModel):
    problem: str = Field(description="原問題")
    domain: str = Field(description="數學領域")
    relevant_concepts: List[str] = Field(description="相關概念")
    solution_approach: str = Field(description="解題方法概述")
    steps: List[SolutionStep] = Field(description="詳細解題步驟")
    final_answer: str = Field(description="最終答案")
    verification: Optional[str] = Field(None, description="驗證過程")
    alternative_methods: Optional[List[str]] = Field(None, description="其他可能的解法")

# --- API 請求模型 ---

class MathProblem(BaseModel):
    problem: str = Field(description="數學問題描述")
    domain: Optional[MathDomain] = Field(None, description="數學領域")
    difficulty: Optional[DifficultyLevel] = Field(None, description="難度等級")
    specific_concepts: Optional[List[str]] = Field(None, description="涉及的具體概念")
    session_id: Optional[str] = Field(None, description="對話ID，用於追蹤長期對話。如果為空，將創建新對話。")

class ConceptRequest(BaseModel):
    concept_name: str = Field(description="概念名稱")
    domain: Optional[str] = Field(None, description="數學領域")
    session_id: Optional[str] = Field(None, description="對話ID，用於追蹤長期對話")

class QuestionRequest(BaseModel):
    session_id: str = Field(description="對話ID")
    question: str = Field(description="針對解題過程的問題")
    step_number: Optional[int] = Field(None, description="針對的步驟編號")
    context: Optional[str] = Field(None, description="問題背景")

class ImageMathProblem(BaseModel):
    domain: Optional[MathDomain] = Field(None, description="數學領域")
    difficulty: Optional[DifficultyLevel] = Field(None, description="難度等級")
    specific_concepts: Optional[List[str]] = Field(None, description="涉及的具體概念")
    additional_context: Optional[str] = Field(None, description="額外說明或背景")
    session_id: Optional[str] = Field(None, description="對話ID，用於追蹤長期對話")

# --- API 回應模型 ---

class MathSolutionResponse(BaseModel):
    session_id: str = Field(description="本次對話的ID，前端需保存並在後續請求中帶上")
    solution: MathSolution

class ConversationInfo(BaseModel):
    session_id: str = Field(description="對話ID")
    title: str = Field(description="對話標題")
    created_at: str = Field(description="創建時間")
    updated_at: str = Field(description="最後更新時間")

class ConceptExplanation(BaseModel):
    concept_name: str = Field(description="概念名稱")
    domain: str = Field(description="所屬領域")
    explanation: str = Field(description="概念解釋")
    key_points: List[str] = Field(description="關鍵要點")
    examples: List[str] = Field(description="應用例子")
    additional_context: Optional[str] = Field(None, description="額外說明或背景")
    session_id: Optional[str] = Field(None, description="對話ID，用於追蹤長期對話")

# --- 內部檢查模型 ---

class ProblemClarityResponse(BaseModel):
    is_clear: bool = Field(description="問題是否描述清楚")
    issue_type: str = Field(description="問題類型")
    specific_issues: List[str] = Field(description="具體問題點")
    suggestions: List[str] = Field(description="改善建議")

class ReasonableMathCheck(BaseModel):
    """用於 gpt-5-mini 判斷是否為合理數學問題的結構"""
    is_reasonable_math_question: bool = Field(description="輸入是否為合理的數學問題（寬鬆判定）")
    reason: str = Field(description="判斷的簡要理由")