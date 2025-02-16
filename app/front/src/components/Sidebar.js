import React from 'react';
import { MessageSquare, HelpCircle, Sliders, BoxIcon } from 'lucide-react';

export const Sidebar = ({ currentPage, onPageChange }) => {
  const menuItems = [
    { id: 'chat', icon: MessageSquare, bgColor: '#baf2bb', iconColor: 'text-green-500' },
    { id: 'math', icon: HelpCircle, bgColor: '#baf2d8', iconColor: 'text-green-500' },
    { id: 'toolbox', icon: BoxIcon, bgColor: '#bad7f2', iconColor: 'text-blue-500' },
    { id: 'settings', icon: Sliders, bgColor: '#f2bac9', iconColor: 'text-pink-500' }
  ];

  return (
    <div className="flex flex-col gap-4 p-4 bg-white">
      {menuItems.map((item) => (
        <button
          key={item.id}
          style={{ backgroundColor: item.bgColor }} 
          onClick={() => onPageChange(item.id)}
          className={`p-2 rounded-lg ${item.bgColor} transition-all duration-200 ${
            currentPage === item.id ? 'ring-2 ring-offset-2 ring-gray-300' : ''
          }`}
        >
          {item.icon ? (
            <item.icon className={`w-6 h-6 ${item.iconColor}`} />
          ) : (
            <div className="w-6 h-6" />
          )}
        </button>
      ))}
    </div>
  );
};