import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useAppContext } from "../AppContext";
import Dropdown from "./Dropdown";

const fetchModelOptions = async () => {
  try {
    const res = await fetch("http://localhost:8000/api/v1/models");
    const data = await res.json();
    const llmOptions = Object.keys(data.llm || {}).map((m) => ({ label: m, value: m }));
    return { llmOptions };
  } catch (e) {
    console.error("載入模型失敗:", e);
    return { llmOptions: [{ label: "載入失敗", value: "" }] };
  }
};

const selectModel = async ({ feature = "math", llm }) => {
  try {
    const res = await fetch("http://localhost:8000/api/v1/models/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feature, llm }),
    });
    if (!res.ok) throw new Error("切換模型失敗");
  } catch (e) {
    console.error("切換模型失敗:", e);
  }
};

const MathSettings = () => {
  const [isUnfold, setIsUnfold] = useState(false);
  const settingsRef = useRef(null);
  const { mathModel, setMathModel } = useAppContext();
  const [llmOptions, setLLMOptions] = useState([]);

  useEffect(() => {
    const handler = (e) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target)) {
        setIsUnfold(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    fetchModelOptions().then(({ llmOptions }) => {
      setLLMOptions(llmOptions);
      if (!mathModel && llmOptions.length > 0) {
        setMathModel(llmOptions[0].value);
      }
    });
  }, []);

  useEffect(() => {
    if (mathModel) {
      selectModel({ feature: "math", llm: mathModel });
    }
  }, [mathModel]);

  return (
    <div
      ref={settingsRef}
      className={`h-full bg-gray-200 transition-all duration-300 flex-shrink-0 overflow-hidden relative rounded-lg shadow-lg ${
        isUnfold ? "w-64" : "w-10"
      } m-2 rounded-2xl`}
    >
      <div onClick={() => setIsUnfold((p) => !p)} className="m-2 cursor-pointer z-10">
        {isUnfold ? <ChevronLeft size={24} color="black" /> : <ChevronRight size={24} color="black" />}
      </div>

      <div className={`absolute w-full h-full transition-transform duration-300 ${isUnfold ? "translate-x-0" : "translate-x-full"}`}>
        <div className="px-4 text-black space-y-3 mt-4">
          <Dropdown
            options={llmOptions}
            onSelect={(opt) => {
              if (opt.value !== mathModel) setMathModel(opt.value);
            }}
            showtext={"選擇模型"}
            choice={mathModel}
          />
        </div>
      </div>
    </div>
  );
};

export default MathSettings;



