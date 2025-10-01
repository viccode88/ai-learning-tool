// CopyButton.jsx
import React, { useState } from "react";
import { Copy, CopyCheck } from "lucide-react";


const CopyButton = ({ textToCopy }) => {
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(textToCopy || "");
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 3000);
    } catch (err) {
      console.error("複製失敗：", err);
    }
  };

  return (
    <div onClick={handleCopy}
      className="transition-all duration-300 ease-in-out cursor-pointer relative group">
      <div className={`absolute -top-7 left-1/2 -translate-x-1/2 text-sm px-2 py-1 rounded bg-black text-white whitespace-nowrap 
          opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none`}>
        {isCopied ? "已複製!" : "點擊複製"}
      </div>

      <div className="transition-transform duration-300 ease-in-out hover:scale-110">
        {isCopied ? (
          <CopyCheck className="text-black dark:text-gray-400 transition-all duration-300" size={16}/>) : (<Copy className="text-gray-600 dark:text-slate-50 transition-all duration-300" size={16}/>)}
      </div>
    </div>
  );
};

export default CopyButton;
