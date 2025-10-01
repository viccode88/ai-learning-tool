// components/ThemeToggle.jsx
import { useEffect, useState } from 'react'
import { Sun, Moon } from 'lucide-react'


export default function ThemeToggle({isSidebarOpen}) {
  const [isDark, setIsDark] = useState(false)

  // 初始化：從 localStorage 或 prefers-color-scheme 設定
  useEffect(() => {
    const storedTheme = localStorage.getItem('theme')
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    if (storedTheme === 'dark' || (!storedTheme && prefersDark)) {
      document.documentElement.classList.add('dark')
      setIsDark(true)
    }
  }, [])

  // 切換主題
  const toggleTheme = () => {
    const newTheme = isDark ? 'light' : 'dark'
    localStorage.setItem('theme', newTheme)
    document.documentElement.classList.toggle('dark')
    setIsDark(!isDark)
  }

  return (
    <li onClick={toggleTheme} className="flex w-4/5 items-center pl-4 py-3 rounded-full hover:bg-gray-700 dark:hover:bg-gray-700 transition cursor-pointer"> 
      {isDark ? <Moon size={24} className="text-white" /> : <Sun size={24} className="text-yellow-400" /> }
      <span className={`text-nowrap ml-3 transition-opacity duration-300 ${isSidebarOpen ? 'opacity-100' : 'opacity-0 w-0'}`}>
              {isDark ? "暗色模式" : "亮色模式"}
            </span>
    </li>
  )
} 
