// src/pages/MathPage.jsx
import React ,{ useState,useEffect } from "react";
import MathShell from "../components/Mathshell";
import { Import } from "lucide-react";
import MathList from "../components/Mathlist";


const MathPage = () => {
  const [selectedProblem, setSelectedProblem] = useState(null); // 目前選擇的對話檔案
  useEffect(() => {
      console.log("selectedProblem:", selectedProblem);
    }, [selectedProblem]);
  return (
    <div className="h-full p-8 dark:text-slate-50 select-none">
      <h1 className="text-2xl font-bold">數學解題</h1>
      <div className="flex w-full h-[81vh]">
        {/* <MathList setSelectedConversation={setSelectedProblem}/> */}
        <MathShell  selectedProblem={selectedProblem}/>
        {/* {selectedProblem ? ( <MathShell selectedProblem={selectedProblem} /> ) : ( <MathShelldefault  selectedProblem={selectedProblem}/> )} */}
      </div>
    </div>
  );
};

export default MathPage;
