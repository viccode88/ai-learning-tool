import React, { useState } from "react";
import Button from './components/Button';

function App() {
    const [message, setMessage] = useState("請點擊按鈕");

    return (
        <div className="flex flex-col items-center justify-center h-screen">
        < h3 className="text-2xl font-bold mb-4">{message}</h3>
        <Button label={message} onClick={() => setMessage("按鈕被點擊")} />
        </div>
    );
}

export default App;
