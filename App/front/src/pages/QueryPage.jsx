import React, { useState } from "react";
import { useAppContext } from "../AppContext";

import InputBox from "../components/InputBox";
import EnglishSettings from "../components/EnglishSettings";
import AudioButton from "../components/littlebutton/AudioButton";


const QueryPage = () => {
  const {
    model,
    level,
  } = useAppContext();
  const [queryword, setQueryword] = useState("");
  const [definitions, setDefinitions] = useState([]);
  const [examples, setExamples] = useState([]);
  const [grammarTips, setGrammarTips] = useState("");
  const [ipa, setIpa] = useState("");
  const [translation, setTranslation] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);


  const handleSend = async ({ text }) => {
    if (!text.trim()) return;

    setLoading(true);
    setError("");
    setQueryword(text);
    setDefinitions([]);
    setExamples([]);
    setGrammarTips("");
    setIpa("");
    setTranslation(null);
    setAudioUrl(null);

    try {
      const url = new URL("http://localhost:8000/api/v1/query", window.location.origin);
      url.searchParams.append("q", text.trim());
      if (level) url.searchParams.append("level", level);
      if (model) url.searchParams.append("model", model);

      const res = await fetch(url.toString(), { method: "GET" });

      const contentType = res.headers.get("content-type") || "";
      if (!res.ok) {
        const errData = contentType.includes("application/json")
          ? await res.json()
          : await res.text();
        throw new Error(errData.detail || "查詢失敗");
      }

      if (!contentType.includes("application/json")) {
        throw new Error("回傳格式錯誤，請確認後端是否正確回傳 JSON");
      }

      const data = await res.json();
      setDefinitions(data.definitions || []);
      setExamples(data.examples || []);
      setGrammarTips(data.grammar_tips || "");
      setIpa(data.ipa || "");
      setTranslation(data.translation || null);
      setAudioUrl(data.audio_url || null);
    } catch (err) {
      setError(err.message || "發生錯誤");
    } finally {
      setLoading(false);
    }
  };

  const ResultCard = ({ title, children }) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
      <h3 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">{title}</h3>
      <div className="text-gray-700 dark:text-gray-300 space-y-3">
        {children}
      </div>
    </div>
  );

  return (
    <div className="flex h-full w-full bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-slate-50">
      <div className="flex flex-col h-full w-full">
        <header className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">單字/片語查詢</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">輸入單字、片語或句子，立即獲得詳細解釋。</p>
          </div>
        </header>
        
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto">
            {loading && (
              <div className="flex justify-center items-center h-48">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
              </div>
            )}
            {error && (
              <div className="mt-4 p-4 bg-red-100 dark:bg-red-900/20 border border-red-400 dark:border-red-600/50 text-red-700 dark:text-red-300 rounded-lg select-text">
                <strong>錯誤：</strong>{error}
              </div>
            )}

            {!loading && !error && queryword && (
              <div className="space-y-6 animate-fade-in">
                <div className="pb-6 mb-6 border-b border-gray-200 dark:border-gray-700">
                  <h2 className="text-5xl font-bold mb-3 select-text flex items-center">
                    {queryword}
                    <span className="text-2xl text-gray-500 dark:text-gray-400 ml-4 font-mono">{ipa}</span>
                    <AudioButton ttstext={queryword} size={24} className="ml-3 text-blue-500 hover:text-blue-600"/>
                  </h2>
                  {translation && (
                    <p className="text-xl text-blue-600 dark:text-blue-400 select-text">{translation}</p>
                  )}
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  {definitions.length > 0 && (
                    <ResultCard title="定義">
                      <ul className="list-inside space-y-2">
                        {definitions.map((def, i) => (
                          <li key={i} className="flex items-start">
                            <span className="font-semibold text-blue-500 dark:text-blue-400 w-16 flex-shrink-0">{def.pos || 'N/A'}</span>
                            <span>{def.text}</span>
                          </li>
                        ))}
                      </ul>
                    </ResultCard>
                  )}

                  {examples.length > 0 && (
                    <ResultCard title="例句">
                      <ul className="space-y-4">
                        {examples.map((ex, i) => (
                          <li key={i} className="flex items-center">
                            <span className="flex-grow pr-2">{ex.text}</span>
                            {ex.level && (
                              <span className="text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded-full flex-shrink-0">{ex.level}</span>
                            )}
                            <AudioButton ttstext={ex.text} size={18} className="ml-2 text-gray-500 hover:text-gray-600"/>
                          </li>
                        ))}
                      </ul>
                    </ResultCard>
                  )}
                </div>

                {grammarTips && (
                  <ResultCard title="文法提示">
                    <p className="whitespace-pre-wrap leading-relaxed">{grammarTips}</p>
                  </ResultCard>
                )}

              </div>
            )}
          </div>
        </main>

        <footer className="p-6 border-t border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-900/50 backdrop-blur-sm sticky bottom-0">
          <div className="max-w-4xl mx-auto">
            <InputBox 
              showtext="請輸入查詢內容..." 
              onSend={handleSend} 
              disabled={loading}
            />
          </div>
        </footer>
      </div>
      <EnglishSettings />
    </div>
  );
};

export default QueryPage;
