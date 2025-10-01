import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import Sidebar from './components/Sidebar';
import HomePage from './pages/HomePage';
// import ChatPage from './pages/ChatPage';
import EnglishPage from './pages/EnglishPage';
import QueryPage from './pages/QueryPage';
import MathPage from './pages/MathPage';
import SettingsPage from './pages/SettingsPage';

function App() {
  const [currentPage, setCurrentPage] = useState('home');

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const renderContent = () => {
    switch (currentPage) {
      case 'home':
        return <HomePage setCurrentPage={setCurrentPage}/>;
      // case 'chat':
        // return <ChatPage />;
      case 'english':
        return <EnglishPage />;
      case 'query':
        return <QueryPage />;
      case 'help':
        return <MathPage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <HomePage />;
    }
  };

  return (
    <div className="flex h-screen w-screen bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white">
      {/* Sidebar 區域 */}
      <Sidebar currentPage={currentPage} onPageChange={handlePageChange} />

      {/* 內容區域 */}
      <div className="basis-full flex-initial p-4 relative overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentPage}
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            transition={{ duration: 0.3 }}
            className="w-full h-full flex-1 justify-center items-center"
          >
            {renderContent()}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

export default App;
