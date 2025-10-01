import React, { useState, useRef } from "react";
import { useAppContext } from "../../AppContext";
import { Volume2 } from "lucide-react";


const AudioButton = ({ ttstext, size = 16}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);

  const {
    voice,
    tts,
    speed
  } = useAppContext();

  const handlePlay = async () => {
    if (!ttstext) return;

    if (isPlaying) {
      // 如果正在播放，則停止播放
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        setIsPlaying(false);
      }
      return;
    }

    try {
      const url = `http://localhost:8000/api/v1/pronounce?text=${encodeURIComponent(ttstext)}&voice=${voice}&speed=${speed}&model=${tts}`;
      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onended = () => setIsPlaying(false);
      audio.onerror = () => {
        console.error("音訊播放失敗");
        setIsPlaying(false);
      };

      await audio.play();
      setIsPlaying(true);
    } catch (err) {
      console.error("音訊播放錯誤：", err);
      setIsPlaying(false);
    }
  };

  return (
    <div
      onClick={handlePlay}
      className="cursor-pointer relative group w-6 h-6"
    >
      {/* Tooltip */}
      <div
        className="absolute -top-7 left-1/2 -translate-x-1/2 text-sm px-2 py-1 rounded bg-black text-white whitespace-nowrap 
        opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none z-10"
      >
        大聲朗讀
      </div>

      {/* Icon */}
      <div className="transition-transform duration-300 ease-in-out hover:scale-110" style={{ width: size, height: size }}>
        <Volume2
          className={`transition-all duration-300 ${
            isPlaying ? "text-gray-400" : "text-gray-600 dark:text-slate-50"
          }`}
          size={size}
        />
      </div>
    </div>
  );
};

export default AudioButton;
