import React from 'react';

export const ChatMessage = ({ text, isUser }) => {
    return (
      <div className={`max-w-[80%] ${isUser ? 'ml-auto' : ''}`}>
        <div className="bg-gray-200 p-4 rounded-2xl">
          <p className="text-gray-800">{text}</p>
        </div>
      </div>
    );
  };