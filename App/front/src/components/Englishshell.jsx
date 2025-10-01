import { useEffect, useState, useRef } from "react";
import ChatBox from "./ChatBox";
import InputBox from "./InputBox";

const Englishshell = ({ SelectedConversation}) => {
  const [conversation, setConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [transcript, setTranscript] = useState([]);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (!SelectedConversation) {
      alert("找不到對話 SID，請先建立對話。");
      setLoading(false);
      return;
    }

    fetchConversation(SelectedConversation);
  }, [SelectedConversation]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  const fetchConversation = async (sid) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/conversations/archived/${sid}`);
      if (!res.ok) throw new Error("回應錯誤");
      const data = await res.json();
      setConversation(data);
      setTranscript(data.transcript || []);
    } catch (error) {
      console.error("取得對話資料失敗:", error);
      alert("載入對話資料時發生錯誤。");
    } finally {
      setLoading(false);
    }
  };

  const createConversation = async (userText) => {
    if (!SelectedConversation) return;

    const newUserEntry = { speaker: "user", text: userText };
    setTranscript(prev => [...prev, newUserEntry]);

    try {
      const res = await fetch(`http://localhost:8000/api/v1/conversation/${SelectedConversation}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user: userText }),
      });
      if (!res.ok) throw new Error("回應失敗");
      const data = await res.json();

      await fetchConversation(SelectedConversation);

    } catch (error) {
      console.error("送出訊息時發生錯誤:", error);
    }
  };


  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500 dark:text-gray-400 animate-pulse">載入中...</div>
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500 dark:text-gray-400">無法顯示對話內容。</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full w-full bg-white dark:bg-gray-800 transition-colors duration-200 rounded-lg shadow-lg">
      <div className="p-6 space-y-6 flex-grow overflow-y-auto">
        <div className="space-y-4">
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            {conversation.title || "未命名對話"}
          </h1>
          <div className="space-y-2 text-gray-600 dark:text-gray-300">
            <p>主題：{conversation.topic}</p>
            <p>等級：{conversation.level}</p>
          </div>
        </div>

        <div className="mt-8">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">對話內容</h2>
          {transcript.length > 0 ? (
            <div className="space-y-4 w-full">
              {transcript.map((entry, index) => (
                <div key={index} className="transform transition-all duration-200 hover:scale-[1.01]">
                  <ChatBox
                    role={entry.speaker === "user" ? "user" : "ai"}
                    message={entry.text}
                  />
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          ) : (
            <div className="text-gray-500 dark:text-gray-400">目前尚無訊息。</div>
          )}
        </div>
      </div>

      <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <InputBox onSend={(data) => createConversation(data.text)} showtext="請輸入你的需求說明..." />
      </div>
    </div>
  );
};

export default Englishshell;
