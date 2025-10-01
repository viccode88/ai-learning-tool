// src/pages/HomePage.jsx
import React from "react";


const HomePage = ({setCurrentPage}) => {
  return (
    <div className="h-full p-8 dark:text-slate-50 select-none">
      <h1 className="text-3xl font-bold">Home Page</h1>
      <p>歡迎來到首頁！</p>
      <div className="flex items-center justify-centerw-2/3 h-2/3">
        <div className="p-10 grid grid-cols-2 grid-rows-2 w-full h-full ">
          <div className="font-semibold text-4x1 flex items-center justify-center text-center rounded-lg m-8 shadow-lg transition transform active:scale-95 cursor-pointer bg-gray-200 dark:bg-gray-600" onClick={() => setCurrentPage("english")}>英文對話</div>
          <div className="font-semibold text-4x1 flex items-center justify-center text-center rounded-lg m-8 shadow-lg transition transform active:scale-95 cursor-pointer bg-gray-200 dark:bg-gray-600" onClick={() => setCurrentPage("query")}>片語查詢</div>
          <div className="font-semibold text-4x1 flex items-center justify-center text-center rounded-lg m-8 shadow-lg transition transform active:scale-95 cursor-pointer bg-gray-200 dark:bg-gray-600" onClick={() => setCurrentPage("help")}>數學</div>
          <div className="font-semibold text-4x1 flex items-center justify-center text-center rounded-lg m-8 shadow-lg transition transform active:scale-95 cursor-pointer bg-gray-200 dark:bg-gray-600" onClick={() => setCurrentPage("settings")}>設定</div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
