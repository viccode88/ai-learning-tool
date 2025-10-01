import { useState, useRef, useEffect } from "react";
import { ChevronUp, ChevronDown } from 'lucide-react';
import { useAppContext } from "../AppContext";

const Dropdown = ({ options, onSelect, showtext = "請選擇", choice }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [resolvedOptions, setResolvedOptions] = useState([]);
  const dropdownRef = useRef(null);

  const handleSelect = (option) => {
    setSelected(option);
    setIsOpen(false);
    onSelect?.(option);
  };

  // ✅ 處理 async function 傳入的 options
  useEffect(() => {
    const loadOptions = async () => {
      if (typeof options === "function") {
        try {
          const result = await options();
          setResolvedOptions(result);
        } catch (error) {
          console.error("載入 options 失敗:", error);
          setResolvedOptions([{ label: "載入失敗", value: "" }]);
        }
      } else {
        setResolvedOptions(options);
      }
    };
    loadOptions();
  }, [options]);

  // 關閉選單功能
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  return (
    <div className="relative inline-block w-full" ref={dropdownRef}>
      <label className="whitespace-nowrap overflow-hidden text-ellipsis">
        {showtext}
      </label>
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex justify-between items-center w-full bg-white border border-gray-300 rounded-lg shadow-sm px-4 py-2 text-left whitespace-nowrap"
      >
        <span>{selected ? selected.label : choice}</span>
        {isOpen ? (
          <ChevronUp size={24} color="black" className="ml-2" />
        ) : (
          <ChevronDown size={24} color="black" className="ml-2" />
        )}
      </div>

      {isOpen && (
        <ul className="absolute mt-1 w-full bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto z-10">
          {resolvedOptions.map((option) => (
            <li
              key={option.value}
              onClick={() => handleSelect(option)}
              className="px-4 py-2 hover:bg-blue-100 cursor-pointer"
            >
              {option.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default Dropdown;
