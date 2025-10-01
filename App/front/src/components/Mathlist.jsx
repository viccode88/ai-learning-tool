import { useState, useEffect, useRef } from "react";
import { ScrollText, Scroll } from "lucide-react";


const MathList = ({ setSelectedConversation }) => {
    const [isUnfold, setIsUnfold] = useState(false);
    const [conversations, setConversations] = useState([]);
    const settingsRef = useRef(null);

    useEffect(() => {
    const fetchConversations = async () => {
        try {
        const response = await fetch("http://localhost:8000/api/v1/math/conversations");
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setConversations(data);
        } catch (error) {
        console.error("Failed to fetch conversations:", error);
        }
    };

    fetchConversations();
    }, []);




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

      {/* 滑出清單內容 */}
      <div
        className={`text-nowrap overflow-hidden absolute w-full h-full transition-transform duration-300 px-4 text-black mt-4
          ${isUnfold ? "translate-x-0" : "-translate-x-full"}`}
      >
        <h2 className="text-xl font-bold mb-4">對話列表</h2>
        <ul className="space-y-2">
          {(conversations || []).map((data) => (
            <li
              key={data.session_id}
              className="p-2 cursor-pointer hover:bg-gray-300 rounded w-full"
              onClick={() => setSelectedConversation(data.session_id)}
              title={data.session_id} // 滑鼠懸停顯示 session_id
            >
              {data.title || "未命名對話"}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default MathList;
