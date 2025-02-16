import React from 'react';
import { ChatMessage } from '../components/ChatMessage';
import { VideoSection } from '../components/VideoSection';
import ChatInput from '../components/ChatInput';

const ChatPage = ({ showVideo }) => {
  return (
    <div className="chat-container">
      {showVideo && <VideoSection />}
      

      <div className="chat-content">
        <ChatMessage text="Some chat words......" isUser={false} />
        <ChatMessage text="Some chat words......" isUser={true} />
      </div>

      <ChatInput />
      
      <div className="absolute top-4 right-4 flex items-center gap-4">
        <input type="range" className="w-32" />
        <select className="p-2 pr-8 bg-white rounded-lg border">
          <option>選單</option>
        </select>
      </div>
    </div>
  );
};

export default ChatPage;
