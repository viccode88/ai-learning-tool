import React, { useState } from "react";
import styled from "styled-components";

const InputBox = ({ showtext, onSend }) => {
  const [input, setInput] = useState("");
  const [sfile, setFile] = useState(null);

  const handleSend = () => {
    if (!input.trim() && !sfile) return;
    // 如果有檔案，則傳送檔案；如果沒有檔案，則只傳送文字
    console.log("送出的訊息:", { text: input.trim(), file: sfile || undefined });
    onSend({ text: input.trim(), file: sfile || undefined });
    setInput("");
    setFile(null);
    document.getElementById("file").value = "";
  };

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (f) {
      // 檢查檔案類型
      const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
      if (!validTypes.includes(f.type)) {
        alert('請上傳 JPEG、PNG 或 WebP 格式的圖片');
        e.target.value = '';
        return;
      }
      setFile(f);
      console.log("上傳檔案:", f);
    } else {
      setFile(null);
      setInput("");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <StyledWrapper>
      <div className="messageBox">
        <label className="fileUploadWrapper" htmlFor="file">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 337 337">
            <circle strokeWidth={20} stroke="#6c6c6c" fill="none" r="158.5" cy="168.5" cx="168.5" />
            <path strokeLinecap="round" strokeWidth={25} stroke="#6c6c6c" d="M167.759 79V259" />
            <path strokeLinecap="round" strokeWidth={25} stroke="#6c6c6c" d="M79 167.138H259" />
          </svg>
          <input 
            type="file" 
            id="file" 
            onChange={handleFileChange} 
            accept=".jpg,.jpeg,.png,.webp"
            hidden 
          />
        </label>

        <input
          id="messageInput"
          type="text"
          placeholder={showtext || "請輸入..."}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />

        <button id="sendButton" onClick={handleSend}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 664 663">
            <path
              strokeLinejoin="round"
              strokeLinecap="round"
              strokeWidth="33.67"
              stroke="#6c6c6c"
              fill="none"
              d="M646.293 331.888L17.7538 17.6187L155.245 331.888M646.293 331.888L17.753 646.157L155.245 331.888M646.293 331.888L318.735 330.228L155.245 331.888"
            />
          </svg>
        </button>
      </div>
    </StyledWrapper>
  );
};

const StyledWrapper = styled.div`
  .messageBox {
    width: 100%;
    height: 40px;
    display: flex;
    align-items: center;
    background-color: #2d2d2d;
    padding: 0 15px;
    border-radius: 10px;
    border: 1px solid rgb(63, 63, 63);
  }

  .messageBox:focus-within {
    border: 1px solid rgb(110, 110, 110);
  }

  .fileUploadWrapper {
    display: flex;
    align-items: center;
    cursor: pointer;
  }

  .fileUploadWrapper svg {
    height: 18px;
  }

  #messageInput {
    flex: 1;
    margin: 0 10px;
    height: 100%;
    background: transparent;
    border: none;
    outline: none;
    color: white;
  }

  #sendButton {
    background: transparent;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
  }

  #sendButton svg {
    height: 18px;
  }
`;

export default InputBox;
