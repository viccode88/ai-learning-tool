import React, { useState } from "react";
import Button from "./Button";

function InputBox() {
  const [name, setName] = useState("");

  return (
    <div className="flex flex-col items-center space-y-4">
      <input
        type="text"
        placeholder="輸入你的名字"
        className="m-2 border p-2 rounded"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <Button label="提交" onClick={() => alert(`你好, ${name}!`)  } color="bg-green-600"  />
    </div>
  );
}

export default InputBox;
