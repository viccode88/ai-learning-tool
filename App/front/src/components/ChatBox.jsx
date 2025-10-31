import React, { useRef, useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import CopyButton from "./littlebutton/CopyButton";
import AudioButton from "./littlebutton/AudioButton";


const ChatBox = ({ message, role, messageId, status, error, onRetry, onEdit, isLastUserMessage, hint, translation, structured }) => {
  const messageRef = useRef(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(typeof message === 'string' ? message : '');
  const [showTranslation, setShowTranslation] = useState(false);
  const [showHint, setShowHint] = useState(false);

  useEffect(() => {
    setEditText(typeof message === 'string' ? message : JSON.stringify(message));
  }, [message]);
  // 判斷 user 或 ai 的排列方向
  const isUser = role === "user";
  const isAI = role === "ai";

  const handleEditSubmit = () => {
    if (editText.trim() && onEdit) {
      onEdit(messageId, editText.trim());
      setIsEditing(false);
    }
  };

  const handleEditCancel = () => {
    setEditText(message);
    setIsEditing(false);
  };

  return (
    <div
      className={`w-full p-3 flex flex-col ${
        isUser ? "items-end" : "items-start"
      }`}
    >
      <div
        className={`p-2 rounded-lg shadow-md max-w-lg break-words relative ${
          isUser 
            ? status === 'failed' 
              ? "bg-red-400 text-white" 
              : "bg-gray-400 text-white" 
            : isAI 
              ? "bg-gray-200 text-black" 
              : ""
        }`}
        ref={messageRef}
      >
        {isEditing ? (
          <div className="space-y-2">
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              className="w-full p-2 rounded bg-white text-black border border-gray-300 min-h-[60px]"
              autoFocus
            />
            <div className="flex space-x-2 justify-end">
              <button 
                onClick={handleEditCancel}
                className="px-3 py-1 text-xs bg-gray-500 text-white rounded hover:bg-gray-600"
              >
                取消
              </button>
              <button 
                onClick={handleEditSubmit}
                className="px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                確定
              </button>
            </div>
          </div>
        ) : (
          <>
            <ReactMarkdown>{typeof message === 'string' ? message : '無法顯示內容'}</ReactMarkdown>
            
            {/* 結構化輸出的控制按鈕區域 */}
            {isAI && (hint || translation) && (
              <div className="mt-4 pt-3 border-t border-gray-300/50 dark:border-gray-600/50 space-y-2">
                {/* 提示詞按鈕和內容 */}
                {hint && (
                  <div>
                    <button
                      onClick={() => setShowHint(!showHint)}
                      className="text-xs font-semibold text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300 flex items-center gap-1.5 transition-colors"
                    >
                      💡 {showHint ? '隱藏提示' : '顯示提示'}
                      <span className={`transform transition-transform duration-200 ${showHint ? 'rotate-180' : ''}`}>
                        ▼
                      </span>
                    </button>
                    {showHint && (
                      <div className="mt-2 text-sm text-gray-800 dark:text-gray-200 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800/50 p-3 rounded-md italic">
                        {hint}
                      </div>
                    )}
                  </div>
                )}
                
                {/* 翻譯按鈕和內容 */}
                {translation && (
                  <div>
                    <button
                      onClick={() => setShowTranslation(!showTranslation)}
                      className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 flex items-center gap-1.5 transition-colors"
                    >
                      🌏 {showTranslation ? '隱藏翻譯' : '顯示翻譯'}
                      <span className={`transform transition-transform duration-200 ${showTranslation ? 'rotate-180' : ''}`}>
                        ▼
                      </span>
                    </button>
                    {showTranslation && (
                      <div className="mt-2 text-sm text-gray-800 dark:text-gray-200 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/50 p-3 rounded-md">
                        {translation}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
            
            {status === 'sending' && (
              <div className="mt-2 text-xs opacity-70">發送中...</div>
            )}
            {status === 'failed' && error && (
              <div className="mt-2 text-xs">❌ 發送失敗: {error}</div>
            )}
          </>
        )}
      </div>

      <div
        className={`w-auto pt-1 flex space-x-1 ${
          isUser ? "justify-end" : "justify-start"
        }`}
      >
        {!isEditing && <CopyButton textToCopy={messageRef.current?.innerText || ""} />}
        
        {isUser && status === 'failed' && onRetry && (
          <div 
            onClick={() => onRetry(messageId)}
            className="transition-all duration-300 ease-in-out cursor-pointer relative group"
            title="重新發送"
          >
            <div className="absolute -top-7 left-1/2 -translate-x-1/2 text-sm px-2 py-1 rounded bg-black text-white whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
              重新發送
            </div>
            <div className="transition-transform duration-300 ease-in-out hover:scale-110">
              <svg className="w-4 h-4 text-gray-600 dark:text-slate-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
          </div>
        )}
        
        {isUser && status === 'success' && isLastUserMessage && onEdit && !isEditing && (
          <div 
            onClick={() => setIsEditing(true)}
            className="transition-all duration-300 ease-in-out cursor-pointer relative group"
            title="編輯訊息"
          >
            <div className="absolute -top-7 left-1/2 -translate-x-1/2 text-sm px-2 py-1 rounded bg-black text-white whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
              編輯訊息
            </div>
            <div className="transition-transform duration-300 ease-in-out hover:scale-110">
              <svg className="w-4 h-4 text-gray-600 dark:text-slate-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </div>
          </div>
        )}
        
        {isAI && status === 'success' && (
          <AudioButton ttstext={message} size={16} />
        )}
      </div>
    </div>
  );
};

export default ChatBox;
