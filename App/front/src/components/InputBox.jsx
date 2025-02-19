import React, { useState } from "react";
import Button from "./Button";

function InputBox() {
  const [name, setName] = useState("");

  return (
    <div className="flex flex-col items-center space-y-4">
      <input
        type="text"
        placeholder="輸入你的名字"
        className="border p-2 rounded"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <Button label="提交" onClick={() => alert(`你好, ${name}!`)} />
    </div>
  );
}

export default InputBox;
