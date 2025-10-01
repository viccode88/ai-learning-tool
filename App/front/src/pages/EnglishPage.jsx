// src/pages/EnglishPage.jsx
import React ,{ useState,useEffect } from "react";
import EnglishShelldefault from "../components/Englishshell_default";
import Englishshell from "../components/Englishshell";
import EnglishSettings from "../components/EnglishSettings";
import EnglishList from "../components/Englishlist";


const EnglishPage = () => {
  const [selectedConversation, setSelectedConversation] = useState(null);
  
  useEffect(() => {
    console.log("selectedConversation:", selectedConversation);
  }, [selectedConversation]);
  return (
    <div className="h-full p-8 dark:text-slate-50 select-none">
      <h1 className="text-2xl font-bold">英文對話</h1>
        <div className="p-2 pb-6 flex h-full w-full overflow-hidden">
          <EnglishList setSelectedConversation={setSelectedConversation}/>
          {!selectedConversation ? (
            <EnglishShelldefault setSelectedConversation={setSelectedConversation}/>
          ) : (
            <Englishshell SelectedConversation={selectedConversation}/>
          )}
            <EnglishSettings /> 
        </div>
    </div>
  );
};

export default EnglishPage;
