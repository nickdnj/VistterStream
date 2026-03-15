import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { PhotoIcon, SwatchIcon, PaintBrushIcon, ChartBarIcon } from '@heroicons/react/24/outline';
import AssetLibrary from './AssetLibrary';
import TemplateCatalog from './TemplateCatalog';

const tabs = [
  { name: 'My Assets', path: '/assets', icon: PhotoIcon },
  { name: 'Templates', path: '/assets/templates', icon: SwatchIcon },
  { name: 'Canvas Editor', path: '/assets/editor', icon: PaintBrushIcon },
  { name: 'Analytics', path: '/assets/analytics', icon: ChartBarIcon, disabled: true },
];

const AssetStudio: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const activeTab = tabs.find(t => t.path === location.pathname) || tabs[0];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Asset Studio</h1>
        <p className="text-sm text-gray-400 mt-1">Create and manage stream overlays</p>
      </div>

      {/* Tab bar */}
      <div className="flex space-x-1 border-b border-dark-700 mb-6">
        {tabs.map((tab) => {
          const isActive = tab.path === activeTab.path;
          return (
            <button
              key={tab.name}
              onClick={() => !tab.disabled && navigate(tab.path)}
              disabled={tab.disabled}
              className={`flex items-center px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                isActive
                  ? 'border-primary-500 text-primary-400'
                  : tab.disabled
                    ? 'border-transparent text-gray-600 cursor-not-allowed'
                    : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-dark-600'
              }`}
            >
              <tab.icon className="h-4 w-4 mr-2" />
              {tab.name}
              {tab.disabled && (
                <span className="ml-2 text-xs bg-dark-700 text-gray-500 px-2 py-0.5 rounded-full">
                  Soon
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {activeTab.path === '/assets' && <AssetLibrary />}
      {activeTab.path === '/assets/templates' && <TemplateCatalog />}
      {activeTab.path === '/assets/editor' && (
        <div className="text-center py-20">
          <PaintBrushIcon className="h-16 w-16 text-gray-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-300 mb-2">Canvas Editor</h2>
          <p className="text-gray-500 mb-6">Create custom overlay graphics with the built-in editor</p>
          <button
            onClick={() => navigate('/assets/editor/new')}
            className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
          >
            New Canvas Project
          </button>
        </div>
      )}
    </div>
  );
};

export default AssetStudio;
