import React, { useRef } from "react";
import ReactMarkdown from "react-markdown";
import CopyButton from "./littlebutton/CopyButton";
import AudioButton from "./littlebutton/AudioButton";


const ChatBox = ({ message, role }) => {
  const messageRef = useRef(null);

  // 判斷 user 或 ai 的排列方向
  const isUser = role === "user";
  const isAI = role === "ai"; // 新增這行


  return (
    <div
      className={`w-full p-3 flex flex-col ${
        isUser ? "items-end" : "items-start"
      }`}
    >
      <div
        className={`p-2 rounded-lg shadow-md max-w-lg break-words ${
          isUser ? "bg-gray-400 text-white" : isAI ? "bg-gray-200 text-black" : ""
        }`}
        ref={messageRef}
      >
        <ReactMarkdown>{message}</ReactMarkdown>
      </div>

      <div
        className={`w-auto pt-1 flex space-x-2 ${
          isUser ? "justify-end" : "justify-start"
        }`}
      >
        <CopyButton textToCopy={messageRef.current?.innerText || ""} />
        {isUser ? (
            null // <EditchatButton />
        ) : isAI ? (
          <AudioButton ttstext={message} size={16} />
        ) : null}
      </div>
    </div>
  );
};

export default ChatBox;
