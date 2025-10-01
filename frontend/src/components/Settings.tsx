import React, { useState } from 'react';
import PresetManagement from './PresetManagement';
import StreamingDestinations from './StreamingDestinations';

type SettingsTab = 'general' | 'presets' | 'destinations' | 'system';

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');

  const tabs = [
    { id: 'general' as SettingsTab, name: 'General', icon: '⚙️' },
    { id: 'presets' as SettingsTab, name: 'PTZ Presets', icon: '🎯' },
    { id: 'destinations' as SettingsTab, name: 'Destinations', icon: '📡' },
    { id: 'system' as SettingsTab, name: 'System', icon: '💻' },
  ];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="mt-2 text-gray-400">Configure your VistterStream appliance</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-dark-700 mb-6">
        <nav className="flex space-x-8" aria-label="Settings tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm transition-colors
                ${activeTab === tab.id
                  ? 'border-primary-500 text-primary-500'
                  : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-300'
                }
              `}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'general' && (
          <div className="bg-dark-800 rounded-lg p-8 border border-dark-700">
            <h2 className="text-xl font-semibold text-white mb-4">General Settings</h2>
            <p className="text-gray-400">System configuration options coming soon...</p>
            
            <div className="mt-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Appliance Name
                </label>
                <input
                  type="text"
                  placeholder="VistterStream Appliance"
                  className="w-full max-w-md px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  disabled
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Timezone
                </label>
                <select
                  className="w-full max-w-md px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  disabled
                >
                  <option>America/New_York</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'presets' && (
          <div>
            <PresetManagement />
          </div>
        )}

        {activeTab === 'destinations' && (
          <div>
            <StreamingDestinations />
          </div>
        )}

        {activeTab === 'system' && (
          <div className="bg-dark-800 rounded-lg p-8 border border-dark-700">
            <h2 className="text-xl font-semibold text-white mb-4">System Information</h2>
            <div className="space-y-4 text-sm">
              <div className="flex justify-between py-2 border-b border-dark-700">
                <span className="text-gray-400">Version:</span>
                <span className="text-white font-mono">1.0.0-beta</span>
              </div>
              <div className="flex justify-between py-2 border-b border-dark-700">
                <span className="text-gray-400">Platform:</span>
                <span className="text-white font-mono">macOS</span>
              </div>
              <div className="flex justify-between py-2 border-b border-dark-700">
                <span className="text-gray-400">Database:</span>
                <span className="text-white font-mono">SQLite</span>
              </div>
              <div className="flex justify-between py-2 border-b border-dark-700">
                <span className="text-gray-400">FFmpeg:</span>
                <span className="text-white font-mono">7.1.1</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Settings;
