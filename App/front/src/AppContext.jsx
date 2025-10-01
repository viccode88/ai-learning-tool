import React, { createContext, useContext, useState } from "react";

const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [model, setModel] = useState("gpt-4o");
  const [tts, setTts] = useState("tts-1");
  const [voice, setVoice] = useState("alloy");
  const [level, setLevel] = useState("A1");
  const [speed, setSpeed] = useState("normal")

  return (
    <AppContext.Provider
      value={{
        model,
        setModel,
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
