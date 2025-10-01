import { useState,useEffect,useRef } from 'react';
import { PanelLeft, PanelLeftClose, Home, MessageSquare, BookOpenText, Search, HelpCircle, Settings  } from 'lucide-react';
import ThemeToggle from './ThemeToggle';


const Sidebar = ({ currentPage, onPageChange }) => {
  const [isHovered, setIsHovered] = useState(false);

  const menuItems = [
    { name: 'home', label: '首頁', icon: <Home size={24} /> },
    // { name: 'chat', label: 'Chat', icon: <MessageSquare size={24} /> },
    { name: 'english', label: '英文對話', icon: <MessageSquare size={24} /> },
    { name: 'query', label: '單字/片語查詢', icon: <Search size={24} /> },
    { name: 'help', label: '數學解題', icon: <HelpCircle size={24} /> },
    { name: 'settings', label: '設定', icon: <Settings size={24} /> },
  ];

  return (
    <div
      className={`h-screen bg-gray-900 text-white transition-all duration-300 flex-shrink-0 select-none ${
        isHovered ? 'w-48' : 'w-16'
      }`}
    >
      <ul className="mt-4 flex-col h-auto">
        <li
            className={`flex items-center px-4 py-3 cursor-pointer transition-all `}
            onClick={() => setIsHovered(!isHovered)}
          >{isHovered ? <PanelLeftClose size={24} /> : <PanelLeft size={24}/>}</li>
        
        {menuItems.map((item) => (
          <li
            key={item.name}
            className={`flex items-center pl-4 py-3 cursor-pointer transition-all ${
              currentPage === item.name ? 'bg-gray-700' : 'hover:bg-gray-800'
            }`}
            onClick={() => onPageChange(item.name)}
          >
            {item.icon}
            <span className={`text-nowrap ml-3 transition-opacity duration-300 ${isHovered ? 'opacity-100' : 'opacity-0 w-0'}`}>
              {item.label}
            </span>
          </li>
        ))}
        <il className="mb-2">
          <ThemeToggle isSidebarOpen={isHovered} /></il>
      </ul>
    </div>
  );
};


export default Sidebar;
