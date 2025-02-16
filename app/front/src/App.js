import React, { useState } from 'react';


import { Sidebar } from './components/Sidebar';
import ChatPage from './pages/ChatPage';
import MathPage from './pages/MathPage';
import SettingsPage from './pages/SettingsPage';
import ToolboxPage from './pages/ToolboxPage';


const App = () => {
  const [currentPage, setCurrentPage] = useState('chat');

  const handlePageChange = (page) => {
    if (currentPage !== page) {
      console.log("Changing page to:", page);
      setCurrentPage(page);
    }
  };

  const renderContent = () => {
    console.log("Rendering page:", currentPage); // Debug 當前頁面
    switch (currentPage) {
      case 'chat':
        return <ChatPage showVideo={false} />;
      case 'math':
        return <MathPage />;
      case 'settings':
        return <SettingsPage />;
      case 'toolbox':
        return <ToolboxPage />;
      default:
        return <ChatPage showVideo={false} />;
    }
  };
  
  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar currentPage={currentPage} onPageChange={handlePageChange} />
      <div className="flex-1 relative">
        {renderContent()}
      </div>
    </div>
  );
};

export default App;