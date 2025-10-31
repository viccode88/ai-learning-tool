import React, { useState, useEffect } from "react";
import styled from "styled-components";

const InputBox = ({ showtext, onSendMessage, onSend, disabled = false }) => {
  const [input, setInput] = useState("");
  const [sfile, setFile] = useState(null);
  const [preview, setPreview] = useState(null);

  const handleSend = () => {
    if (disabled || (!input.trim() && !sfile)) return;
    console.log("送出的訊息:", { text: input.trim(), file: sfile || undefined });
    if (onSend) {
      // 現代用法：統一以物件傳遞，滿足 Mathshell/QueryPage/MathBox 的需求
      onSend({ text: input.trim(), file: sfile || undefined });
    } else if (onSendMessage) {
      // 舊用法：維持相容（英文對話建立期望字串參數）
      onSendMessage(input.trim(), sfile);
    }
    setInput("");
    setFile(null);
    setPreview(null);
    const fileInput = document.getElementById("file");
    if (fileInput) fileInput.value = "";
  };

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (f) {
      const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];
      if (!validTypes.includes(f.type)) {
        alert('請上傳 JPEG、PNG 或 WebP 格式的圖片');
        e.target.value = '';
        return;
      }
      setFile(f);
      // 生成預覽圖
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(f);
      console.log("上傳檔案:", f);
    } else {
      setFile(null);
      setPreview(null);
    }
  };

  const handleRemoveFile = () => {
    setFile(null);
    setPreview(null);
    const fileInput = document.getElementById("file");
    if (fileInput) fileInput.value = "";
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <StyledWrapper>
      {preview && (
        <div className="imagePreview">
          <img src={preview} alt="預覽" />
          <button 
            className="removeButton" 
            onClick={handleRemoveFile}
            disabled={disabled}
            title="移除圖片"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      )}
      <div className={`messageBox ${disabled ? 'disabled' : ''}`}>
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
            disabled={disabled}
            hidden 
          />
        </label>

        <input
          id="messageInput"
          type="text"
          placeholder={disabled ? "發送中..." : (showtext || "請輸入你想聊的...")}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
        />

        <button id="sendButton" onClick={handleSend} disabled={disabled}>
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
  position: relative;

  .imagePreview {
    position: relative;
    margin-bottom: 8px;
    display: inline-block;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    background: #1a1a1a;
  }

  .imagePreview img {
    display: block;
    max-width: 200px;
    max-height: 150px;
    object-fit: contain;
    border-radius: 8px;
  }

  .removeButton {
    position: absolute;
    top: 4px;
    right: 4px;
    background: rgba(0, 0, 0, 0.7);
    border: none;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
    color: white;
  }

  .removeButton:hover {
    background: rgba(220, 38, 38, 0.9);
    transform: scale(1.1);
  }

  .removeButton:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .removeButton svg {
    width: 14px;
    height: 14px;
  }

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

  .messageBox.disabled {
    opacity: 0.6;
    cursor: not-allowed;
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

  #messageInput:disabled {
    cursor: not-allowed;
  }

  #sendButton {
    background: transparent;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
  }

  #sendButton:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }

  #sendButton svg {
    height: 18px;
  }
`;

export default InputBox;
