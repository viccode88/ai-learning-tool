import { useEffect, useState, useRef } from "react";
import ChatBox from "./ChatBox";
import InputBox from "./InputBox";

const Englishshell = ({ SelectedConversation}) => {
  const [conversation, setConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [transcript, setTranscript] = useState([]);
  const [isSending, setIsSending] = useState(false);
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
      
      // 確保 transcript 中的每個 entry 都有 text 屬性
      const processedTranscript = (data.transcript || []).map((msg, idx) => {
        let textContent = msg.text;
        if (typeof msg.text === 'object' && msg.text !== null && msg.text.ai_response) {
          textContent = msg.text.ai_response;
        } else if (typeof msg.text !== 'string') {
          textContent = JSON.stringify(msg.text); // 作為後備
        }
        
        return {
          ...msg,
          text: textContent,
          id: `msg-${idx}`,
          status: 'success'
        };
      });
      
      setTranscript(processedTranscript);
    } catch (error) {
      console.error("取得對話資料失敗:", error);
      alert("載入對話資料時發生錯誤。");
    } finally {
      setLoading(false);
    }
  };

  const createConversation = async (userText) => {
    if (!SelectedConversation || isSending) return;

    setIsSending(true);
    const messageId = `msg-${Date.now()}`;
    const newUserEntry = { 
      speaker: "user", 
      text: userText, 
      id: messageId,
      status: 'sending'
    };
    setTranscript(prev => [...prev, newUserEntry]);

    try {
      const res = await fetch(`http://localhost:8000/api/v1/conversation/${SelectedConversation}/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: JSON.stringify({ user: userText }),
      });
      if (!res.ok) throw new Error("回應失敗");

      // 標記使用者訊息為成功
      setTranscript(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, status: 'success' } : msg
      ));

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let jsonBuffer = "";
      let hasAddedLive = false;
      const aiMessageId = `msg-${Date.now()}-ai`;
      let structuredData = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        
        // SSE: 逐行處理 data: ...\n\n
        const lines = chunk.split("\n\n");
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);
          
          if (payload === "[DONE]") {
            continue;
          }
          
          try {
            const parsed = JSON.parse(payload);
            
            if (parsed.type === 'error') {
              console.error("串流錯誤:", parsed.message);
              throw new Error(parsed.message);
            }
            
            if (parsed.type === 'delta') {
              // 累積 JSON 片段
              jsonBuffer += parsed.content;
              
              // 嘗試解析部分 JSON 來顯示進度（可選）
              if (!hasAddedLive) {
                setTranscript(prev => [...prev, { 
                  speaker: "ai", 
                  text: "正在生成回應...",
                  id: aiMessageId,
                  status: 'sending'
                }]);
                hasAddedLive = true;
              }
            }
            
            if (parsed.type === 'complete') {
              // 接收到完整的結構化數據
              structuredData = parsed.data;
              
              // 更新 AI 訊息，包含結構化數據
              setTranscript(prev => {
                const filtered = prev.filter(msg => msg.id !== aiMessageId);
                return [...filtered, { 
                  speaker: "ai", 
                  text: structuredData.ai_response,
                  hint: structuredData.hint,
                  translation: structuredData.translation,
                  id: aiMessageId,
                  status: 'success',
                  structured: true
                }];
              });
            }
          } catch (e) {
            // 如果不是 JSON，可能是舊格式或錯誤
            if (payload.startsWith("[ERROR]")) {
              console.error("串流錯誤:", payload);
              throw new Error(payload);
            }
            console.warn("無法解析 payload:", payload, e);
          }
        }
      }

      // 如果沒有收到 complete 事件，嘗試解析累積的 JSON
      if (!structuredData && jsonBuffer) {
        try {
          structuredData = JSON.parse(jsonBuffer);
          setTranscript(prev => {
            const filtered = prev.filter(msg => msg.id !== aiMessageId);
            return [...filtered, { 
              speaker: "ai", 
              text: structuredData.ai_response,
              hint: structuredData.hint,
              translation: structuredData.translation,
              id: aiMessageId,
              status: 'success',
              structured: true
            }];
          });
        } catch (e) {
          console.error("無法解析完整 JSON:", e);
          throw new Error("無法解析伺服器回應");
        }
      }

    } catch (error) {
      console.error("送出訊息時發生錯誤:", error);
      // 標記使用者訊息為失敗
      setTranscript(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, status: 'failed', error: error.message } : msg
      ));
    } finally {
      setIsSending(false);
    }
  };

  const handleRetry = (messageId) => {
    const message = transcript.find(msg => msg.id === messageId);
    if (message && message.speaker === 'user') {
      // 移除失敗的訊息及其後續訊息
      setTranscript(prev => prev.filter(msg => msg.id !== messageId));
      // 重新發送
      createConversation(message.text);
    }
  };

  const handleEdit = (messageId, newText) => {
    const messageIndex = transcript.findIndex(msg => msg.id === messageId);
    if (messageIndex === -1) return;
    
    // 移除該訊息及其後續所有訊息
    setTranscript(prev => prev.slice(0, messageIndex));
    
    // 重新發送編輯後的訊息
    createConversation(newText);
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
                <div key={entry.id || index} className="transform transition-all duration-200 hover:scale-[1.01]">
                  <ChatBox
                    role={entry.speaker === "user" ? "user" : "ai"}
                    message={entry.text}
                    messageId={entry.id}
                    status={entry.status}
                    error={entry.error}
                    onRetry={handleRetry}
                    onEdit={handleEdit}
                    isLastUserMessage={entry.speaker === "user" && index === transcript.findLastIndex(msg => msg.speaker === "user")}
                    hint={entry.hint}
                    translation={entry.translation}
                    structured={entry.structured}
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
        <InputBox 
          onSendMessage={(text) => createConversation(text)} 
          showtext="請輸入你想聊的..." 
          disabled={isSending}
        />
      </div>
    </div>
  );
};

export default Englishshell;
