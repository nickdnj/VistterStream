import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  HomeIcon,
  CameraIcon,
  FilmIcon,
  Cog6ToothIcon,
  Bars3Icon,
  XMarkIcon,
  UserIcon,
  ArrowRightOnRectangleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { user, logout } = useAuth();
  const location = useLocation();

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
    { name: 'Timelines', href: '/timelines', icon: FilmIcon },
    { name: 'ReelForge', href: '/reelforge', icon: SparklesIcon },
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
      <div className={`hidden lg:fixed lg:inset-y-0 lg:flex lg:flex-col transition-all duration-300 ${
        sidebarCollapsed ? 'lg:w-20' : 'lg:w-64'
      }`}>
        <div className="flex flex-col flex-grow bg-dark-800 border-r border-dark-700">
          <div className="flex items-center justify-between h-16 px-4 border-b border-dark-700">
            <div className="flex items-center overflow-hidden">
              <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center flex-shrink-0">
                <CameraIcon className="h-5 w-5 text-white" />
              </div>
              {!sidebarCollapsed && (
                <span className="ml-2 text-xl font-bold text-white whitespace-nowrap">VistterStream</span>
              )}
            </div>
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="text-gray-400 hover:text-white transition-colors flex-shrink-0"
              title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {sidebarCollapsed ? (
                <ChevronRightIcon className="h-5 w-5" />
              ) : (
                <ChevronLeftIcon className="h-5 w-5" />
              )}
            </button>
          </div>
          <nav className="mt-4 flex-1 px-2 space-y-1">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center ${sidebarCollapsed ? 'justify-center px-3' : 'px-3'} py-3 rounded-lg text-sm font-medium transition-colors ${
                  isCurrentPath(item.href)
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-300 hover:bg-dark-700 hover:text-white'
                }`}
                title={sidebarCollapsed ? item.name : undefined}
              >
                <item.icon className={`h-5 w-5 flex-shrink-0 ${sidebarCollapsed ? '' : 'mr-3'}`} />
                {!sidebarCollapsed && <span className="whitespace-nowrap">{item.name}</span>}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      {/* Main content */}
      <div className={`flex flex-col h-screen transition-all duration-300 ${sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-64'}`}>
        {/* Top bar */}
        <div className="sticky top-0 z-40 bg-dark-800 border-b border-dark-700">
          <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden text-gray-400 hover:text-white"
            >
              <Bars3Icon className="h-6 w-6" />
            </button>
            
            <div className="flex-1"></div>
            
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
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
