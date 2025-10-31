import React, { createContext, useContext, useEffect, useState } from "react";

const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [model, setModel] = useState("gpt-5-mini");
  const [mathModel, setMathModel] = useState("gpt-5-mini");
  const [tts, setTts] = useState("tts-1");
  const [voice, setVoice] = useState("alloy");
  const [level, setLevel] = useState("A1");
  const [speed, setSpeed] = useState("normal")

  // 從 localStorage 載入
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("app_prefs") || "{}");
      if (saved.model) setModel(saved.model);
      if (saved.mathModel) setMathModel(saved.mathModel);
      if (saved.tts) setTts(saved.tts);
      if (saved.voice) setVoice(saved.voice);
      if (saved.level) setLevel(saved.level);
      if (saved.speed) setSpeed(saved.speed);
    } catch {}
  }, []);

  // 寫入 localStorage
  useEffect(() => {
    const payload = { model, mathModel, tts, voice, level, speed };
    try {
      localStorage.setItem("app_prefs", JSON.stringify(payload));
    } catch {}
  }, [model, mathModel, tts, voice, level, speed]);

  return (
    <AppContext.Provider
      value={{
        model,
        setModel,
        mathModel,
        setMathModel,
        tts,
        setTts,
        voice,
        setVoice,
        level,
        setLevel,
        speed,
        setSpeed
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => useContext(AppContext);
