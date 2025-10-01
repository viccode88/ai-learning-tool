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

  return (
    <div className="flex h-full w-full dark:text-slate-50">
      <div className="flex flex-col h-full w-full dark:text-slate-50 ">
        <div className="p-8 max-w-3xl mx-auto w-full">
          <h1 className="text-2xl font-bold">單字/片語查詢</h1>
        </div>
        <div className="flex-1 overflow-y-auto p-4 w-full max-w-3xl mx-auto min-w-max select-none">
          {loading && <div className="mt-4 ">查詢中...</div>}
          {error && <div className="mt-4 text-red-500 select-text">錯誤：{error}</div>}

          {!loading && !error && queryword && (
            <div className="m-6">
              <h2 className="text-4xl font-bold mb-2 select-text">
                {queryword} <span className="text-lg italic">{ipa}</span> <span><AudioButton ttstext={queryword} size={18} className="pl-8 pt-8"/></span>
              </h2>

              {translation && (
                <div className="mb-4 text-xl text-gray-700 select-text">翻譯：{translation}</div>
              )}

              {audioUrl && (
                <div className="mb-4">
                  <audio controls src={audioUrl}>
                    Your browser does not support the audio element.
                  </audio>
                </div>
              )}

              {definitions.length > 0 && (
                <div className="mb-4">
                  <h3 className="font-semibold text-xl mb-1 select-text">定義</h3>
                  <ul className="list-disc ml-6 select-text" >
                    {definitions.map((def, i) => (
                      <li key={i}>
                        {def.pos ? `(${def.pos}) ` : ""}
                        {def.text}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {examples.length > 0 && (
                <div className="mb-4">
                  <h3 className="font-semibold text-xl mb-1">例句</h3>
                  <ul className="list-disc ml-6 select-text">
                    {examples.map((ex, i) => (
                      <li key={i}>
                        {ex.text}{" "}
                        {ex.level && (
                          <span className="text-sm text-gray-400">[{ex.level}]</span>
                        )}
                        <AudioButton ttstext={ex.text} size={18} className="pl-8 pt-8"/>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {grammarTips && (
                <div className="mb-4 select-text">
                  <h3 className="font-semibold text-xl mb-1">文法提示</h3>
                  <p>{grammarTips}</p>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="max-w-3xl mx-auto w-full pb-6">
          <InputBox showtext="請輸入查詢內容" onSend={handleSend} />
        </div>
      </div>
      <EnglishSettings/> 
    </div>
  );
};

export default QueryPage;
