import React, { useRef, useState } from "react";
import CopyButton from "./littlebutton/CopyButton";
import AudioButton from "./littlebutton/AudioButton";
import { HelpCircle } from "lucide-react";
import InputBox from "./InputBox"; // 引入 InputBox


const MathBox = ({ step, sessionId }) => {
  const messageRef = useRef(null);
  const { step_number, description, reasoning, calculation, key_insight } = step;
  const [questionAnswer, setQuestionAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [showInputBox, setShowInputBox] = useState(false); // ⬅️ 控制顯示輸入框

  const handleAsk = () => {
    setShowInputBox(!showInputBox);
    setQuestionAnswer(""); // 清除舊回應
  };

  const handleQuestionSend = async ({ text }) => {
    if (!text) return;

    setLoading(true);
    setQuestionAnswer("");

    try {
      const res = await fetch("http://localhost:8000/api/v1/math/question", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          session_id: sessionId,
          step_number: step_number,
          question: text,
          context: description
        })
      });

      if (!res.ok) throw new Error("無法取得回答");
      const result = await res.json();
      setQuestionAnswer(result.answer);
    } catch (err) {
      setQuestionAnswer("❌ 發生錯誤：" + err.message);
    } finally {
      setLoading(false);
      setShowInputBox(false); // 發送後自動收起
    }
  };

  return (
    <div className="max-w-[90%] p-3 rounded-lg bg-white text-black shadow-md relative group">
      <div ref={messageRef} className="space-y-2">
        <h4 className="font-semibold">步驟 {step_number}</h4>
        <p><strong>📝 描述：</strong>{description}</p>
        <p><strong>🤔 推理：</strong>{reasoning}</p>
        <p><strong>🧮 計算：</strong>{calculation || "（此步驟無需計算）"}</p>
        {key_insight && (
          <p>
            <strong>💡 關鍵洞察：</strong>{key_insight}
          </p>
        )}
      </div>

      <div className="absolute top-2 right-2 flex space-x-1">
        <HelpCircle size={20} onClick={handleAsk} className="cursor-pointer" />
      </div>

      {/* 顯示輸入框 */}
      {showInputBox && (
        <div className="mt-2">
          <InputBox
            showtext="請針對此步驟提問..."
            onSend={handleQuestionSend}
          />
        </div>
      )}

      {/* 顯示載入/回應 */}
      {loading && <p className="text-blue-600 mt-2">💬 回覆中...</p>}
      {questionAnswer && <p className="mt-2 bg-gray-100 p-2 rounded">{questionAnswer}</p>}
    </div>
  );
};

export default MathBox;
