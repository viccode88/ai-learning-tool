import React from 'react';
import { MessageSquare } from 'lucide-react';

const ChatInput = () => {
  return (
    <div className="chat-input">
      <input
        type="text"
        placeholder="Type something......"
        className="w-full p-4 pr-12 bg-gray-200 rounded-xl focus:outline-none"
      />
      <button 
        className="absolute right-4 top-1/2 transform -translate-y-1/2"
        style={{ backgroundColor: "bg-gray-200" }}
      >
        <MessageSquare className="w-5 h-5 text-gray-500" />
      </button>
    </div>
  );
};

export default ChatInput;