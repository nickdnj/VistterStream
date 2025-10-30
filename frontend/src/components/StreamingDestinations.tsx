import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import { AxiosError } from 'axios';


interface Destination {
  id?: number;
  name: string;
  platform: string;
  rtmp_url: string;
  stream_key: string;
  description: string;
  channel_id?: string;
  is_active?: boolean;
  created_at?: string;
  last_used?: string;
  // YouTube Watchdog fields
  enable_watchdog?: boolean;
  youtube_api_key?: string;
  youtube_stream_id?: string;
  youtube_broadcast_id?: string;
  youtube_watch_url?: string;
  watchdog_check_interval?: number;
  watchdog_enable_frame_probe?: boolean;
  watchdog_enable_daily_reset?: boolean;
  watchdog_daily_reset_hour?: number;
  youtube_oauth_connected?: boolean;
  youtube_token_expires_at?: string | null;
  youtube_oauth_scopes?: string | null;
}

interface PlatformPreset {
  name: string;
  rtmp_url: string;
  description: string;
}

const TooltipIcon: React.FC<{ label: string; tooltip: string }> = ({ label, tooltip }) => (
  <div className="relative group flex items-center justify-center">
    <button
      type="button"
      className="text-gray-400 hover:text-gray-200 focus:text-gray-200 focus:outline-none"
      aria-label={tooltip}
    >
      {label}
    </button>
    <div className="pointer-events-none absolute bottom-full left-1/2 mb-2 hidden w-64 -translate-x-1/2 rounded bg-black px-3 py-2 text-xs text-gray-100 shadow-lg group-hover:block group-focus-within:block">
      {tooltip}
    </div>
  </div>
);

const StreamingDestinations: React.FC = () => {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [presets, setPresets] = useState<Record<string, PlatformPreset>>({});
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingDestination, setEditingDestination] = useState<Destination | null>(null);
  const [showStreamKey, setShowStreamKey] = useState<Record<number, boolean>>({});
  const pollingRef = useRef<Record<number, number>>({});

  const [oauthEnvDraft, setOauthEnvDraft] = useState<{ clientId: string; clientSecret: string; redirectUri: string }>({
    clientId: '',
    clientSecret: '',
    redirectUri: ''
  });

  const [newDestination, setNewDestination] = useState<Destination>({
    name: '',
    platform: 'youtube',
    rtmp_url: '',
    stream_key: '',
    description: '',
    channel_id: '',
    youtube_stream_id: '',
    youtube_broadcast_id: '',
    youtube_watch_url: '',
    youtube_api_key: '',
    enable_watchdog: false,
    watchdog_check_interval: 30,
    watchdog_enable_frame_probe: false,
    watchdog_enable_daily_reset: false,
    watchdog_daily_reset_hour: 3
  });

  const isYoutubeForm = (editingDestination?.platform ?? newDestination.platform) === 'youtube';

  const clearOAuthPolling = () => {
    Object.values(pollingRef.current).forEach((timeoutId) => window.clearTimeout(timeoutId));
    pollingRef.current = {};
  };

  useEffect(() => {
    loadDestinations();
    loadPresets();

    return () => {
      clearOAuthPolling();
    };
  }, []);

  useEffect(() => {
    if (!showAddModal && !editingDestination) {
      setOauthEnvDraft({ clientId: '', clientSecret: '', redirectUri: '' });
    }
  }, [showAddModal, editingDestination]);

  const loadDestinations = async () => {
    try {
      const response = await api.get('/destinations/');
      setDestinations(response.data);
    } catch (error) {
      console.error('Failed to load destinations:', error);
    }
  };

  const loadPresets = async () => {
    try {
      const response = await api.get('/destinations/presets');
      setPresets(response.data);
    } catch (error) {
      console.error('Failed to load presets:', error);
    }
  };

  const handlePlatformChange = (platform: string) => {
    const preset = presets[platform];
    if (preset) {
      setNewDestination({
        ...newDestination,
        platform,
        name: preset.name,
        rtmp_url: preset.rtmp_url,
        description: preset.description,
        channel_id: platform === 'youtube' ? (newDestination.channel_id || '') : ''
      });
    }
  };

  const createDestination = async () => {
    try {
      await api.post('/destinations/', newDestination);
      setShowAddModal(false);
      setNewDestination({
        name: '',
        platform: 'youtube',
        rtmp_url: '',
        stream_key: '',
        description: '',
        channel_id: '',
        youtube_stream_id: '',
        youtube_broadcast_id: '',
        youtube_watch_url: '',
        youtube_api_key: '',
        enable_watchdog: false,
        watchdog_check_interval: 30,
        watchdog_enable_frame_probe: false,
        watchdog_enable_daily_reset: false,
        watchdog_daily_reset_hour: 3
      });
      loadDestinations();
    } catch (error) {
      console.error('Failed to create destination:', error);
      alert('Failed to create destination');
    }
  };

  const updateDestination = async () => {
    if (!editingDestination || !editingDestination.id) return;

    try {
      await api.put(`/destinations/${editingDestination.id}`, editingDestination);
      setEditingDestination(null);
      loadDestinations();
    } catch (error) {
      console.error('Failed to update destination:', error);
      alert('Failed to update destination');
    }
  };

  const deleteDestination = async (id: number) => {
    if (!window.confirm('Delete this streaming destination?')) return;

    try {
      await api.delete(`/destinations/${id}`);
      loadDestinations();
    } catch (error) {
      console.error('Failed to delete destination:', error);
      alert('Failed to delete destination');
    }
  };

  const toggleStreamKey = (id: number) => {
    setShowStreamKey(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const refreshOAuthStatus = async (id: number): Promise<boolean> => {
    try {
      const response = await api.get(`/destinations/${id}/youtube/oauth-status`);
      const { connected, expires_at, scopes } = response.data;
      setDestinations(prev => prev.map(dest => (
        dest.id === id
          ? {
              ...dest,
              youtube_oauth_connected: connected,
              youtube_token_expires_at: expires_at,
              youtube_oauth_scopes: scopes,
            }
          : dest
      )));
      return connected;
    } catch (error) {
      console.error('Failed to refresh OAuth status:', error);
      return false;
    }
  };

  const pollOAuthStatus = (id: number, attempt = 0) => {
    if (attempt > 12) {
      return;
    }

    if (pollingRef.current[id]) {
      window.clearTimeout(pollingRef.current[id]);
    }

    pollingRef.current[id] = window.setTimeout(async () => {
      const connected = await refreshOAuthStatus(id);
      if (!connected) {
        pollOAuthStatus(id, attempt + 1);
      } else {
        delete pollingRef.current[id];
      }
    }, 5000);
  };

  const startOAuthFlow = async (destination: Destination) => {
    if (!destination.id) return;

    try {
      const response = await api.post(`/destinations/${destination.id}/youtube/oauth-start`, {
        prompt_consent: !destination.youtube_oauth_connected,
      });
      const { authorization_url } = response.data;
      window.open(authorization_url, '_blank', 'width=600,height=700');
      pollOAuthStatus(destination.id);
    } catch (error) {
      console.error('Failed to start OAuth flow:', error);
      const axiosError = error as AxiosError<{ detail?: string }>;
      const detail = axiosError.response?.data?.detail;
      const message = detail
        ? `Failed to start YouTube OAuth flow: ${detail}`
        : 'Failed to start YouTube OAuth flow. Check backend logs for details.';
      alert(message);
    }
  };

  const disconnectOAuth = async (id: number) => {
    if (!window.confirm('Disconnect YouTube OAuth for this destination?')) return;

    try {
      await api.delete(`/destinations/${id}/youtube/oauth`);
      await refreshOAuthStatus(id);
      clearOAuthPolling();
    } catch (error) {
      console.error('Failed to disconnect OAuth:', error);
      alert('Failed to disconnect YouTube OAuth.');
    }
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = {
      youtube: '📺',
      facebook: '👥',
      twitch: '🎮',
      custom: '🔧'
    };
    return icons[platform] || '📡';
  };

  const getPlatformColor = (platform: string) => {
    const colors: Record<string, string> = {
      youtube: 'bg-red-600',
      facebook: 'bg-blue-600',
      twitch: 'bg-purple-600',
      custom: 'bg-gray-600'
    };
    return colors[platform] || 'bg-gray-600';
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">📡 Streaming Destinations</h1>
        <p className="text-gray-400">Configure YouTube, Facebook, Twitch, and custom RTMP destinations</p>
      </div>

      {/* Add New Button */}
      <div className="mb-6">
        <button
          onClick={() => setShowAddModal(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium"
        >
          + Add Destination
        </button>
      </div>

      {/* Destinations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {destinations.map((dest) => (
          <div key={dest.id} className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            {/* Platform Badge */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{getPlatformIcon(dest.platform)}</span>
                <span className={`${getPlatformColor(dest.platform)} px-3 py-1 rounded-full text-xs font-medium text-white capitalize`}>
                  {dest.platform}
                </span>
              </div>
              {dest.is_active && (
                <span className="bg-green-600 px-2 py-1 rounded text-xs font-medium text-white">
                  Active
                </span>
              )}
            </div>

            {/* Name & Description */}
            <h3 className="text-xl font-bold text-white mb-2">{dest.name}</h3>
            <p className="text-gray-400 text-sm mb-4">{dest.description}</p>

            {dest.platform === 'youtube' && (
              <div className="mt-4 p-4 bg-gray-900 border border-gray-700 rounded-lg">
                <div className="flex flex-col gap-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-200">YouTube OAuth</p>
                    <p className={`text-sm ${dest.youtube_oauth_connected ? 'text-green-400' : 'text-yellow-400'}`}>
                      {dest.youtube_oauth_connected ? 'Connected' : 'Not connected'}
                    </p>
                    {dest.youtube_token_expires_at && (
                      <p className="text-xs text-gray-400 mt-1">
                        Token expires {new Date(dest.youtube_token_expires_at).toLocaleString()}
                      </p>
                    )}
                    {dest.youtube_oauth_scopes && (
                      <p className="text-xs text-gray-500 mt-1 break-words">
                        Scopes: {dest.youtube_oauth_scopes}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => startOAuthFlow(dest)}
                      className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm"
                    >
                      {dest.youtube_oauth_connected ? 'Reconnect OAuth' : 'Connect OAuth'}
                    </button>
                    <button
                      onClick={() => refreshOAuthStatus(dest.id!)}
                      className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-md text-sm"
                    >
                      Refresh Status
                    </button>
                    {dest.youtube_oauth_connected && (
                      <button
                        onClick={() => disconnectOAuth(dest.id!)}
                        className="bg-gray-800 hover:bg-gray-700 text-gray-200 px-4 py-2 rounded-md text-sm"
                      >
                        Disconnect
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-gray-500">
                    Complete the Google authorization in the new window, then click "Refresh Status" if the badge does not turn
                    green automatically.
                  </p>
                </div>
              </div>
            )}

            {/* RTMP URL */}
            <div className="mb-3">
              <div className="text-gray-500 text-xs mb-1">RTMP Server</div>
              <div className="bg-gray-900 px-3 py-2 rounded text-gray-300 text-sm font-mono break-all">
                {dest.rtmp_url}
              </div>
            </div>

            {(dest.platform === 'youtube' || dest.channel_id) && (
              <div className="mb-3">
                <div className="text-gray-500 text-xs mb-1">Channel ID</div>
                <div className="bg-gray-900 px-3 py-2 rounded text-gray-300 text-sm font-mono break-all">
                  {dest.channel_id || 'Not set'}
                </div>
              </div>
            )}

            {/* Stream Key (masked) */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-1">
                <div className="text-gray-500 text-xs">Stream Key</div>
                <button
                  onClick={() => toggleStreamKey(dest.id!)}
                  className="text-blue-500 hover:text-blue-400 text-xs"
                >
                  {showStreamKey[dest.id!] ? 'Hide' : 'Show'}
                </button>
              </div>
              <div className="bg-gray-900 px-3 py-2 rounded text-gray-300 text-sm font-mono break-all">
                {showStreamKey[dest.id!] ? dest.stream_key : '••••••••••••••••'}
              </div>
            </div>

            {/* Last Used */}
            {dest.last_used && (
              <div className="text-gray-500 text-xs mb-4">
                Last used: {new Date(dest.last_used).toLocaleDateString()}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={() => setEditingDestination(dest)}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded"
              >
                Edit
              </button>
              <button
                onClick={() => deleteDestination(dest.id!)}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
              >
                Delete
              </button>
            </div>
          </div>
        ))}

        {destinations.length === 0 && (
          <div className="col-span-full bg-gray-800 rounded-lg p-12 text-center border-2 border-dashed border-gray-700">
            <div className="text-6xl mb-4">📡</div>
            <h3 className="text-xl font-bold text-white mb-2">No Streaming Destinations</h3>
            <p className="text-gray-400 mb-4">Add your first destination to get started</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded"
            >
              Add Destination
            </button>
          </div>
        )}
      </div>

      {/* Add/Edit Modal */}
      {(showAddModal || editingDestination) && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-screen overflow-y-auto">
            <h2 className="text-2xl font-bold text-white mb-6">
              {editingDestination ? 'Edit Destination' : 'Add Streaming Destination'}
            </h2>

            <div className="space-y-4">
              {/* Platform Selection */}
              <div>
                <label className="block text-gray-300 mb-2">Platform</label>
                <select
                  value={editingDestination ? editingDestination.platform : newDestination.platform}
                  onChange={(e) => {
                    if (editingDestination) {
                      setEditingDestination({
                        ...editingDestination,
                        platform: e.target.value,
                        channel_id: e.target.value === 'youtube' ? (editingDestination.channel_id || '') : ''
                      });
                    } else {
                      handlePlatformChange(e.target.value);
                    }
                  }}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded"
                >
                  <option value="youtube">YouTube Live</option>
                  <option value="facebook">Facebook Live</option>
                  <option value="twitch">Twitch</option>
                  <option value="custom">Custom RTMP</option>
                </select>
              </div>

              {/* Name */}
              <div>
                <label className="block text-gray-300 mb-2">Name</label>
                <input
                  type="text"
                  value={editingDestination ? editingDestination.name : newDestination.name}
                  onChange={(e) => {
                    if (editingDestination) {
                      setEditingDestination({ ...editingDestination, name: e.target.value });
                    } else {
                      setNewDestination({ ...newDestination, name: e.target.value });
                    }
                  }}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded"
                  placeholder="My YouTube Channel"
                />
              </div>

              {/* RTMP URL */}
              <div>
                <label className="block text-gray-300 mb-2">RTMP Server URL</label>
                <input
                  type="text"
                  value={editingDestination ? editingDestination.rtmp_url : newDestination.rtmp_url}
                  onChange={(e) => {
                    if (editingDestination) {
                      setEditingDestination({ ...editingDestination, rtmp_url: e.target.value });
                    } else {
                      setNewDestination({ ...newDestination, rtmp_url: e.target.value });
                    }
                  }}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded font-mono text-sm"
                  placeholder="rtmp://a.rtmp.youtube.com/live2"
                />
              </div>

              {/* Stream Key */}
              <div>
                <label className="block text-gray-300 mb-2">Stream Key</label>
                <input
                  type="password"
                  value={editingDestination ? editingDestination.stream_key : newDestination.stream_key}
                  onChange={(e) => {
                    if (editingDestination) {
                      setEditingDestination({ ...editingDestination, stream_key: e.target.value });
                    } else {
                      setNewDestination({ ...newDestination, stream_key: e.target.value });
                    }
                  }}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded font-mono text-sm"
                  placeholder="xxxx-xxxx-xxxx-xxxx"
                />
              </div>

              <div>
                <label className="block text-gray-300 mb-2">YouTube Channel ID</label>
                <input
                  type="text"
                  value={editingDestination ? (editingDestination.channel_id || '') : (newDestination.channel_id || '')}
                  onChange={(e) => {
                    if (editingDestination) {
                      setEditingDestination({ ...editingDestination, channel_id: e.target.value });
                    } else {
                      setNewDestination({ ...newDestination, channel_id: e.target.value });
                    }
                  }}
                  className={`w-full px-4 py-2 rounded font-mono text-sm ${isYoutubeForm ? 'bg-gray-700 text-white' : 'bg-gray-700/60 text-gray-400'}`}
                  placeholder="UCxxxxxxxxxxxxxxxx"
                  disabled={!isYoutubeForm}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Add your channel ID to enable quick links to YouTube Studio and the public channel page.
                </p>
              </div>

              {/* YouTube Stream ID */}
              <div>
                <label className="block text-gray-300 mb-2">YouTube Stream ID</label>
                <input
                  type="text"
                  value={editingDestination ? (editingDestination.youtube_stream_id || '') : (newDestination.youtube_stream_id || '')}
                  onChange={(e) => {
                    if (editingDestination) {
                      setEditingDestination({ ...editingDestination, youtube_stream_id: e.target.value });
                    } else {
                      setNewDestination({ ...newDestination, youtube_stream_id: e.target.value });
                    }
                  }}
                  className={`w-full px-4 py-2 rounded font-mono text-sm ${isYoutubeForm ? 'bg-gray-700 text-white' : 'bg-gray-700/60 text-gray-400'}`}
                  placeholder="s6qs14YByEQ (from YouTube Studio livestream URL)"
                  disabled={!isYoutubeForm}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Primary ingestion stream identifier (studio.youtube.com/video/<strong>ID</strong>/livestreaming).
                </p>
              </div>

              {/* YouTube Broadcast ID */}
              <div>
                <label className="block text-gray-300 mb-2">YouTube Broadcast ID</label>
                <input
                  type="text"
                  value={editingDestination ? (editingDestination.youtube_broadcast_id || '') : (newDestination.youtube_broadcast_id || '')}
                  onChange={(e) => {
                    if (editingDestination) {
                      setEditingDestination({ ...editingDestination, youtube_broadcast_id: e.target.value });
                    } else {
                      setNewDestination({ ...newDestination, youtube_broadcast_id: e.target.value });
                    }
                  }}
                  className={`w-full px-4 py-2 rounded font-mono text-sm ${isYoutubeForm ? 'bg-gray-700 text-white' : 'bg-gray-700/60 text-gray-400'}`}
                  placeholder="ab12cd34ef56gh78"
                  disabled={!isYoutubeForm}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Optional liveBroadcast ID for API-driven transitions. Required for automatic OAuth recovery flows.
                </p>
              </div>

              {isYoutubeForm && (
                <div className="border border-gray-700 rounded-lg p-4 bg-gray-950 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-md font-semibold text-white">YouTube OAuth Environment</h3>
                  </div>
                  <p className="text-sm text-gray-400">
                    OAuth uses server environment variables. Configure them on the backend host and redeploy.
                  </p>
                  <ul className="list-disc list-inside text-xs text-gray-400 space-y-1">
                    <li><code className="font-mono">YOUTUBE_OAUTH_CLIENT_ID</code></li>
                    <li><code className="font-mono">YOUTUBE_OAUTH_CLIENT_SECRET</code></li>
                    <li><code className="font-mono">YOUTUBE_OAUTH_REDIRECT_URI</code></li>
                  </ul>
                  <div className="space-y-2">
                    <label className="block text-gray-300 text-sm">Redirect URI (use this exact path)</label>
                    <div className="flex gap-2 items-center">
                      <input
                        type="text"
                        readOnly
                        value={`${window.location.origin}/api/destinations/youtube/oauth/callback`}
                        className="flex-1 bg-gray-800 text-gray-100 px-3 py-2 rounded font-mono text-xs"
                      />
                      <button
                        type="button"
                        onClick={() => navigator.clipboard.writeText(`${window.location.origin}/api/destinations/youtube/oauth/callback`)}
                        className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded text-xs"
                      >
                        Copy
                      </button>
                    </div>
                    <p className="text-xs text-gray-500">
                      Add this URI to your Google Cloud OAuth client and set it as <code className="font-mono">YOUTUBE_OAUTH_REDIRECT_URI</code>.
                    </p>
                  </div>
                </div>
              )}

              {/* Stream Watchdog Section */}
              {isYoutubeForm && (
                <div className="border-t border-gray-700 pt-4 mt-4">
                  <h3 className="text-lg font-semibold text-white mb-3">🐕 Stream Watchdog (Optional)</h3>
                  <p className="text-sm text-gray-400 mb-4">
                    Monitors your FFmpeg encoder and automatically restarts it if it crashes or hangs.
                    If you still rely on the legacy API-key polling, toggle the watchdog on to reveal the
                    field where you can paste your YouTube Data API key.
                  </p>

                  {/* Enable Watchdog Toggle */}
                  <div className="mb-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editingDestination ? (editingDestination.enable_watchdog || false) : (newDestination.enable_watchdog || false)}
                        onChange={(e) => {
                          if (editingDestination) {
                            setEditingDestination({ ...editingDestination, enable_watchdog: e.target.checked });
                          } else {
                            setNewDestination({ ...newDestination, enable_watchdog: e.target.checked });
                          }
                        }}
                        className="w-4 h-4"
                      />
                      <span className="text-gray-300">Enable Watchdog Monitoring</span>
                    </label>
                  </div>

                  {/* Watchdog Config Fields (show only if enabled) */}
                  {(editingDestination?.enable_watchdog || newDestination.enable_watchdog) && (
                    <div className="space-y-4 pl-6 border-l-2 border-blue-600">

                      {/* YouTube API Key */}
                      <div>
                        <label className="block text-gray-300 mb-2">YouTube API Key (Optional)</label>
                        <input
                          type="text"
                          value={editingDestination ? (editingDestination.youtube_api_key || '') : (newDestination.youtube_api_key || '')}
                          onChange={(e) => {
                            if (editingDestination) {
                              setEditingDestination({ ...editingDestination, youtube_api_key: e.target.value });
                            } else {
                              setNewDestination({ ...newDestination, youtube_api_key: e.target.value });
                            }
                          }}
                          className="w-full bg-gray-700 text-white px-4 py-2 rounded font-mono text-sm"
                          placeholder="AIza..."
                        />
                        <p className="text-xs text-gray-500 mt-1">
                        </p>
                      </div>

                      {/* Check Interval */}
                      <div>
                        <label className="block text-gray-300 mb-2">Check Interval (seconds)</label>
                        <input
                          type="number"
                          min="15"
                          max="300"
                          value={editingDestination ? (editingDestination.watchdog_check_interval || 30) : (newDestination.watchdog_check_interval || 30)}
                          onChange={(e) => {
                            const val = parseInt(e.target.value || '0', 10);
                            if (editingDestination) {
                              setEditingDestination({ ...editingDestination, watchdog_check_interval: val });
                            } else {
                              setNewDestination({ ...newDestination, watchdog_check_interval: val });
                            }
                          }}
                          className="w-full bg-gray-700 text-white px-4 py-2 rounded"
                        />
                        <p className="text-xs text-gray-500 mt-1">How often to check stream health (default: 30s)</p>
                      </div>

                      {/* Frame Probe Toggle */}
                      <div className="space-y-1">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={editingDestination ? (editingDestination.watchdog_enable_frame_probe || false) : (newDestination.watchdog_enable_frame_probe || false)}
                            onChange={(e) => {
                              if (editingDestination) {
                                setEditingDestination({ ...editingDestination, watchdog_enable_frame_probe: e.target.checked });
                              } else {
                                setNewDestination({ ...newDestination, watchdog_enable_frame_probe: e.target.checked });
                              }
                            }}
                            className="w-4 h-4"
                          />
                          <span className="text-gray-300">Enable Frame Probe</span>
                        </label>
                        <p className="text-xs text-gray-500">
                          Requires the /live URL or OAuth to verify that fresh video frames are available on YouTube.
                        </p>
                      </div>

                      {/* Daily Reset Toggle */}
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={editingDestination ? (editingDestination.watchdog_enable_daily_reset || false) : (newDestination.watchdog_enable_daily_reset || false)}
                            onChange={(e) => {
                              if (editingDestination) {
                                setEditingDestination({ ...editingDestination, watchdog_enable_daily_reset: e.target.checked });
                              } else {
                                setNewDestination({ ...newDestination, watchdog_enable_daily_reset: e.target.checked });
                              }
                            }}
                            className="w-4 h-4"
                          />
                          <span className="text-gray-300">Enable Daily Broadcast Reset</span>
                        </label>

                        {(editingDestination?.watchdog_enable_daily_reset || newDestination.watchdog_enable_daily_reset) && (
                          <div className="pl-6 space-y-1">
                            <label className="block text-gray-300 mb-1">Reset Hour (UTC)</label>
                            <input
                              type="number"
                              min="0"
                              max="23"
                              value={editingDestination ? (editingDestination.watchdog_daily_reset_hour ?? 3) : (newDestination.watchdog_daily_reset_hour ?? 3)}
                              onChange={(e) => {
                                const val = parseInt(e.target.value || '0', 10);
                                if (editingDestination) {
                                  setEditingDestination({ ...editingDestination, watchdog_daily_reset_hour: val });
                                } else {
                                  setNewDestination({ ...newDestination, watchdog_daily_reset_hour: val });
                                }
                              }}
                              className="w-full bg-gray-700 text-white px-4 py-2 rounded"
                            />
                            <p className="text-xs text-gray-500">
                              Choose a low-traffic hour (UTC) for proactive YouTube event transitions.
                            </p>
                          </div>
                        )}
                      </div>

                      {/* YouTube Channel Live URL (Optional) */}
                      <div>
                        <label className="block text-gray-300 mb-2">
                          YouTube Channel /live URL (Optional)
                        </label>
                        <input
                          type="text"
                          value={editingDestination ? (editingDestination.youtube_watch_url || '') : (newDestination.youtube_watch_url || '')}
                          onChange={(e) => {
                            if (editingDestination) {
                              setEditingDestination({ ...editingDestination, youtube_watch_url: e.target.value });
                            } else {
                              setNewDestination({ ...newDestination, youtube_watch_url: e.target.value });
                            }
                          }}
                          className="w-full bg-gray-700 text-white px-4 py-2 rounded font-mono text-sm"
                          placeholder="https://youtube.com/channel/UCxxxxx/live"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          If provided, watchdog will also check if YouTube shows your stream as live (no API key needed!).
                        </p>
                      </div>

                    </div>
                  )}
                </div>
              )}

              {/* Description */}
              <div>
                <label className="block text-gray-300 mb-2">Description (Optional)</label>
                <textarea
                  value={editingDestination ? editingDestination.description : newDestination.description}
                  onChange={(e) => {
                    if (editingDestination) {
                      setEditingDestination({ ...editingDestination, description: e.target.value });
                    } else {
                      setNewDestination({ ...newDestination, description: e.target.value });
                    }
                  }}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded h-20"
                  placeholder="Main streaming channel for events"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="mt-6 flex gap-3">
              <button
                onClick={editingDestination ? updateDestination : createDestination}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
              >
                {editingDestination ? 'Update' : 'Create'}
              </button>
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setEditingDestination(null);
                }}
                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StreamingDestinations;
