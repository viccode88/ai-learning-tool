import { useState, useEffect, useRef } from "react";
import { ScrollText, Scroll } from "lucide-react";


const EnglishList = ({ setSelectedConversation }) => {
  const [isUnfold, setIsUnfold] = useState(false);
  const [conversations, setConversations] = useState([]);
  const settingsRef = useRef(null);

  // 新增一個函式用來抓取資料
  const fetchConversations = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/conversations/archived");
      const data = await res.json();
      if (data && Array.isArray(data.archives)) {
        // 將列表倒轉，最新放最上面
        setConversations(data.archives.slice().reverse());
      } else {
        console.warn("資料格式異常：", data);
        setConversations([]);
      }
    } catch (err) {
      console.error("Error loading conversations:", err);
      setConversations([]);
    }
  };

  // 監聽 isUnfold，只要展開就呼叫 fetchConversations 更新列表
  useEffect(() => {
    if (isUnfold) {
      fetchConversations();
    }
  }, [isUnfold]);

  return (
    <div
      ref={settingsRef}
      className={`h-full bg-gray-200 transition-all duration-300 flex-shrink-0 overflow-hidden relative rounded-lg shadow-lg
                ${isUnfold ? "w-64" : "w-10"} m-2 rounded-2xl`}
    >
      {/* 展開 / 折疊按鈕 */}
      <div onClick={() => setIsUnfold((prev) => !prev)} className="m-2 cursor-pointer z-10">
        {isUnfold ? <ScrollText size={24} color="black" /> : <Scroll size={24} color="black" />}
      </div>

      {/* 左滑消失的內容 */}
      <div
        className={`text-nowrap overflow-hidden absolute w-full h-full transition-transform duration-300 px-4 text-black mt-4
                    ${isUnfold ? "translate-x-0" : "-translate-x-full"}`}
      >
        <h2 className="text-xl font-bold mb-4">對話列表</h2>
        <ul className="space-y-2">
          {(conversations || []).map((data) => (
            <li
              key={data.sid}
              className="p-2 cursor-pointer hover:bg-gray-300 rounded w-full"
              onClick={() => setSelectedConversation(data.sid)}
            >
              {data.title}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default EnglishList;
