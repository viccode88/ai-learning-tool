# math_solver.py
# (已更新：包含 re-export 和輔助函式)

import asyncio
import json
import os
import uuid
import base64
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

import openai
from openai import OpenAI, AsyncOpenAI
from prompt_loader import get_prompt
from fastapi import HTTPException
from pydantic import BaseModel

# --- 匯入 Pydantic 模型 ---
from math_model import (
    MathProblem, ImageMathProblem, MathSolution, MathSolutionResponse,
    ConceptRequest, ConceptExplanation, QuestionRequest,
    ProblemClarityResponse, ReasonableMathCheck, MathDomain,
    DifficultyLevel, ConversationInfo 
)

# --- 匯入知識庫 ---
from knowledge_base import MATH_CONCEPTS

# --- 匯入對話管理 ---
# (匯入函式和實例)
from conversation import (
    conversation_manager, ConversationManager, 
    list_conversations as list_conversations_from_db
)
from model_registry import model_registry

# --- OpenAI 客戶端 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)


class MathSolver:
    def __init__(self):
        self.model = os.getenv("DEFAULT_LLM_MODEL", model_registry.get("math", "llm", "gpt-5"))
        self._define_schemas()

    def _define_schemas(self):
        """
        集中定義所有用於 Structured Outputs 的 JSON Schema
        """
        
        # 1. 數學解題 Schema (最複雜的)
        self.MATH_SOLUTION_SCHEMA = {
            "type": "object",
            "properties": {
                "is_math_question": {"type": "boolean", "description": "此輸入是否為數學題目（寬鬆判定）"},
                "problem": {"type": "string", "description": "原始問題（如果是圖片，請轉錄）"},
                "domain": {"type": "string", "description": "數學領域"},
                "relevant_concepts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "相關的數學概念"
                },
                "solution_approach": {"type": "string", "description": "解題方法概述"},
                "steps": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_number": {"type": "integer", "description": "步驟編號"},
                            "description": {"type": "string", "description": "步驟描述"},
                            "reasoning": {"type": "string", "description": "推理過程"},
                            "calculation": {"type": "string", "description": "計算過程"},
                            "key_insight": {"type": "string", "description": "關鍵洞察"}
                        },
                        "required": ["step_number", "description", "reasoning", "calculation", "key_insight"],
                        "additionalProperties": False
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
            "required": ["is_math_question", "problem", "domain", "relevant_concepts", "solution_approach", "steps", "final_answer", "verification", "alternative_methods"],
            "additionalProperties": False
        }

        # 2. 概念解釋 Schema
        self.CONCEPT_EXPLANATION_SCHEMA = {
            "type": "object",
            "properties": {
                "concept_name": {"type": "string", "description": "概念名稱"},
                "domain": {"type": "string", "description": "所屬領域"},
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
            "required": ["concept_name", "domain", "explanation", "key_points", "examples"],
            "additionalProperties": False
        }

        # 3. 問題清晰度 Schema
        self.CLARITY_CHECK_SCHEMA = {
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
            "required": ["is_clear", "issue_type", "specific_issues", "suggestions"],
            "additionalProperties": False
        }

        # 4. 合理性檢查 Schema (文字)
        self.REASONABLE_MATH_SCHEMA = {
            "type": "object",
            "properties": {
                "is_reasonable_math_question": {"type": "boolean", "description": "輸入是否為合理的數學問題（寬鬆判定）"},
                "reason": {"type": "string", "description": "判斷的簡要理由"}
            },
            "required": ["is_reasonable_math_question", "reason"],
            "additionalProperties": False
        }
        
        # 5. 圖片分類 Schema
        self.IMAGE_IS_MATH_SCHEMA = {
            "type": "object",
            "properties": {
                "is_math": {"type": "boolean"},
                "reason": {"type": "string"},
            },
            "required": ["is_math", "reason"],
            "additionalProperties": False
        }

    # --- 內部輔助函式 (Schema) ---
    def _get_math_solution_schema(self) -> Dict[str, Any]:
        return self.MATH_SOLUTION_SCHEMA

    def _get_concept_explanation_schema(self) -> Dict[str, Any]:
        return self.CONCEPT_EXPLANATION_SCHEMA

    def _get_clarity_check_schema(self) -> Dict[str, Any]:
        return self.CLARITY_CHECK_SCHEMA

    def _get_reasonable_math_schema(self) -> Dict[str, Any]:
        return self.REASONABLE_MATH_SCHEMA

    def _get_image_is_math_schema(self) -> Dict[str, Any]:
        return self.IMAGE_IS_MATH_SCHEMA

    # --- 內部輔助函式 (提示詞) ---
    def _build_system_prompt(self, problem: MathProblem) -> str:
        concepts_text = ""
        if problem.domain:
            domain_concepts = MATH_CONCEPTS.get(problem.domain.value, {})
            concepts_text = f"\n\n相關數學概念：\n"
            for section, concepts in domain_concepts.items():
                concepts_text += f"{section}:\n"
                for concept in concepts:
                    concepts_text += f"- {concept}\n"
        high_school_math_instructions = "\n\nHigh school mathematics:\n"
        for domain in MATH_CONCEPTS.keys():
            high_school_math_instructions += f"- {domain}\n"
        try:
            return get_prompt("math.solver_system", concepts_text=concepts_text, default=f"你是一位專業的高中數學教師... (省略，同原檔)")
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"缺少提示詞配置: {str(e)}")

    def _build_user_prompt(self, problem: MathProblem) -> str:
        domain_section = f"\n\n數學領域：{problem.domain.value}" if problem.domain else ""
        difficulty_section = f"\n難度等級：{problem.difficulty.value}" if problem.difficulty else ""
        specific_concepts_section = f"\n涉及概念：{', '.join(problem.specific_concepts)}" if problem.specific_concepts else ""
        try:
            return get_prompt("math.user_solve", problem=problem.problem, domain_section=domain_section, difficulty_section=difficulty_section, specific_concepts_section=specific_concepts_section, default=f"請解決以下數學問題：\n\n{problem.problem}...")
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"缺少提示詞配置: {str(e)}")

    def _build_image_system_prompt(self, image_problem: ImageMathProblem) -> str:
        concepts_text = ""
        if image_problem.domain:
            domain_concepts = MATH_CONCEPTS.get(image_problem.domain.value, {})
            concepts_text = f"\n\n相關數學概念：\n"
            for section, concepts in domain_concepts.items():
                concepts_text += f"{section}:\n"
                for concept in concepts:
                    concepts_text += f"- {concept}\n"
        high_school_math_instructions = "\n\nHigh school mathematics:\n"
        for domain in MATH_CONCEPTS.keys():
            high_school_math_instructions += f"- {domain}\n"
        try:
            return get_prompt("math.image_solver_system", concepts_text=concepts_text, default=f"你是一位專業的高中數學教師和解題專家，擅長從圖片中識別和解決數學問題... (省略，同原檔)")
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"缺少提示詞配置: {str(e)}")

    def _build_image_user_prompt(self, image_problem: ImageMathProblem) -> str:
        domain_section = f"\n\n預期數學領域：{image_problem.domain.value}" if image_problem.domain else ""
        difficulty_section = f"\n預期難度等級：{image_problem.difficulty.value}" if image_problem.difficulty else ""
        specific_concepts_section = f"\n可能涉及概念：{', '.join(image_problem.specific_concepts)}" if image_problem.specific_concepts else ""
        additional_context_section = f"\n額外說明：{image_problem.additional_context}" if image_problem.additional_context else ""
        try:
            return get_prompt("math.image_user_prompt", domain_section=domain_section, difficulty_section=difficulty_section, specific_concepts_section=specific_concepts_section, additional_context_section=additional_context_section, default="請分析這張圖片中的數學問題並提供詳細解答...")
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"缺少提示詞配置: {str(e)}")
    
    # --- 內部輔助函式 (AI 呼叫) ---
    async def _generate_title(self, problem_text: str) -> str:
        try:
            system_prompt = get_prompt("math.title_system", default="你是一個標題生成器。請為以下的數學問題生成一個簡潔、不超過15個字的中文標題。")
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"缺少提示詞配置: {str(e)}")
        messages = [
            {"role": "developer", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": problem_text}]}
        ]
        try:
            resp = await client.responses.create(
                model=model_registry.get("math", "llm", self.model), # 或是使用 gpt-5-mini
                input=messages,
                max_output_tokens=40,
            )
            title = getattr(resp, "output_text", None)
            if not title:
                return "數學問題"
            title = title.strip().replace("\"", "").replace("'", "")
            return title if title else "數學問題"
        except Exception as e:
            print(f"Error generating title: {e}")
            return "數學問題"

    def _find_concept_info(self, concept_name: str, domain: Optional[str] = None) -> str:
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

    # --- 預先分類 (重構) ---
    async def _classify_text_is_reasonable_math(self, problem_text: str) -> Optional[ReasonableMathCheck]:
        try:
            system_prompt = get_prompt("math.text_is_math_system")
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"缺少提示詞配置: {str(e)}")
        messages = [
            {"role": "developer", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": problem_text}]}
        ]
        try:
            resp = await client.responses.create(
                model="gpt-5-mini",
                input=messages,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "reasonable_math_check",
                        "schema": self._get_reasonable_math_schema(),
                        "strict": True
                    }
                },
                max_output_tokens=200,
            )
            output_text = getattr(resp, "output_text", None)
            if output_text:
                data = json.loads(output_text)
                return ReasonableMathCheck(**data)
        except Exception as e:
            print(f"Mini classifier failed: {e}")
        return None # 失敗時返回 None

    async def _classify_image_is_math(self, base64_image: str, context_text: Optional[str] = None) -> Optional[bool]:
        try:
            system_prompt = get_prompt("math.image_is_math_system")
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"缺少提示詞配置: {str(e)}")
        user_text = context_text or "Classify whether this image contains a math problem."
        messages = [
            {"role": "developer", "content": [{"type": "input_text", "text": system_prompt}]},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_text},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{base64_image}"},
                ],
            },
        ]
        try:
            resp = await client.responses.create(
                model=model_registry.get("math", "llm", self.model),
                input=messages,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "image_is_math",
                        "schema": self._get_image_is_math_schema(),
                        "strict": True
                    }
                },
                max_output_tokens=120,
            )
            output_text = getattr(resp, "output_text", None)
            if output_text:
                data = json.loads(output_text)
                return bool(data.get("is_math"))
        except Exception:
            return None # 失敗時返回 None

    # --- 統一的核心解題邏輯 (新) ---
    async def _solve(
        self,
        messages: List[Dict[str, Any]],
        session_id: str,
        problem_input: BaseModel, # (MathProblem or ImageMathProblem)
        is_new_conversation: bool
    ) -> MathSolutionResponse:
        """統一的解題核心函式"""
        
        try:
            # 轉換 messages 為 API 要求的格式
            input_payload: List[Dict[str, Any]] = []
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content")
                converted_role = "developer" if role == "system" else role
                
                if isinstance(content, list):
                    # 處理圖片和文字混合
                    converted_items = []
                    for item in content:
                        if item.get("type") == "text":
                            converted_items.append({"type": "input_text", "text": item.get("text", "")})
                        elif item.get("type") == "image_url":
                            converted_items.append({"type": "input_image", "image_url": item.get("image_url")})
                    input_payload.append({"role": converted_role, "content": converted_items})
                else:
                    # 處理純文字
                    input_payload.append({
                        "role": converted_role,
                        "content": [{"type": "input_text", "text": str(content)}]
                    })

            # 呼叫 OpenAI API
            resp = await client.responses.create(
                model=self.model,
                input=input_payload,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "math_solution",
                        "schema": self._get_math_solution_schema(),
                        "strict": True
                    },
                    "verbosity": "medium",
                },
                max_output_tokens=3500,
                reasoning={"effort": "medium", "summary": "auto"},
                store=True,
                include=[
                    "reasoning.encrypted_content",
                    "web_search_call.action.sources"
                ]
            )

            output_text = getattr(resp, "output_text", None)
            if not output_text:
                raise HTTPException(status_code=500, detail="AI 未能生成結構化解答")

            solution_data = json.loads(output_text)

            if not solution_data.get("is_math_question", True):
                raise HTTPException(status_code=400, detail="[NOT_MATH] 這不是一個數學問題。")

            solution_data.pop("is_math_question", None)
            solution = MathSolution(**solution_data)
            
            # 儲存到對話
            if is_new_conversation:
                title = await self._generate_title(solution.problem)
                conversation_manager.add_message(session_id, "user", problem_input, title=title)
                conversation_manager.add_message(session_id, "assistant", solution)
            else:
                conversation_manager.add_message(session_id, "user", problem_input)
                conversation_manager.add_message(session_id, "assistant", solution)

            return MathSolutionResponse(session_id=session_id, solution=solution)

        except HTTPException:
            raise
        except openai.APIError as e:
            print(f"OpenAI API error during math solving: {e}")
            raise HTTPException(status_code=500, detail=f"數學解題失敗: {e.message}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            raise HTTPException(status_code=500, detail="解析 AI 回應時發生錯誤")
        except Exception as e:
            print(f"Error in _solve: {e}")
            raise HTTPException(status_code=500, detail="解題過程中發生內部錯誤")

    # --- 公開 API 方法 (重構) ---

    async def solve_problem(self, problem: MathProblem) -> MathSolutionResponse:
        """(重構) 解決文字數學問題"""
        if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            raise HTTPException(status_code=500, detail="OpenAI API Key not configured.")
        
        session_id = problem.session_id or str(uuid.uuid4())
        is_new_conversation = not problem.session_id

        # 1. 預先分類
        classifier = await self._classify_text_is_reasonable_math(problem.problem)
        if classifier and not classifier.is_reasonable_math_question:
            raise HTTPException(status_code=400, detail=f"[NOT_MATH] 這不是合理的數學問題: {classifier.reason}")
        
        # 2. 構建提示詞
        system_prompt = self._build_system_prompt(problem)
        user_prompt = self._build_user_prompt(problem)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 3. 呼叫核心解題
        return await self._solve(messages, session_id, problem, is_new_conversation)

    async def solve_image_problem(self, image_data: bytes, image_problem: ImageMathProblem) -> MathSolutionResponse:
        """(重構) 解決圖片中的數學問題"""
        if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            raise HTTPException(status_code=500, detail="OpenAI API Key not configured.")
        
        session_id = image_problem.session_id or str(uuid.uuid4())
        is_new_conversation = not image_problem.session_id
        
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # 1. 預先分類
        is_math = await self._classify_image_is_math(base64_image, image_problem.additional_context)
        if is_math is False:
            raise HTTPException(status_code=400, detail="[NOT_MATH] 這張圖片看起來不是數學題。")

        # 2. 構建提示詞
        system_prompt = self._build_image_system_prompt(image_problem)
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": self._build_image_user_prompt(image_problem)},
                    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}
                ]
            }
        ]
        
        # 3. 呼叫核心解題
        return await self._solve(messages, session_id, image_problem, is_new_conversation)

    async def get_concept_explanation(self, request: ConceptRequest) -> ConceptExplanation:
        """(重構) 獲取數學概念的詳細解釋"""
        if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            raise HTTPException(status_code=500, detail="OpenAI API Key not configured.")
        
        relevant_info = self._find_concept_info(request.concept_name, request.domain)
        try:
            system_prompt = get_prompt("math.concept_explain_system", relevant_info=relevant_info, default=f"你是一位高中數學教師... (省略，同原檔)")
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"缺少提示詞配置: {str(e)}")
        
        messages = [
            {"role": "developer", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": f"請解釋數學概念：{request.concept_name}"}]}
        ]
        
        try:
            resp = await client.responses.create(
                model=self.model,
                input=messages,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "explain_math_concept",
                        "schema": self._get_concept_explanation_schema(),
                        "strict": True
                    }
                },
                max_output_tokens=3000,
            )
            
            output_text = getattr(resp, "output_text", None)
            if not output_text:
                raise HTTPException(status_code=500, detail="AI 未能生成結構化的概念解釋")

            explanation_data = json.loads(output_text)
            explanation = ConceptExplanation(**explanation_data)
            
            if request.session_id:
                explanation.session_id = request.session_id
                conversation_manager.add_message(request.session_id, "user", request)
                conversation_manager.add_message(request.session_id, "assistant", explanation)
            return explanation
            
        except Exception as e:
            print(f"Error in get_concept_explanation: {e}")
            raise HTTPException(status_code=500, detail="獲取概念解釋時發生內部錯誤")

    async def answer_question(self, request: QuestionRequest) -> str:
        """(重構) 回答關於解題過程的問題"""
        history = conversation_manager.get_history(request.session_id)
        if not history:
            return "對話紀錄為空，無法回答問題。"

        # 構建傳送給模型的對話歷史 
        try:
            answer_system_prompt = get_prompt("math.answer_question_system", default="你是一位專業的數學教師...")
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"缺少提示詞配置: {str(e)}")
        messages_for_api = [
            {"role": "developer", "content": [{"type": "input_text", "text": answer_system_prompt}]}
        ]
        
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            text = ""
            if isinstance(content, dict):
                if "problem" in content and "steps" in content:
                    text = f"你對問題 '{content.get('problem', '')}' 給出了詳細解答..."
                elif "problem" in content:
                    text = f"學生問了一個問題：{content.get('problem', '')}"
                elif "question" in content:
                    text = f"學生問：'{content.get('question', '')}'"
                elif "answer" in content:
                    text = f"你的回答：'{content.get('answer', '')}'"
                else:
                    text = "..."
            else:
                text = str(content)
            
            api_role = "user" if role == "user" else "assistant"
            if text:
                 messages_for_api.append({"role": api_role, "content": [{"type": "input_text", "text": text}]})

        # 添加當前問題
        current_question_text = request.question
        if request.step_number:
            last_solution = conversation_manager.get_last_solution(request.session_id)
            if last_solution and 1 <= request.step_number <= len(last_solution.steps):
                step = last_solution.steps[request.step_number - 1]
                current_question_text += f" (針對步驟 {request.step_number}：'{step.description}')"
        
        messages_for_api.append({"role": "user", "content": [{"type": "input_text", "text": current_question_text}]})
        
        try:
            resp = await client.responses.create(
                model=self.model,
                input=messages_for_api,
                max_output_tokens=3000,
            )
            response = getattr(resp, "output_text", None)
            if not response:
                raise HTTPException(status_code=500, detail="AI 未能生成回答")
            
            conversation_manager.add_message(request.session_id, "user", request)
            conversation_manager.add_message(request.session_id, "assistant", {"answer": response})
            
            return response
            
        except Exception as e:
            print(f"Error in answer_question: {e}")
            raise HTTPException(status_code=500, detail="回答問題時發生錯誤")

    async def _check_problem_clarity(self, problem_text: str) -> ProblemClarityResponse:
        """(重構) 檢查數學問題描述是否清楚明確"""
        try:
            system_prompt = get_prompt("math.clarity_check_system", default="你是一位數學問題分析專家...")
            user_prompt = get_prompt("math.clarity_check_user", problem_text=problem_text, default=f"請分析以下數學問題的描述清晰度：\n\n{problem_text}")
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"缺少提示詞配置: {str(e)}")

        messages = [
            {"role": "developer", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]}
        ]

        try:
            resp = await client.responses.create(
                model=self.model,
                input=messages,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "analyze_problem_clarity",
                        "schema": self._get_clarity_check_schema(),
                        "strict": True
                    }
                },
                max_output_tokens=1000,
            )
            
            output_text = getattr(resp, "output_text", None)
            if output_text:
                data = json.loads(output_text)
                return ProblemClarityResponse(**data)

            # 預設
            return ProblemClarityResponse(is_clear=True, issue_type="無問題", specific_issues=[], suggestions=[])

        except Exception as e:
            print(f"Error in _check_problem_clarity: {e}")
            return ProblemClarityResponse(is_clear=True, issue_type="檢查失敗", specific_issues=[], suggestions=[])


# --- 全局數學解題器實例 ---
math_solver = MathSolver()

# --- 輔助函式 (供 API 層使用) ---

def get_available_concepts() -> Dict[str, List[str]]:
    """
    獲取所有可用的數學概念，供前端選單與提示使用。
    (此函式放在這裡是為了讓 math_api.py 方便導入)
    """
    result = {}
    for domain, sections in MATH_CONCEPTS.items():
        concepts = []
        for section, concept_list in sections.items():
            # 保持與您原始程式碼一致的格式
            concepts.extend([f"{section}: {concept}" for concept in concept_list])
        result[domain] = concepts
    return result

def list_conversations() -> List[ConversationInfo]:
    """
    列出所有對話紀錄。
    (此函式是對 conversation.py 的轉發，讓 math_api.py 方便導入)
    """
    return list_conversations_from_db()