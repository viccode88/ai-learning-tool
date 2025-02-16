import React from 'react';
import ChatInput from '../components/ChatInput';

const MathPage = () => {
  return (
    <div className="flex-1 flex flex-col p-4 gap-4">
      <div className="bg-gray-200 p-4 rounded-2xl">
        <p className="font-bold mb-2">Step 1: .......</p>
        <p className="font-bold mb-2">Step 2: .......</p>
        <p className="font-bold mb-2">Step 3: .......</p>
        <p className="font-bold mb-2">Step 4: .......</p>
      </div>
      <ChatInput />
    </div>
  );
};

export default MathPage;
