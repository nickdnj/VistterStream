import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import {
  HomeIcon,
  CameraIcon,
  PlayIcon,
  FilmIcon,
  Cog6ToothIcon,
  Bars3Icon,
  XMarkIcon,
  UserIcon,
  ArrowRightOnRectangleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isKilling, setIsKilling] = useState(false);
  const { user, logout } = useAuth();
  const location = useLocation();

  const handleEmergencyStop = async () => {
    if (!confirm('🚨 EMERGENCY STOP: Kill all streams and FFmpeg processes?')) {
      return;
    }

    setIsKilling(true);
    try {
      const response = await axios.post('/api/emergency/kill-all-streams');
      alert(`✅ Emergency stop complete!\n\nKilled ${response.data.total_killed} processes:\n${response.data.killed_processes.join('\n')}`);
    } catch (error) {
      console.error('Emergency stop failed:', error);
      alert('❌ Emergency stop failed! Check console for details.');
    } finally {
      setIsKilling(false);
    }
  };

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
    { name: 'Cameras', href: '/cameras', icon: CameraIcon },
    { name: 'Streams', href: '/streams', icon: PlayIcon },
    { name: 'Timelines', href: '/timelines', icon: FilmIcon },
    { name: 'Presets', href: '/presets', icon: Cog6ToothIcon },
    { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
  ];

  const isCurrentPath = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-dark-900">
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 z-50 lg:hidden ${sidebarOpen ? 'block' : 'hidden'}`}>
        <div className="fixed inset-0 bg-dark-900 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 w-64 bg-dark-800 shadow-xl">
          <div className="flex items-center justify-between h-16 px-4 border-b border-dark-700">
            <div className="flex items-center">
              <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center">
                <CameraIcon className="h-5 w-5 text-white" />
              </div>
              <span className="ml-2 text-xl font-bold text-white">VistterStream</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="text-gray-400 hover:text-white"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
          <nav className="mt-4 px-4">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isCurrentPath(item.href)
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-300 hover:bg-dark-700 hover:text-white'
                }`}
                onClick={() => setSidebarOpen(false)}
              >
                <item.icon className="h-5 w-5 mr-3" />
                {item.name}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex flex-col flex-grow bg-dark-800 border-r border-dark-700">
          <div className="flex items-center h-16 px-4 border-b border-dark-700">
            <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <CameraIcon className="h-5 w-5 text-white" />
            </div>
            <span className="ml-2 text-xl font-bold text-white">VistterStream</span>
          </div>
          <nav className="mt-4 flex-1 px-4 space-y-1">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isCurrentPath(item.href)
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-300 hover:bg-dark-700 hover:text-white'
                }`}
              >
                <item.icon className="h-5 w-5 mr-3" />
                {item.name}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <div className="sticky top-0 z-40 bg-dark-800 border-b border-dark-700">
          <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden text-gray-400 hover:text-white"
            >
              <Bars3Icon className="h-6 w-6" />
            </button>
            
            <div className="flex items-center space-x-4">
              {/* Emergency Stop Button */}
              <button
                onClick={handleEmergencyStop}
                disabled={isKilling}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  isKilling
                    ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                    : 'bg-red-600 hover:bg-red-700 text-white'
                }`}
                title="Emergency: Kill all streams and FFmpeg processes"
              >
                <ExclamationTriangleIcon className="h-5 w-5" />
                <span className="hidden sm:inline">
                  {isKilling ? 'Stopping...' : 'Kill All Streams'}
                </span>
              </button>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="h-8 w-8 bg-primary-600 rounded-full flex items-center justify-center">
                  <UserIcon className="h-5 w-5 text-white" />
                </div>
                <div className="hidden sm:block">
                  <p className="text-sm font-medium text-white">{user?.username}</p>
                  <p className="text-xs text-gray-400">Administrator</p>
                </div>
              </div>
              <button
                onClick={logout}
                className="text-gray-400 hover:text-white transition-colors"
                title="Sign out"
              >
                <ArrowRightOnRectangleIcon className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="flex-1">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
