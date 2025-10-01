import React, { useEffect, useState } from "react";


const SettingsPage = () => {
    const [version, setVersion] = useState(null);
    const [health, setHealth] = useState(null);

    useEffect(() => {
        fetch("http://localhost:8000/api/v1/meta/health")
            .then((res) => res.json())
            .then((data) => setHealth(data));
    }, []);

    useEffect(() => {
        fetch("http://localhost:8000/api/v1/meta/version")
            .then((res) => res.json())
            .then((data) => setVersion(data));
    }, []);

    return (
        <div className="p-6 space-y-6 dark:text-slate-50">
            <h1 className="text-3xl font-bold">設定</h1>
            <p className="text-gray-600 dark:text-gray-300 select-none">系統狀態與版本資訊。</p>

            <div className=" bg-gray-200 dark:bg-gray-600 rounded-lg p-4">
                <h2 className="text-xl font-semibold mb-2">✅ 系統狀態</h2>
                {health ? (
                    <p>
                        狀態：<span className="font-mono bg-green-100 text-green-800 px-2 py-1 rounded">{health.status}</span>
                    </p>
                ) : (
                    <p className="select-none">讀取中...</p>
                )}
            </div>

            <div className=" bg-gray-200 dark:bg-gray-600 rounded-lg p-4">
                <h2 className="text-xl font-semibold mb-2">📦 版本資訊</h2>
                {version ? (
                    <ul className="space-y-1">
                        <li>APP版本：<span className="font-mono">{"0.3.2"}</span></li>
                        <li>API版本號：<span className="font-mono">{version.version}</span></li>
                        <li>部署時間：<span className="font-mono">{new Date(version.deployment_time).toLocaleString()}</span></li>
                    </ul>
                ) : (
                    <p className="select-none">讀取中...</p>
                )}
            </div>
        </div>
    );
};

export default SettingsPage;
