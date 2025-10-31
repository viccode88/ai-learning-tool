import { useState, useEffect, useRef } from "react";
import { ScrollText, Scroll } from "lucide-react";

const NewConversationModal = ({ isOpen, onClose, onCreate, isCreating }) => {
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState("A1");
  const levels = ["A1", "A2", "B1", "B2", "C1", "C2"];

  const handleSubmit = () => {
    if (!isCreating) {
      onCreate(topic, level);
      setTopic("");
      setLevel("A1");
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-xl text-black dark:text-white">
        <h2 className="text-xl font-bold mb-4">新增對話</h2>
        {isCreating ? (
          <div className="py-8 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-300">正在建立對話...</p>
          </div>
        ) : (
          <>
            <div className="space-y-4">
              <div>
                <label htmlFor="topic" className="block text-sm font-medium text-gray-700 dark:text-gray-300">主題</label>
                <input
                  type="text"
                  id="topic"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="例如：訂餐"
                />
              </div>
              <div>
                <label htmlFor="level" className="block text-sm font-medium text-gray-700 dark:text-gray-300">難度</label>
                <select
                  id="level"
                  value={level}
                  onChange={(e) => setLevel(e.target.value)}
                  className="mt-1 block w-full pl-3 pr-10 py-2 text-base bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                >
                  {levels.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-2">
              <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-200 dark:bg-gray-600 rounded-md hover:bg-gray-300 dark:hover:bg-gray-500">取消</button>
              <button onClick={handleSubmit} className="px-4 py-2 text-sm font-medium text-white bg-black rounded-md hover:bg-gray-800">建立</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const EnglishList = ({ setSelectedConversation }) => {
  const [isUnfold, setIsUnfold] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const settingsRef = useRef(null);

  const fetchConversations = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/conversations/archived");
      const data = await res.json();
      if (data && Array.isArray(data.archives)) {
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

  const handleNewConversation = async (topic, level) => {
    setIsCreating(true);
    try {
      const requestBody = {
        topic: topic || "",
        level: level || "A1",
        // 不設定 title，讓後端自動生成
      };
      const res = await fetch("http://localhost:8000/api/v1/conversation", { 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody)
      });
      const data = await res.json();
      if (data && data.sid) {
        setSelectedConversation(data.sid);
        await fetchConversations();
        setIsModalOpen(false);
      }
    } catch (e) {
      console.error("新建對話失敗", e);
      alert("建立對話失敗，請稍後再試");
    } finally {
      setIsCreating(false);
    }
  };

  useEffect(() => {
    if (isUnfold) {
      fetchConversations();
    }
  }, [isUnfold]);

  return (
    <>
      <NewConversationModal
        isOpen={isModalOpen}
        onClose={() => !isCreating && setIsModalOpen(false)}
        onCreate={handleNewConversation}
        isCreating={isCreating}
      />
      <div
        ref={settingsRef}
        className={`h-full bg-gray-200 transition-all duration-300 flex-shrink-0 overflow-hidden relative rounded-lg shadow-lg
                  ${isUnfold ? "w-64" : "w-10"} m-2 rounded-2xl`}
      >
        <div onClick={() => setIsUnfold((prev) => !prev)} className="m-2 cursor-pointer z-10">
          {isUnfold ? <ScrollText size={24} color="black" /> : <Scroll size={24} color="black" />}
        </div>

        <div
          className={`text-nowrap overflow-hidden absolute w-full h-full transition-transform duration-300 px-4 text-black mt-4
                      ${isUnfold ? "translate-x-0" : "-translate-x-full"}`}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">對話列表</h2>
            <button
              className="px-2 py-1 text-sm bg-black text-white rounded"
              onClick={() => setIsModalOpen(true)}
            >新增</button>
          </div>
          <ul className="space-y-2">
            {(conversations || []).map((data) => (
              <li
                key={data.sid}
                className="p-2 hover:bg-gray-300 rounded w-full"
              >
                <div className="flex items-center justify-between">
                  <div className="cursor-pointer flex-1 truncate pr-2" onClick={() => setSelectedConversation(data.sid)}>
                    {data.title || "未命名對話"}
                  </div>
                  <button
                    className="text-xs text-red-600 flex-shrink-0 px-2 py-1 hover:bg-red-100 rounded"
                    onClick={async (e) => {
                      e.stopPropagation();
                      try {
                        const res = await fetch(`http://localhost:8000/api/v1/conversation/${data.sid}`, { method: "DELETE" });
                        if (res.ok) {
                          fetchConversations();
                          setSelectedConversation(null);
                        } else {
                           console.error("刪除失敗", await res.text());
                        }
                      } catch (err) {
                        console.error("刪除失敗", err);
                      }
                    }}
                  >刪除</button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
};

export default EnglishList;
