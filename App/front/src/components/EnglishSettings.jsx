import { useState, useRef, useEffect } from "react";
import { useAppContext } from "../AppContext";
import { ChevronLeft, ChevronRight } from "lucide-react";
import Dropdown from "./Dropdown";


const fetchModelOptions = async () => {
  try {
    const res = await fetch("http://localhost:8000/api/v1/models");
    const data = await res.json();

    const llmOptions = Object.keys(data.llm || {}).map((model) => ({
      label: model,
      value: model,
    }));
    const ttsOptions = Object.keys(data.tts || {}).map((model) => ({
      label: model,
      value: model,
    }));

    return { llmOptions, ttsOptions, ttsData: data.tts };
  } catch (error) {
    console.error("載入模型失敗:", error);
    return {
      llmOptions: [{ label: "載入失敗", value: "" }],
      ttsOptions: [],
      ttsData: {},
    };
  }
};

const selectModel = async ({ llm, tts, tts_voice }) => {
  try {
    const payload = { llm, tts, tts_voice };
    console.log("selectModel payload:", payload);
    const res = await fetch("http://localhost:8000/api/v1/models/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("切換模型失敗");
    console.log("模型切換成功");
  } catch (error) {
    console.error("模型切換失敗:", error);
  }
};

const EnglishSettings = () => {
  const [isUnfold, setIsUnfold] = useState(false);
  const settingsRef = useRef(null);

  const {
    model, setModel,
    tts, setTts,
    voice, setVoice,
    level, setLevel,
  } = useAppContext();

  const [llmOptions, setLLMOptions] = useState([]);
  const [ttsOptions, setTTSOptions] = useState([]);
  const [ttsData, setTTSData] = useState({});
  const [voiceOptions, setVoiceOptions] = useState([]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target)) {
        setIsUnfold(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    fetchModelOptions().then(({ llmOptions, ttsOptions, ttsData }) => {
      setLLMOptions(llmOptions);
      setTTSOptions(ttsOptions);
      setTTSData(ttsData);

      // 如果尚未設定，就預設為第一個值
      if (!model && llmOptions.length > 0) setModel(llmOptions[0].value);
      if (!tts && ttsOptions.length > 0) setTts(ttsOptions[0].value);
    });
  }, []);

  useEffect(() => {
    if (tts && typeof tts === "string" && ttsData[tts]?.voices) {
      const voices = ttsData[tts].voices.map((v) => ({ label: v, value: v }));
      setVoiceOptions(voices);

      // 如果 voice 尚未設定或不是合法選項，預設為第一個
      if (!voice || !ttsData[tts].voices.includes(voice)) {
        setVoice(ttsData[tts].voices[0] || "");
      }
    } else {
      setVoiceOptions([]);
    }
  }, [tts, ttsData]);

  useEffect(() => {
    if (model && tts && voice) {
      selectModel({ llm: model, tts, tts_voice: voice });
    }
  }, [model, tts, voice]);

  const levelOptions = ["A1", "A2", "B1", "B2", "C1", "C2"].map((lvl) => ({
    label: lvl,
    value: lvl,
  }));

  return (
    <div
      ref={settingsRef}
      className={`h-full bg-gray-200 transition-all duration-300 flex-shrink-0 overflow-hidden relative rounded-lg shadow-lg
        ${isUnfold ? "w-64" : "w-10"} m-2 rounded-2xl`}
    >
      <div onClick={() => setIsUnfold((prev) => !prev)} className="m-2 cursor-pointer z-10">
        {isUnfold ? <ChevronLeft size={24} color="black" /> : <ChevronRight size={24} color="black" />}
      </div>

      <div className={`absolute w-full h-full transition-transform duration-300 ${isUnfold ? "translate-x-0" : "translate-x-full"}`}>
        <div className="px-4 text-black space-y-3 mt-4">
          <Dropdown
            options={levelOptions}
            onSelect={(opt) => {
              if (opt.value !== level) setLevel(opt.value);
            }}
            showtext="CEFR 等級"
            choice={level}
          />
          <Dropdown
            options={llmOptions}
            onSelect={(opt) => {
              if (opt.value !== model) setModel(opt.value);
            }}
            showtext={"選擇模型"}
            choice={model}
          />
          <Dropdown
            options={ttsOptions}
            onSelect={(opt) => {
              if (opt.value !== tts) setTts(opt.value);
            }}
            showtext="選擇 TTS"
            choice={tts}
          />
          <Dropdown
            options={voiceOptions}
            onSelect={(opt) => {
              if (opt.value !== voice) setVoice(opt.value);
            }}
            showtext="選擇聲音"
            choice={voice}
          />
        </div>
      </div>
    </div>
  );
};

export default EnglishSettings;
