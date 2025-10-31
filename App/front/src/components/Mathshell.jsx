import React, { useState } from "react";
import { useAppContext } from "../AppContext";
import MathBox from "./MathBox";
import InputBox from "./InputBox";

const Mathshell = (selectedProblem) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [session_id, setSession_id] = useState("");
  const [loading, setLoading] = useState(false);
  const { mathModel } = useAppContext();

  const handleSendMessage = async (message, options = {}) => {
    setError("");
    setData(null);
    setLoading(true);

    try {
      let response;
      if (message.file) {
        // 如果有檔案，使用圖片解題端點
        const formData = new FormData();
        formData.append('image', message.file);
        
        // 如果有其他選項，也加入到 formData
        if (message.text) {
          formData.append('additional_context', message.text);
        }
        
        response = await fetch("http://localhost:8000/api/v1/math/solve-image", {
          method: "POST",
          body: formData,
        });
      } else {
        // 如果沒有檔案，使用原本的文字解題端點
        const requestBody = { problem: message.text };

        if (options.domain) requestBody.domain = options.domain;
        if (options.difficulty) requestBody.difficulty = options.difficulty;
        if (options.specific_concepts && options.specific_concepts.length > 0) {
          requestBody.specific_concepts = options.specific_concepts;
        }

        response = await fetch("http://localhost:8000/api/v1/math/solve", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        });
      }

      if (!response.ok) {
        let detail = "發生未知錯誤";
        try {
          const errData = await response.json();
          detail = errData.detail || detail;
        } catch (_) {
          detail = await response.text();
        }
        if (typeof detail === 'string' && detail.startsWith('[NOT_MATH]')) {
          throw new Error('[NOT_MATH] 這看起來不像數學題，請提供更明確的數學問題或上傳包含題目的圖片。');
        }
        throw new Error(detail);
      }

      const result = await response.json();
      setData(result.solution);
      setSession_id(result.session_id);
    } catch (err) {
      const msg = err.message || "無法取得資料";
      if (msg.startsWith('[NOT_MATH]')) {
        setError('');
        setData({
          problem: message.text || '（未提供文字）',
          domain: '未識別',
          solution_approach: '非數學題提示',
          relevant_concepts: [],
          steps: [],
          final_answer: '這看起來不是數學題，請輸入數學相關問題或上傳包含題目的圖片。',
        });
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full w-full p-6 bg-white dark:bg-gray-800 transition-colors duration-200 rounded-lg shadow-lg">
      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 dark:text-red-400 font-medium">
          錯誤：{error}
        </div>
      )}

      {loading && (
        <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-blue-600 dark:text-blue-400 font-medium animate-pulse">
          計算中，請稍候…
        </div>
      )}

      {!data && !error && !loading && (
        <div className="mb-6 text-xl text-gray-600 dark:text-gray-300 font-medium">
          輸入數學問題或上傳圖片
        </div>
      )}

      {data && (
        <div className="space-y-8 overflow-y-auto flex-grow">
          <div className="space-y-4">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">問題</h2>
            <p className="text-gray-700 dark:text-gray-300">{data.problem}</p>
          </div>

          <div className="space-y-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p className="text-gray-700 dark:text-gray-300">
              <span className="font-semibold">領域：</span>{data.domain || "未指定"}
            </p>
            <p className="text-gray-700 dark:text-gray-300">
              <span className="font-semibold">方法：</span>{data.solution_approach}
            </p>
            <p className="text-gray-700 dark:text-gray-300">
              <span className="font-semibold">相關概念：</span>{data.relevant_concepts.join(", ")}
            </p>
          </div>

          <div className="space-y-6">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white">解題步驟</h3>
            <div className="space-y-4">
              {data.steps.map((step) => (
                <div key={step.step_number} className="transform transition-all duration-200 hover:scale-[1.01]">
                  <MathBox step={step} sessionId={session_id} />
                </div>
              ))}
            </div>
          </div>

          <div className="mt-8 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">最終答案</h3>
            <p className="text-gray-700 dark:text-gray-300">{data.final_answer}</p>
          </div>
        </div>
      )}

      <div className="mt-6">
        <InputBox onSend={handleSendMessage} showtext="請輸入要解的數學問題或上傳圖片…" />
      </div>
    </div>
  );
};

export default Mathshell;
