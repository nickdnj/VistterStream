import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { authService } from '../services/authService';
import { useAuth } from '../contexts/AuthContext';
import PresetManagement from './PresetManagement';
import StreamingDestinations from './StreamingDestinations';
import AssetManagement from './AssetManagement';
import CameraManagement from './CameraManagement';
import Scheduler from './Scheduler';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

type SettingsTab = 'general' | 'account' | 'cameras' | 'scheduler' | 'presets' | 'assets' | 'destinations' | 'dashboard' | 'system';

interface GeneralSettings {
  appliance_name: string;
  timezone: string;
  state_name: string;
  city: string;
  latitude: number | null;
  longitude: number | null;
}

const Settings: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const [isKilling, setIsKilling] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  
  // General settings state
  const [generalSettings, setGeneralSettings] = useState<GeneralSettings>({
    appliance_name: 'VistterStream Appliance',
    timezone: 'America/New_York',
    state_name: '',
    city: '',
    latitude: null,
    longitude: null,
  });
  const [generalSettingsLoading, setGeneralSettingsLoading] = useState(false);
  const [generalSettingsSaving, setGeneralSettingsSaving] = useState(false);
  const [generalSettingsMessage, setGeneralSettingsMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [locationDetecting, setLocationDetecting] = useState(false);

  const extractErrorDetail = (error: unknown): string | undefined => {
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string; message?: string } } }).response;
      return response?.data?.detail || response?.data?.message;
    }
    return undefined;
  };

  // Load general settings on mount
  useEffect(() => {
    loadGeneralSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadGeneralSettings = async () => {
    setGeneralSettingsLoading(true);
    try {
      const response = await api.get('/settings/');
      setGeneralSettings({
        appliance_name: response.data.appliance_name || 'VistterStream Appliance',
        timezone: response.data.timezone || 'America/New_York',
        state_name: response.data.state_name || '',
        city: response.data.city || '',
        latitude: response.data.latitude || null,
        longitude: response.data.longitude || null,
      });
      
      // Auto-detect location if not already set
      if (!response.data.latitude || !response.data.longitude) {
        detectLocation();
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
      // Try to detect location anyway
      detectLocation();
    } finally {
      setGeneralSettingsLoading(false);
    }
  };

  const detectLocation = () => {
    if (!navigator.geolocation) {
      console.warn('Geolocation not supported by browser');
      return;
    }

    setLocationDetecting(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        
        try {
          // Reverse geocode using OpenStreetMap Nominatim
          const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`
          );
          const data = await response.json();
          
          const state_name = data.address?.state || '';
          const city = data.address?.city || data.address?.town || data.address?.village || '';
          
          setGeneralSettings((prev) => ({
            ...prev,
            latitude,
            longitude,
            city,
            state_name,
          }));
          
          console.log('Location detected:', { city, state_name, latitude, longitude });
        } catch (error) {
          console.error('Reverse geocoding failed:', error);
          // Still set lat/lon even if reverse geocoding fails
          setGeneralSettings((prev) => ({
            ...prev,
            latitude,
            longitude,
          }));
        } finally {
          setLocationDetecting(false);
        }
      },
      (error) => {
        console.warn('Location detection failed:', error.message);
        setLocationDetecting(false);
      }
    );
  };

  const handleSaveGeneralSettings = async (event: React.FormEvent) => {
    event.preventDefault();
    setGeneralSettingsMessage(null);
    setGeneralSettingsSaving(true);

    try {
      await api.post('/settings/', generalSettings);
      setGeneralSettingsMessage({ type: 'success', text: 'Settings saved successfully. Location synced to all assets.' });
    } catch (error) {
      console.error('Failed to save settings:', error);
      const detail = extractErrorDetail(error);
      setGeneralSettingsMessage({ type: 'error', text: detail || 'Failed to save settings. Please try again.' });
    } finally {
      setGeneralSettingsSaving(false);
    }
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
    { id: 'cameras' as SettingsTab, name: 'Cameras', icon: '📷' },
    { id: 'scheduler' as SettingsTab, name: 'Scheduler', icon: '📅' },
    { id: 'presets' as SettingsTab, name: 'PTZ Presets', icon: '🎯' },
    { id: 'assets' as SettingsTab, name: 'Assets', icon: '🎨' },
    { id: 'destinations' as SettingsTab, name: 'Destinations', icon: '📡' },
    { id: 'dashboard' as SettingsTab, name: 'Dashboard', icon: '📊' },
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
          <div className="bg-dark-800 rounded-lg p-8 border border-dark-700 max-w-3xl">
            <h2 className="text-xl font-semibold text-white mb-2">General Settings</h2>
            <p className="text-gray-400 mb-6">Configure system-wide settings and location information.</p>

            {generalSettingsMessage && (
              <div
                className={`rounded-md p-4 mb-6 border ${generalSettingsMessage.type === 'success' ? 'bg-green-900/20 border-green-500/40 text-green-300' : 'bg-red-900/20 border-red-500/40 text-red-300'}`}
              >
                {generalSettingsMessage.text}
              </div>
            )}

            {generalSettingsLoading ? (
              <div className="text-gray-400 text-center py-8">Loading settings...</div>
            ) : (
              <form onSubmit={handleSaveGeneralSettings} className="space-y-6">
                {/* System Configuration */}
                <div>
                  <h3 className="text-lg font-medium text-white mb-4">System Configuration</h3>
                  <div className="space-y-4">
                    <div>
                      <label htmlFor="appliance-name" className="block text-sm font-medium text-gray-300 mb-2">
                        Appliance Name
                      </label>
                      <input
                        id="appliance-name"
                        type="text"
                        value={generalSettings.appliance_name}
                        onChange={(e) => setGeneralSettings({ ...generalSettings, appliance_name: e.target.value })}
                        className="w-full max-w-md px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                    
                    <div>
                      <label htmlFor="timezone" className="block text-sm font-medium text-gray-300 mb-2">
                        Timezone
                      </label>
                      <select
                        id="timezone"
                        value={generalSettings.timezone}
                        onChange={(e) => setGeneralSettings({ ...generalSettings, timezone: e.target.value })}
                        className="w-full max-w-md px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      >
                        <option value="America/New_York">America/New_York (EST/EDT)</option>
                        <option value="America/Chicago">America/Chicago (CST/CDT)</option>
                        <option value="America/Denver">America/Denver (MST/MDT)</option>
                        <option value="America/Los_Angeles">America/Los_Angeles (PST/PDT)</option>
                        <option value="America/Phoenix">America/Phoenix (MST)</option>
                        <option value="America/Anchorage">America/Anchorage (AKST/AKDT)</option>
                        <option value="Pacific/Honolulu">Pacific/Honolulu (HST)</option>
                        <option value="UTC">UTC</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Location Information */}
                <div>
                  <h3 className="text-lg font-medium text-white mb-2">Location Information</h3>
                  <p className="text-sm text-gray-400 mb-4">
                    📍 Location auto-detected where possible. You can override manually. Changes sync to all assets.
                  </p>
                  
                  {locationDetecting && (
                    <div className="mb-4 p-3 bg-blue-900/20 border border-blue-500/40 rounded-md text-blue-300 text-sm">
                      🔍 Detecting your location...
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="city" className="block text-sm font-medium text-gray-300 mb-2">
                        City
                      </label>
                      <input
                        id="city"
                        type="text"
                        value={generalSettings.city}
                        onChange={(e) => setGeneralSettings({ ...generalSettings, city: e.target.value })}
                        placeholder="e.g., San Francisco"
                        className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                    
                    <div>
                      <label htmlFor="state" className="block text-sm font-medium text-gray-300 mb-2">
                        State / Province
                      </label>
                      <input
                        id="state"
                        type="text"
                        value={generalSettings.state_name}
                        onChange={(e) => setGeneralSettings({ ...generalSettings, state_name: e.target.value })}
                        placeholder="e.g., California"
                        className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                    
                    <div>
                      <label htmlFor="latitude" className="block text-sm font-medium text-gray-300 mb-2">
                        Latitude
                      </label>
                      <input
                        id="latitude"
                        type="number"
                        step="any"
                        value={generalSettings.latitude ?? ''}
                        onChange={(e) => setGeneralSettings({ ...generalSettings, latitude: e.target.value ? parseFloat(e.target.value) : null })}
                        placeholder="Auto-detected"
                        className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        readOnly
                      />
                    </div>
                    
                    <div>
                      <label htmlFor="longitude" className="block text-sm font-medium text-gray-300 mb-2">
                        Longitude
                      </label>
                      <input
                        id="longitude"
                        type="number"
                        step="any"
                        value={generalSettings.longitude ?? ''}
                        onChange={(e) => setGeneralSettings({ ...generalSettings, longitude: e.target.value ? parseFloat(e.target.value) : null })}
                        placeholder="Auto-detected"
                        className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        readOnly
                      />
                    </div>
                  </div>

                  <div className="mt-3">
                    <button
                      type="button"
                      onClick={detectLocation}
                      disabled={locationDetecting}
                      className="text-sm text-primary-400 hover:text-primary-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {locationDetecting ? '🔍 Detecting...' : '🔄 Re-detect Location'}
                    </button>
                  </div>
                </div>

                {/* Save Button */}
                <div className="flex items-center gap-3 pt-4 border-t border-dark-700">
                  <button
                    type="submit"
                    disabled={generalSettingsSaving}
                    className="px-5 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    {generalSettingsSaving ? 'Saving...' : 'Save Settings'}
                  </button>
                </div>
              </form>
            )}
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

        {activeTab === 'cameras' && (
          <div>
            <CameraManagement />
          </div>
        )}

        {activeTab === 'scheduler' && (
          <div>
            <Scheduler />
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

        {activeTab === 'dashboard' && (
          <div className="bg-dark-800 rounded-lg p-8 border border-dark-700 max-w-3xl">
            <h2 className="text-xl font-semibold text-white mb-2">Dashboard Metrics</h2>
            <p className="text-gray-400 mb-6">Customize which metrics are displayed on your dashboard.</p>

            <div className="space-y-4">
              <div className="flex items-center justify-between py-3 border-b border-dark-700">
                <div>
                  <p className="text-sm font-medium text-white">Show Memory Usage</p>
                  <p className="text-xs text-gray-400 mt-1">Display system RAM usage percentage</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={localStorage.getItem('dashboard_show_memory') !== 'false'}
                    onChange={(e) => {
                      localStorage.setItem('dashboard_show_memory', e.target.checked.toString());
                      window.location.reload();
                    }}
                  />
                  <div className="w-11 h-6 bg-dark-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-800 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>

              <div className="flex items-center justify-between py-3 border-b border-dark-700">
                <div>
                  <p className="text-sm font-medium text-white">Show Network Usage</p>
                  <p className="text-xs text-gray-400 mt-1">Display network throughput as % of 100 Mbps</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={localStorage.getItem('dashboard_show_network') !== 'false'}
                    onChange={(e) => {
                      localStorage.setItem('dashboard_show_network', e.target.checked.toString());
                      window.location.reload();
                    }}
                  />
                  <div className="w-11 h-6 bg-dark-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-800 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>

              <div className="flex items-center justify-between py-3 border-b border-dark-700">
                <div>
                  <p className="text-sm font-medium text-white">Show Disk Usage</p>
                  <p className="text-xs text-gray-400 mt-1">Display storage space usage percentage</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={localStorage.getItem('dashboard_show_disk') !== 'false'}
                    onChange={(e) => {
                      localStorage.setItem('dashboard_show_disk', e.target.checked.toString());
                      window.location.reload();
                    }}
                  />
                  <div className="w-11 h-6 bg-dark-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-800 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>
            </div>

            <div className="mt-6 p-4 bg-blue-900/20 border border-blue-500/30 rounded-md">
              <p className="text-sm text-blue-300">
                ℹ️ <strong>Note:</strong> Changes to dashboard metrics will take effect after a page refresh.
              </p>
            </div>
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
