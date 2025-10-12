import React, { useState } from 'react';
import { api } from '../services/api';
import { authService } from '../services/authService';
import { useAuth } from '../contexts/AuthContext';
import PresetManagement from './PresetManagement';
import StreamingDestinations from './StreamingDestinations';
import AssetManagement from './AssetManagement';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

type SettingsTab = 'general' | 'account' | 'presets' | 'assets' | 'destinations' | 'system';

const Settings: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const [isKilling, setIsKilling] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const extractErrorDetail = (error: unknown): string | undefined => {
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string; message?: string } } }).response;
      return response?.data?.detail || response?.data?.message;
    }
    return undefined;
  };

  const handleEmergencyStop = async () => {
    if (!window.confirm('🚨 EMERGENCY STOP: Kill all streams and FFmpeg processes?')) {
      return;
    }

    setIsKilling(true);
    try {
      const response = await api.post('/emergency/kill-all-streams');
      alert(`✅ Emergency stop complete!\n\nKilled ${response.data.total_killed} processes:\n${response.data.killed_processes.join('\n')}`);
    } catch (error) {
      console.error('Emergency stop failed:', error);
      const detail = extractErrorDetail(error);
      alert(`❌ Emergency stop failed${detail ? `: ${detail}` : '! Check console for details.'}`);
    } finally {
      setIsKilling(false);
    }
  };

  const handleChangePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setPasswordMessage(null);

    if (newPassword !== confirmPassword) {
      setPasswordMessage({ type: 'error', text: 'New passwords do not match.' });
      return;
    }

    setPasswordLoading(true);
    try {
      await authService.changePassword(currentPassword, newPassword);
      setPasswordMessage({ type: 'success', text: 'Password updated successfully.' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      console.error('Failed to change password:', error);
      const detail = extractErrorDetail(error);
      setPasswordMessage({ type: 'error', text: detail || 'Failed to update password. Please try again.' });
    } finally {
      setPasswordLoading(false);
    }
  };

  const tabs = [
    { id: 'general' as SettingsTab, name: 'General', icon: '⚙️' },
    { id: 'account' as SettingsTab, name: 'Account', icon: '👤' },
    { id: 'presets' as SettingsTab, name: 'PTZ Presets', icon: '🎯' },
    { id: 'assets' as SettingsTab, name: 'Assets', icon: '🎨' },
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

        {activeTab === 'account' && (
          <div className="bg-dark-800 rounded-lg p-8 border border-dark-700 max-w-3xl">
            <h2 className="text-xl font-semibold text-white mb-2">Account Security</h2>
            <p className="text-gray-400 mb-6">Update the administrator password for this appliance.</p>

            <div className="mb-6">
              <span className="text-sm text-gray-400">Signed in as</span>
              <div className="text-lg text-white font-semibold">{user?.username || 'admin'}</div>
            </div>

            {passwordMessage && (
              <div
                className={`rounded-md p-4 mb-6 border ${passwordMessage.type === 'success' ? 'bg-green-900/20 border-green-500/40 text-green-300' : 'bg-red-900/20 border-red-500/40 text-red-300'}`}
              >
                {passwordMessage.text}
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-4 max-w-xl">
              <div>
                <label htmlFor="current-password" className="block text-sm font-medium text-gray-300 mb-2">Current Password</label>
                <input
                  id="current-password"
                  name="current-password"
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  required
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="new-password" className="block text-sm font-medium text-gray-300 mb-2">New Password</label>
                  <input
                    id="new-password"
                    name="new-password"
                    type="password"
                    autoComplete="new-password"
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    required
                    minLength={6}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-300 mb-2">Confirm Password</label>
                  <input
                    id="confirm-password"
                    name="confirm-password"
                    type="password"
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    required
                    minLength={6}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="submit"
                  disabled={passwordLoading}
                  className="px-5 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {passwordLoading ? 'Saving...' : 'Update Password'}
                </button>
                <span className="text-xs text-gray-500">Password must be at least 6 characters.</span>
              </div>
            </form>
          </div>
        )}

        {activeTab === 'presets' && (
          <div>
            <PresetManagement />
          </div>
        )}

        {activeTab === 'assets' && (
          <div>
            <AssetManagement />
          </div>
        )}

        {activeTab === 'destinations' && (
          <div>
            <StreamingDestinations />
          </div>
        )}

        {activeTab === 'system' && (
          <div className="space-y-6">
            {/* System Information */}
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

            {/* Emergency Controls */}
            <div className="bg-dark-800 rounded-lg p-8 border border-dark-700">
              <h2 className="text-xl font-semibold text-white mb-4">Emergency Controls</h2>
              <p className="text-gray-400 mb-6">
                Use these controls to forcefully stop all streaming processes in case of emergencies.
              </p>
              
              <button
                onClick={handleEmergencyStop}
                disabled={isKilling}
                className={`flex items-center gap-3 px-6 py-3 rounded-lg font-semibold transition-colors ${
                  isKilling
                    ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                    : 'bg-red-600 hover:bg-red-700 text-white'
                }`}
                title="Emergency: Kill all streams and FFmpeg processes"
              >
                <ExclamationTriangleIcon className="h-6 w-6" />
                <div className="text-left">
                  <div className="text-base">
                    {isKilling ? 'Stopping All Processes...' : 'Kill All Streams'}
                  </div>
                  <div className="text-xs opacity-75">
                    Forcefully stop all FFmpeg processes
                  </div>
                </div>
              </button>
              
              <div className="mt-4 p-4 bg-yellow-900/20 border border-yellow-500/30 rounded-md">
                <p className="text-sm text-yellow-400">
                  ⚠️ <strong>Warning:</strong> This will immediately terminate all active streams and FFmpeg processes. 
                  Use only when streams are unresponsive or you need to stop everything quickly.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Settings;
