import asyncio
import json
import os
import uuid
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

import openai
from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, Field
import base64
from io import BytesIO

# 以環境變數建立本模組專用的 OpenAI 客戶端，避免循環匯入
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

# --- 對話管理器 ---
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
    
    def get_last_solution(self, session_id: str) -> Optional['MathSolution']:
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

# --- 數學領域枚舉 ---
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

# --- 高中數學核心概念系統 ---
MATH_CONCEPTS = {
    "數與運算基礎": {
        "1.1 實數系統": [
            "實數與數線：學生理解實數的完備性，包含有理數、無理數的特質，能用區間描述範圍",
            "絕對值：理解絕對值的幾何意義（距離），會解絕對值方程式與不等式",
            "科學記號：能表達極大或極小的數，理解有效位數的概念",
            "指數與對數：理解指數律（包含分數指數、負指數）、認識常用對數(log)及自然對數(ln)、能解指數方程式與對數方程式、理解指數與對數互為反運算"
        ],
        "1.2 複數系統": [
            "複數的表示法：代數式(a+bi)、複數平面上的點",
            "複數運算：四則運算、絕對值（模長）的意義",
            "極式與棣美弗定理：複數的極式表示、n次方根"
        ]
    },
    "代數與函數": {
        "2.1 多項式": [
            "多項式運算：加減乘除、綜合除法",
            "因式分解：提公因式、乘法公式、十字交乘法",
            "餘式定理與因式定理：理解f(a)的意義",
            "勘根定理：用於判斷實根存在區間"
        ],
        "2.2 方程式與不等式": [
            "一元二次方程式：配方法、公式解、判別式",
            "多項式方程式：虛根成對性質、代數基本定理",
            "不等式：一次、二次、多項式不等式的解區間",
            "線性規劃：目標函數的極值問題"
        ],
        "2.3 函數概念": [
            "函數的定義：對應關係、定義域、值域",
            "函數的性質：奇偶性（圖形對稱性）、單調性（遞增遞減）、凹凸性、週期性",
            "函數的運算：合成函數、反函數"
        ],
        "2.4 基本函數類型": [
            "多項式函數：圖形特徵、極值",
            "有理函數：漸近線、不連續點",
            "指數函數與對數函數：成長與衰退模型、半衰期、複利計算",
            "三角函數：sin、cos、tan的定義與圖形、週期現象的數學模型、三角恆等式（和差角公式、倍角半角公式）"
        ]
    },
    "幾何與向量": {
        "3.1 平面向量": [
            "向量表示法：位置向量、分量表示",
            "向量運算：加減法、係數積、內積（點積）：計算夾角、判定垂直、正射影",
            "向量應用：平行與垂直判定、面積計算（行列式）"
        ],
        "3.2 空間概念": [
            "空間向量：三維向量運算、外積",
            "空間中的直線與平面：參數式、比例式、法向量、平面方程式、距離計算（點到直線、點到平面）"
        ],
        "3.3 解析幾何": [
            "直線方程式：斜率、點斜式、平行垂直關係",
            "圓方程式：標準式、切線",
            "圓錐曲線：拋物線、橢圓、雙曲線的標準式"
        ]
    },
    "三角學": {
        "4.1 三角比": [
            "銳角三角比：正弦、餘弦、正切的定義",
            "廣義角：弧度量、極坐標",
            "特殊角：30°、45°、60°、90°等角度的三角比值"
        ],
        "4.2 三角定理": [
            "正弦定理：處理任意三角形問題",
            "餘弦定理：已知三邊求角、已知兩邊夾角求第三邊",
            "三角測量：實際應用問題"
        ]
    },
    "微積分初步": {
        "5.1 極限概念": [
            "數列極限：收斂性、極限運算性質",
            "函數極限：連續性、不連續點類型",
            "無窮級數：等比級數求和"
        ],
        "5.2 微分": [
            "導數定義：極限定義、幾何意義（切線斜率）",
            "微分法則：基本公式（冪函數、三角函數、指對數函數）、四則運算法則、連鎖律",
            "導數應用：函數圖形分析（單調性、極值、凹凸性）、最佳化問題、邊際分析（經濟應用）"
        ],
        "5.3 積分": [
            "不定積分：反導函數概念",
            "定積分：黎曼和、微積分基本定理",
            "積分應用：面積計算、體積計算（旋轉體）、總變化量"
        ]
    },
    "數據分析與機率": {
        "6.1 統計": [
            "數據描述：集中趨勢：平均數、中位數、眾數、離散程度：全距、標準差、四分位距",
            "數據呈現：直方圖、盒狀圖、散布圖",
            "相關與迴歸：相關係數、最適直線"
        ],
        "6.2 機率": [
            "古典機率：樣本空間、事件",
            "條件機率：條件機率公式、獨立事件",
            "貝氏定理：機率的更新",
            "隨機變數：期望值、變異數、二項分布、幾何分布"
        ]
    },
    "線性代數初步": {
        "7.1 矩陣": [
            "矩陣運算：加減、係數積、矩陣相乘",
            "反方陣：二階反方陣的計算",
            "行列式：二階、三階行列式的計算與應用"
        ],
        "7.2 線性方程組": [
            "高斯消去法：解聯立方程式",
            "克拉瑪公式：使用行列式求解",
            "線性變換：平面上的線性變換、轉移矩陣"
        ]
    }
}

# --- Pydantic 模型定義 ---
class MathProblem(BaseModel):
    problem: str = Field(description="數學問題描述")
    domain: Optional[MathDomain] = Field(None, description="數學領域")
    difficulty: Optional[DifficultyLevel] = Field(None, description="難度等級")
    specific_concepts: Optional[List[str]] = Field(None, description="涉及的具體概念")
    session_id: Optional[str] = Field(None, description="對話ID，用於追蹤長期對話。如果為空，將創建新對話。")

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

class ConceptRequest(BaseModel):
    concept_name: str = Field(description="概念名稱")
    domain: Optional[str] = Field(None, description="數學領域")
    session_id: Optional[str] = Field(None, description="對話ID，用於追蹤長期對話")

class ConceptExplanation(BaseModel):
    concept_name: str = Field(description="概念名稱")
    domain: str = Field(description="所屬領域")
    explanation: str = Field(description="概念解釋")
    key_points: List[str] = Field(description="關鍵要點")
    examples: List[str] = Field(description="應用例子")
    additional_context: Optional[str] = Field(None, description="額外說明或背景")
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

class ProblemClarityResponse(BaseModel):
    is_clear: bool = Field(description="問題是否描述清楚")
    issue_type: str = Field(description="問題類型")
    specific_issues: List[str] = Field(description="具體問題點")
    suggestions: List[str] = Field(description="改善建議")

# --- 新增的 API 回應模型 ---
class MathSolutionResponse(BaseModel):
    session_id: str = Field(description="本次對話的ID，前端需保存並在後續請求中帶上")
    solution: MathSolution

class ConversationInfo(BaseModel):
    session_id: str = Field(description="對話ID")
    title: str = Field(description="對話標題")
    created_at: str = Field(description="創建時間")
    updated_at: str = Field(description="最後更新時間")

# --- 核心數學解題類 ---
class MathSolver:
    def __init__(self):
        self.model = "o4-mini"  # 統一使用 o4-mini
        
    async def solve_problem(self, problem: MathProblem) -> MathSolutionResponse:
        """
        解決數學問題的主要方法。
        如果 session_id 為空，則創建一個新的對話。
        """
        if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            raise HTTPException(status_code=500, detail="OpenAI API Key not configured.")
        
        session_id = problem.session_id or str(uuid.uuid4())
        is_new_conversation = not problem.session_id

        # 首先檢查問題描述是否清楚
        clarity_check = await self._check_problem_clarity(problem.problem)
        if not clarity_check.is_clear:
            # 如果問題描述不清楚，直接返回問題分析
            raise HTTPException(
                status_code=400, 
                detail={
                    "error_type": "問題描述不清",
                    "issue_type": clarity_check.issue_type,
                    "specific_issues": clarity_check.specific_issues,
                    "suggestions": clarity_check.suggestions
                }
            )
        
        # 構建系統提示詞
        system_prompt = self._build_system_prompt(problem)
        
        # 構建用戶請求
        user_prompt = self._build_user_prompt(problem)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 定義解題工具
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "solve_math_problem",
                    "description": "解決數學問題並提供詳細的步驟說明",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "problem": {"type": "string", "description": "原始問題"},
                            "domain": {"type": "string", "description": "數學領域"},
                            "relevant_concepts": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "相關的數學概念"
                            },
                            "solution_approach": {"type": "string", "description": "解題方法概述"},
                            "steps": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "step_number": {"type": "integer", "description": "步驟編號"},
                                        "description": {"type": "string", "description": "步驟描述"},
                                        "reasoning": {"type": "string", "description": "推理過程"},
                                        "calculation": {"type": "string", "description": "計算過程"},
                                        "key_insight": {"type": "string", "description": "關鍵洞察"}
                                    },
                                    "required": ["step_number", "description", "reasoning"]
                                }
                            },
                            "final_answer": {"type": "string", "description": "最終答案"},
                            "verification": {"type": "string", "description": "驗證過程"},
                            "alternative_methods": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "其他可能的解法"
                            }
                        },
                        "required": ["problem", "domain", "relevant_concepts", "solution_approach", "steps", "final_answer"]
                    }
                }
            }
        ]
        
        try:
            completion = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "solve_math_problem"}},
            )
            
            response_message = completion.choices[0].message
            tool_calls = response_message.tool_calls
            
            if tool_calls:
                tool_call = tool_calls[0]
                if tool_call.function.name == "solve_math_problem":
                    function_args = json.loads(tool_call.function.arguments)
                    solution = MathSolution(**function_args)
                    
                    # 生成標題並儲存對話
                    title = await self._generate_title(solution.problem) if is_new_conversation else None
                    conversation_manager.add_message(session_id, "user", problem, title=title)
                    conversation_manager.add_message(session_id, "assistant", solution)

                    return MathSolutionResponse(session_id=session_id, solution=solution)
            
            # 如果沒有使用工具調用，返回錯誤
            raise HTTPException(status_code=500, detail="AI 未能正確解析問題結構")
            
        except openai.APIError as e:
            print(f"OpenAI API error during math solving: {e}")
            raise HTTPException(status_code=500, detail=f"數學解題失敗: {e.message}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            raise HTTPException(status_code=500, detail="解析 AI 回應時發生錯誤")
        except Exception as e:
            print(f"Error in solve_problem: {e}")
            raise HTTPException(status_code=500, detail="解題過程中發生內部錯誤")
    
    async def _generate_title(self, problem_text: str) -> str:
        """為問題生成一個簡潔的標題"""
        system_prompt = "你是一個標題生成器。請為以下的數學問題生成一個簡潔、不超過15個字的中文標題。"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": problem_text}
        ]
        try:
            completion = await client.chat.completions.create(
                model="o4-mini",
                messages=messages,
                max_completion_tokens=40,
                temperature=0.2,
            )
            title = completion.choices[0].message.content.strip().replace("\"", "").replace("'", "")
            return title if title else "數學問題"
        except Exception as e:
            print(f"Error generating title: {e}")
            return "數學問題"  # Fallback title

    def _build_system_prompt(self, problem: MathProblem) -> str:
        """構建系統提示詞"""
        concepts_text = ""
        if problem.domain:
            domain_concepts = MATH_CONCEPTS.get(problem.domain.value, {})
            concepts_text = f"\n\n相關數學概念：\n"
            for section, concepts in domain_concepts.items():
                concepts_text += f"{section}:\n"
                for concept in concepts:
                    concepts_text += f"- {concept}\n"
        
        return f"""你是一位專業的高中數學教師和解題專家。你的任務是以最聰明、最優雅的方式解決數學問題。

解題原則：
1. 思考努力程度：HIGH - 深入分析問題，尋找最優解法
2. 避免硬算：優先使用巧妙的數學技巧、性質和定理
3. 條列式輸出：每個步驟都要清楚標號和說明
4. 詳細解釋：不僅要說怎麼做，更要說為什麼這樣做
5. 關鍵洞察：在每個重要步驟指出關鍵的數學洞察

解題風格：
- 首先識別問題的核心和關鍵特徵
- 尋找問題中的模式、對稱性或特殊性質
- 選擇最優雅簡潔的解法路徑
- 每步都要有清楚的數學邏輯
- 適當使用圖形或幾何直觀
- 最後要驗證答案的合理性

{concepts_text}

請使用 solve_math_problem 工具來結構化地回答問題。"""

    def _build_user_prompt(self, problem: MathProblem) -> str:
        """構建用戶請求提示詞"""
        prompt = f"請解決以下數學問題：\n\n{problem.problem}"
        
        if problem.domain:
            prompt += f"\n\n數學領域：{problem.domain.value}"
        
        if problem.difficulty:
            prompt += f"\n難度等級：{problem.difficulty.value}"
            
        if problem.specific_concepts:
            prompt += f"\n涉及概念：{', '.join(problem.specific_concepts)}"
        
        prompt += "\n\n請提供詳細的解題步驟，包括每一步的推理過程和關鍵洞察。"
        
        return prompt
    
    # ==============================================================================
    # ===== 以下是經過完善的 get_concept_explanation 方法 ===========================
    # ==============================================================================
    async def get_concept_explanation(self, request: ConceptRequest) -> ConceptExplanation:
        """獲取數學概念的詳細解釋，並以結構化方式解析回應"""
        if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            raise HTTPException(status_code=500, detail="OpenAI API Key not configured.")
        
        # 在本地知識庫中查找相關概念以提供上下文
        relevant_info = self._find_concept_info(request.concept_name, request.domain)
        
        system_prompt = f"""你是一位高中數學教師，專精於解釋數學概念。
你的任務是根據用戶請求的概念名稱，提供一個全面且結構化的解釋。
請使用 `explain_math_concept` 工具來格式化你的回答，確保包含定義、關鍵要點和範例。

相關背景資訊（如果找到的話）：
{relevant_info}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"請解釋數學概念：{request.concept_name}"}
        ]
        
        # 定義工具，強制AI進行結構化輸出
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "explain_math_concept",
                    "description": "提供一個數學概念的詳細結構化解釋。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "concept_name": {"type": "string", "description": "概念名稱"},
                            "domain": {"type": "string", "description": "所屬領域，例如：代數與函數、幾何與向量"},
                            "explanation": {"type": "string", "description": "對概念的詳細、易於理解的解釋"},
                            "key_points": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "總結該概念的關鍵要點列表"
                            },
                            "examples": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "展示概念應用的具體例子列表"
                            },
                            "additional_context": {"type": "string", "description": "任何額外的相關說明或與其他概念的聯繫"}
                        },
                        "required": ["concept_name", "domain", "explanation", "key_points", "examples"]
                    }
                }
            }
        ]
        
        try:
            completion = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "explain_math_concept"}},
                max_completion_tokens=1500
            )
            
            response_message = completion.choices[0].message
            tool_calls = response_message.tool_calls
            
            if tool_calls:
                tool_call = tool_calls[0]
                if tool_call.function.name == "explain_math_concept":
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # 使用從AI收到的結構化數據創建模型實例
                    explanation = ConceptExplanation(**function_args)
                    
                    # 如果有 session_id，將其添加到回應對象並保存對話紀錄
                    if request.session_id:
                        explanation.session_id = request.session_id
                        conversation_manager.add_message(request.session_id, "user", request)
                        conversation_manager.add_message(request.session_id, "assistant", explanation)
                    
                    return explanation

            # 如果AI未能按要求使用工具，則拋出錯誤
            raise HTTPException(status_code=500, detail="AI 未能生成結構化的概念解釋")
            
        except openai.APIError as e:
            print(f"OpenAI API error during concept explanation: {e}")
            raise HTTPException(status_code=500, detail=f"解釋概念失敗: {e.message}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error during concept explanation: {e}")
            raise HTTPException(status_code=500, detail="解析 AI 回應時發生錯誤")
        except Exception as e:
            print(f"Error in get_concept_explanation: {e}")
            raise HTTPException(status_code=500, detail="獲取概念解釋時發生內部錯誤")

    def _find_concept_info(self, concept_name: str, domain: Optional[str] = None) -> str:
        """在概念庫中查找相關資訊"""
        info_parts = []
        
        search_domains = [domain] if domain else MATH_CONCEPTS.keys()
        
        for domain_name in search_domains:
            if domain_name in MATH_CONCEPTS:
                domain_data = MATH_CONCEPTS[domain_name]
                for section, concepts in domain_data.items():
                    for concept in concepts:
                        if concept_name.lower() in concept.lower():
                            info_parts.append(f"{domain_name} - {section}: {concept}")
        
        return "\n".join(info_parts) if info_parts else "未找到相關概念資訊"
    
    async def answer_question(self, request: QuestionRequest) -> str:
        """回答關於解題過程的問題，並具備長期記憶"""
        history = conversation_manager.get_history(request.session_id)
        if not history:
            return "對話紀錄為空，無法回答問題。請先開始一個對話。"

        # 構建傳送給模型的對話歷史
        messages = [
            {"role": "system", "content": "你是一位專業的數學教師，請根據下面的對話紀錄和學生的新問題，提供清晰的回答。"}
        ]
        
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            
            # 將儲存的對話內容轉換為適合模型的格式
            text = ""
            if isinstance(content, dict):
                # 根據內容類型生成簡潔的文字描述
                if "problem" in content and "steps" in content: # MathSolution
                    text = f"你對問題 '{content.get('problem', '')}' 給出了詳細解答，最終答案是：{content.get('final_answer', '')}。"
                elif "problem" in content: # MathProblem
                    text = f"學生問了一個問題：{content.get('problem', '')}"
                elif "concept_name" in content and "explanation" in content: # ConceptExplanation
                    text = f"你解釋了概念 '{content.get('concept_name', '')}'。"
                elif "concept_name" in content: # ConceptRequest
                    text = f"學生詢問了概念 '{content.get('concept_name', '')}'。"
                elif "question" in content: # QuestionRequest (previous one)
                    text = f"學生問：'{content.get('question', '')}'"
                elif "answer" in content: # Previous answer
                    text = f"你的回答：'{content.get('answer', '')}'"
                else:
                    text = "..." # 省略複雜內容
            else:
                text = str(content)

            if role in ["user", "assistant"] and text:
                 messages.append({"role": role, "content": text})

        # 添加當前問題
        current_question_text = request.question
        if request.step_number:
            # 如果問題針對特定步驟，從歷史中找到最新的解法來提供上下文
            last_solution = conversation_manager.get_last_solution(request.session_id)
            if last_solution and 1 <= request.step_number <= len(last_solution.steps):
                step = last_solution.steps[request.step_number - 1]
                current_question_text += f" (這是針對解題步驟 {request.step_number} 的問題：'{step.description}')"
        
        if request.context:
            current_question_text += f" (額外背景資訊：'{request.context}')"

        messages.append({"role": "user", "content": current_question_text})
        
        try:
            completion = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=800
            )
            
            response = completion.choices[0].message.content.strip()
            
            # 將本次問答也記錄下來
            conversation_manager.add_message(request.session_id, "user", request)
            conversation_manager.add_message(request.session_id, "assistant", {"answer": response})
            
            return response
            
        except Exception as e:
            print(f"Error in answer_question: {e}")
            raise HTTPException(status_code=500, detail="回答問題時發生錯誤")

    async def _check_problem_clarity(self, problem_text: str) -> ProblemClarityResponse:
        """檢查數學問題描述是否清楚明確"""
        
        system_prompt = """你是一位數學問題分析專家。請分析數學問題的描述是否清楚明確。

評估標準：
1. 問題陳述是否完整
2. 數學符號是否正確使用
3. 條件是否充分
4. 目標是否明確
5. 語言表達是否清晰

如果問題描述不清楚，請指出具體問題並給出改善建議。"""

        user_prompt = f"請分析以下數學問題的描述清晰度：\n\n{problem_text}"

        # 定義檢查工具
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "analyze_problem_clarity",
                    "description": "分析數學問題描述的清晰度",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "is_clear": {"type": "boolean", "description": "問題是否描述清楚"},
                            "issue_type": {"type": "string", "description": "問題類型（如：缺少條件、目標不明確、語言模糊等）"},
                            "specific_issues": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "具體問題點"
                            },
                            "suggestions": {
                                "type": "array", 
                                "items": {"type": "string"},
                                "description": "改善建議"
                            }
                        },
                        "required": ["is_clear", "issue_type", "specific_issues", "suggestions"]
                    }
                }
            }
        ]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            completion = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "analyze_problem_clarity"}},
            )

            response_message = completion.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                tool_call = tool_calls[0]
                if tool_call.function.name == "analyze_problem_clarity":
                    function_args = json.loads(tool_call.function.arguments)
                    return ProblemClarityResponse(**function_args)

            # 如果沒有使用工具調用，默認認為問題清楚
            return ProblemClarityResponse(
                is_clear=True,
                issue_type="無問題",
                specific_issues=[],
                suggestions=[]
            )

        except Exception as e:
            print(f"Error in _check_problem_clarity: {e}")
            # 檢查失敗時，默認認為問題清楚，不阻礙解題流程
            return ProblemClarityResponse(
                is_clear=True,
                issue_type="檢查失敗",
                specific_issues=[],
                suggestions=[]
            )

    async def solve_image_problem(self, image_data: bytes, image_problem: ImageMathProblem) -> MathSolutionResponse:
        """解決圖片中的數學問題"""
        if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            raise HTTPException(status_code=500, detail="OpenAI API Key not configured.")
        
        # 修復：如果沒有提供 session_id，則生成一個新的
        session_id = image_problem.session_id or str(uuid.uuid4())
        is_new_conversation = not image_problem.session_id
        
        # 將圖片轉換為base64編碼
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # 構建系統提示詞
        system_prompt = self._build_image_system_prompt(image_problem)
        
        # 構建包含圖片的訊息
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user", 
                "content": [
                    {
                        "type": "text",
                        "text": self._build_image_user_prompt(image_problem)
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ]
        
        # 定義解題工具（與文字解題相同）
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "solve_math_problem",
                    "description": "解決數學問題並提供詳細的步驟說明",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "problem": {"type": "string", "description": "從圖片中識別的原始問題"},
                            "domain": {"type": "string", "description": "數學領域"},
                            "relevant_concepts": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "相關的數學概念"
                            },
                            "solution_approach": {"type": "string", "description": "解題方法概述"},
                            "steps": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "step_number": {"type": "integer", "description": "步驟編號"},
                                        "description": {"type": "string", "description": "步驟描述"},
                                        "reasoning": {"type": "string", "description": "推理過程"},
                                        "calculation": {"type": "string", "description": "計算過程"},
                                        "key_insight": {"type": "string", "description": "關鍵洞察"}
                                    },
                                    "required": ["step_number", "description", "reasoning"]
                                }
                            },
                            "final_answer": {"type": "string", "description": "最終答案"},
                            "verification": {"type": "string", "description": "驗證過程"},
                            "alternative_methods": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "其他可能的解法"
                            }
                        },
                        "required": ["problem", "domain", "relevant_concepts", "solution_approach", "steps", "final_answer"]
                    }
                }
            }
        ]
        
        try:
            completion = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "solve_math_problem"}},
                max_completion_tokens=3000
            )
            
            response_message = completion.choices[0].message
            tool_calls = response_message.tool_calls
            
            if tool_calls:
                tool_call = tool_calls[0]
                if tool_call.function.name == "solve_math_problem":
                    function_args = json.loads(tool_call.function.arguments)
                    solution = MathSolution(**function_args)
                    
                    # 生成標題並儲存對話（如果是新對話）
                    if is_new_conversation:
                        title = await self._generate_title(solution.problem)
                        conversation_manager.add_message(session_id, "user", image_problem, title=title)
                        conversation_manager.add_message(session_id, "assistant", solution)
                    elif session_id:  # 如果有現有的 session_id
                        conversation_manager.add_message(session_id, "user", image_problem)
                        conversation_manager.add_message(session_id, "assistant", solution)
                    
                    # 修復：確保返回有效的 session_id
                    return MathSolutionResponse(session_id=session_id, solution=solution)
            
            # 如果沒有使用工具調用，返回錯誤
            raise HTTPException(status_code=500, detail="AI 未能正確解析圖片中的問題結構")
            
        except openai.APIError as e:
            print(f"OpenAI API error during image math solving: {e}")
            raise HTTPException(status_code=500, detail=f"圖片數學解題失敗: {e.message}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            raise HTTPException(status_code=500, detail="解析 AI 回應時發生錯誤")
        except Exception as e:
            print(f"Error in solve_image_problem: {e}")
            raise HTTPException(status_code=500, detail="圖片解題過程中發生內部錯誤")    
    def _build_image_system_prompt(self, image_problem: ImageMathProblem) -> str:
        """構建圖片解題的系統提示詞"""
        concepts_text = ""
        if image_problem.domain:
            domain_concepts = MATH_CONCEPTS.get(image_problem.domain.value, {})
            concepts_text = f"\n\n相關數學概念：\n"
            for section, concepts in domain_concepts.items():
                concepts_text += f"{section}:\n"
                for concept in concepts:
                    concepts_text += f"- {concept}\n"
        
        return f"""你是一位專業的高中數學教師和解題專家，擅長從圖片中識別和解決數學問題。

圖片解題流程：
1. 仔細觀察並準確識別圖片中的數學問題、公式、圖形
2. 理解題目的完整陳述和所有給定條件
3. 以最聰明、最優雅的方式解決問題

解題原則：
1. 思考努力程度：HIGH - 深入分析問題，尋找最優解法
2. 避免硬算：優先使用巧妙的數學技巧、性質和定理
3. 條列式輸出：每個步驟都要清楚標號和說明
4. 詳細解釋：不僅要說怎麼做，更要說為什麼這樣做
5. 關鍵洞察：在每個重要步驟指出關鍵的數學洞察
6. 圖形理解：如果有圖形，要準確理解其幾何關係和數據

解題風格：
- 首先準確轉錄圖片中的問題內容
- 識別問題的核心和關鍵特徵
- 尋找問題中的模式、對稱性或特殊性質
- 選擇最優雅簡潔的解法路徑
- 每步都要有清楚的數學邏輯
- 充分利用圖形信息進行解題
- 最後要驗證答案的合理性

{concepts_text}

請仔細分析圖片中的數學問題，然後使用 solve_math_problem 工具來結構化地回答。"""

    def _build_image_user_prompt(self, image_problem: ImageMathProblem) -> str:
        """構建圖片解題的用戶請求提示詞"""
        prompt = "請分析這張圖片中的數學問題並提供詳細解答。"
        
        if image_problem.domain:
            prompt += f"\n\n預期數學領域：{image_problem.domain.value}"
        
        if image_problem.difficulty:
            prompt += f"\n預期難度等級：{image_problem.difficulty.value}"
            
        if image_problem.specific_concepts:
            prompt += f"\n可能涉及概念：{', '.join(image_problem.specific_concepts)}"

        if image_problem.additional_context:
            prompt += f"\n額外說明：{image_problem.additional_context}"
        
        prompt += "\n\n請提供：\n1. 準確識別的問題內容\n2. 詳細的解題步驟\n3. 每一步的推理過程和關鍵洞察"
        
        return prompt

# --- 全局數學解題器實例 ---
math_solver = MathSolver()

# --- 新增的API輔助函數 ---
def list_conversations() -> List[ConversationInfo]:
    """
    列出所有已保存的對話紀錄。
    此函數應在 FastAPI 中註冊為一個端點，例如 @app.get("/conversations/", response_model=List[ConversationInfo])
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

# --- 輔助函數 ---
def get_available_concepts() -> Dict[str, List[str]]:
    """獲取所有可用的數學概念"""
    result = {}
    for domain, sections in MATH_CONCEPTS.items():
        concepts = []
        for section, concept_list in sections.items():
            concepts.extend([f"{section}: {concept}" for concept in concept_list])
        result[domain] = concepts
    return result

def search_concepts(keyword: str) -> List[Dict[str, str]]:
    """搜索包含關鍵字的概念"""
    results = []
    for domain, sections in MATH_CONCEPTS.items():
        for section, concept_list in sections.items():
            for concept in concept_list:
                if keyword.lower() in concept.lower():
                    results.append({
                        "domain": domain,
                        "section": section,
                        "concept": concept
                    })
    return results