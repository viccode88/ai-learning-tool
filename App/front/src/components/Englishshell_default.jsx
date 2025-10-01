import React, { useState } from "react";
import { useAppContext } from "../AppContext";
import InputBox from "./InputBox";

const EnglishShelldefault = ({ setSelectedConversation}) => {
  const [topic, setTopic] = useState("");

  const {
    model,
    level
  } = useAppContext();

  const createConversation = async (inputText) => {
    if (!inputText?.trim()) return;

    try {
      const res = await fetch("http://localhost:8000/api/v1/conversation", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic,
          level,
          model,
          user_prompt: inputText.trim(),
        }),
      });

      if (!res.ok) throw new Error("建立對話失敗");
      const data = await res.json();
      const { sid } = data;

      if (sid) {
        setSelectedConversation(sid);
      }
    } catch (err) {
      console.error("建立對話失敗:", err);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-full w-full p-8 bg-white dark:bg-gray-800 transition-colors duration-200 rounded-lg shadow-lg">
      <div className="w-full max-w-2xl space-y-8">
        <div className="text-center space-y-4">
          <h2 className="text-3xl font-semibold text-gray-900 dark:text-gray-100">
            歡迎使用英文學習工具
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            讓我們開始一段有趣的英文學習之旅
          </p>
        </div>

        <div className="space-y-6">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              對話主題（可留空）
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg 
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       bg-white dark:bg-gray-800 text-gray-900 dark:text-white
                       transition-all duration-200"
              placeholder="例如：點餐"
            />
          </div>

          <div className="transform transition-all duration-200">
            <InputBox
              onSend={(data) => createConversation(data.text)}
              showtext="請輸入你的需求說明..."
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default EnglishShelldefault;
