import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

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
}

interface PlatformPreset {
  name: string;
  rtmp_url: string;
  description: string;
}

const StreamingDestinations: React.FC = () => {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [presets, setPresets] = useState<Record<string, PlatformPreset>>({});
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingDestination, setEditingDestination] = useState<Destination | null>(null);
  const [showStreamKey, setShowStreamKey] = useState<Record<number, boolean>>({});

  const [newDestination, setNewDestination] = useState<Destination>({
    name: '',
    platform: 'youtube',
    rtmp_url: '',
    stream_key: '',
    description: '',
    channel_id: ''
  });

  const isYoutubeForm = (editingDestination?.platform ?? newDestination.platform) === 'youtube';

  useEffect(() => {
    loadDestinations();
    loadPresets();
  }, []);

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
        channel_id: ''
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
