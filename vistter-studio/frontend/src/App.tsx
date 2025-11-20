import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { Monitor, Radio, FileVideo, Settings } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-900 text-white">
        {/* Sidebar */}
        <div className="fixed left-0 top-0 h-full w-64 bg-slate-800 border-r border-slate-700">
          <div className="p-6">
            <h1 className="text-2xl font-bold text-blue-400">VistterStudio</h1>
            <p className="text-sm text-slate-400 mt-1">Desktop Control</p>
          </div>

          <nav className="mt-6">
            <Link
              to="/"
              className="flex items-center gap-3 px-6 py-3 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              <Monitor size={20} />
              <span>Dashboard</span>
            </Link>
            <Link
              to="/control"
              className="flex items-center gap-3 px-6 py-3 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              <Radio size={20} />
              <span>Remote Control</span>
            </Link>
            <Link
              to="/timelines"
              className="flex items-center gap-3 px-6 py-3 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              <FileVideo size={20} />
              <span>Timelines</span>
            </Link>
            <Link
              to="/settings"
              className="flex items-center gap-3 px-6 py-3 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              <Settings size={20} />
              <span>Settings</span>
            </Link>
          </nav>
        </div>

        {/* Main Content */}
        <div className="ml-64 p-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/control" element={<div>Remote Control (Coming Soon)</div>} />
            <Route path="/timelines" element={<div>Timelines (Coming Soon)</div>} />
            <Route path="/settings" element={<div>Settings (Coming Soon)</div>} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}

export default App
