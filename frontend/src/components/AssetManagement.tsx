import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Asset {
  id: number;
  name: string;
  type: 'static_image' | 'api_image' | 'video' | 'graphic';
  file_path: string | null;
  api_url: string | null;
  api_refresh_interval: number;
  width: number | null;
  height: number | null;
  position_x: number;
  position_y: number;
  opacity: number;
  description: string | null;
  is_active: boolean;
  created_at: string;
  last_updated: string | null;
}

const AssetManagement: React.FC = () => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [testing, setTesting] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    type: 'api_image' as 'static_image' | 'api_image' | 'video' | 'graphic',
    file_path: '',
    api_url: '',
    api_refresh_interval: 30,
    width: null as number | null,
    height: null as number | null,
    position_x: 0.8,
    position_y: 0.05,
    opacity: 1.0,
    description: '',
  });

  useEffect(() => {
    loadAssets();
  }, []);

  const loadAssets = async () => {
    try {
      const response = await axios.get('/api/assets/');
      setAssets(response.data);
    } catch (error) {
      console.error('Failed to load assets:', error);
      alert('Failed to load assets');
    }
  };

  const handleAddAsset = () => {
    setSelectedAsset(null);
    setFormData({
      name: '',
      type: 'api_image',
      file_path: '',
      api_url: '',
      api_refresh_interval: 30,
      width: null,
      height: null,
      position_x: 0.8,
      position_y: 0.05,
      opacity: 1.0,
      description: '',
    });
    setShowModal(true);
  };

  const handleEditAsset = (asset: Asset) => {
    setSelectedAsset(asset);
    setFormData({
      name: asset.name,
      type: asset.type,
      file_path: asset.file_path || '',
      api_url: asset.api_url || '',
      api_refresh_interval: asset.api_refresh_interval,
      width: asset.width,
      height: asset.height,
      position_x: asset.position_x,
      position_y: asset.position_y,
      opacity: asset.opacity,
      description: asset.description || '',
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const payload = {
      ...formData,
      file_path: formData.file_path || null,
      api_url: formData.api_url || null,
      description: formData.description || null,
    };

    try {
      if (selectedAsset) {
        await axios.put(`/api/assets/${selectedAsset.id}`, payload);
        alert('✅ Asset updated successfully!');
      } else {
        await axios.post('/api/assets/', payload);
        alert('✅ Asset created successfully!');
      }
      setShowModal(false);
      loadAssets();
    } catch (error: any) {
      console.error('Failed to save asset:', error);
      alert(`❌ Failed to save asset:\n${error.response?.data?.detail || error.message}`);
    }
  };

  const handleDeleteAsset = async (assetId: number) => {
    if (!window.confirm('Are you sure you want to delete this asset?')) {
      return;
    }

    try {
      await axios.delete(`/api/assets/${assetId}`);
      alert('✅ Asset deleted successfully!');
      loadAssets();
    } catch (error) {
      console.error('Failed to delete asset:', error);
      alert('❌ Failed to delete asset');
    }
  };

  const handleTestAsset = async (assetId: number) => {
    setTesting(true);
    try {
      const response = await axios.post(`/api/assets/${assetId}/test`);
      if (response.data.success) {
        alert(`✅ Asset test successful!\n\nStatus: ${response.data.status_code}\nContent-Type: ${response.data.content_type}\nSize: ${response.data.content_length} bytes`);
      } else {
        alert(`❌ Asset test failed:\n${response.data.error}`);
      }
    } catch (error: any) {
      console.error('Failed to test asset:', error);
      alert(`❌ Test failed:\n${error.response?.data?.detail || error.message}`);
    } finally {
      setTesting(false);
    }
  };

  const getAssetTypeIcon = (type: string) => {
    switch (type) {
      case 'static_image': return '🖼️';
      case 'api_image': return '🌐';
      case 'video': return '🎥';
      case 'graphic': return '🎨';
      default: return '📄';
    }
  };

  const getPositionLabel = (x: number, y: number) => {
    if (x < 0.33 && y < 0.33) return 'Top Left';
    if (x > 0.66 && y < 0.33) return 'Top Right';
    if (x < 0.33 && y > 0.66) return 'Bottom Left';
    if (x > 0.66 && y > 0.66) return 'Bottom Right';
    if (y < 0.33) return 'Top Center';
    if (y > 0.66) return 'Bottom Center';
    if (x < 0.33) return 'Middle Left';
    if (x > 0.66) return 'Middle Right';
    return 'Center';
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">Assets</h2>
          <p className="text-gray-400 mt-1">Manage overlay graphics, images, and dynamic content</p>
        </div>
        <button
          onClick={handleAddAsset}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-md transition-colors"
        >
          + Add Asset
        </button>
      </div>

      {assets.length === 0 ? (
        <div className="bg-dark-800 rounded-lg p-12 border border-dark-700 text-center">
          <div className="text-6xl mb-4">🎨</div>
          <h3 className="text-xl font-semibold text-white mb-2">No Assets Yet</h3>
          <p className="text-gray-400 mb-6">
            Create assets to overlay on your streams - images, graphics, weather data, and more!
          </p>
          <button
            onClick={handleAddAsset}
            className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-md transition-colors"
          >
            Create First Asset
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {assets.map((asset) => (
            <div key={asset.id} className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden">
              {/* Preview/Icon */}
              <div className="aspect-video bg-dark-700 flex items-center justify-center relative">
                {asset.type === 'api_image' && asset.api_url ? (
                  <img 
                    src={asset.api_url} 
                    alt={asset.name}
                    className="w-full h-full object-contain"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                ) : (
                  <div className="text-6xl">{getAssetTypeIcon(asset.type)}</div>
                )}
                <div className="absolute top-2 right-2 px-2 py-1 bg-black/70 rounded text-xs text-white">
                  {asset.type.replace('_', ' ').toUpperCase()}
                </div>
              </div>

              {/* Details */}
              <div className="p-4">
                <h3 className="text-lg font-semibold text-white mb-2">{asset.name}</h3>
                {asset.description && (
                  <p className="text-sm text-gray-400 mb-3">{asset.description}</p>
                )}

                <div className="space-y-2 text-sm text-gray-400 mb-4">
                  <div className="flex justify-between">
                    <span>Position:</span>
                    <span className="text-white">{getPositionLabel(asset.position_x, asset.position_y)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Opacity:</span>
                    <span className="text-white">{Math.round(asset.opacity * 100)}%</span>
                  </div>
                  {asset.type === 'api_image' && (
                    <div className="flex justify-between">
                      <span>Refresh:</span>
                      <span className="text-white">{asset.api_refresh_interval}s</span>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={() => handleEditAsset(asset)}
                    className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
                  >
                    ✏️ Edit
                  </button>
                  {asset.type === 'api_image' && (
                    <button
                      onClick={() => handleTestAsset(asset.id)}
                      disabled={testing}
                      className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition-colors disabled:opacity-50"
                      title="Test API connection"
                    >
                      🔍
                    </button>
                  )}
                  <button
                    onClick={() => handleDeleteAsset(asset.id)}
                    className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-800 rounded-lg border border-dark-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-dark-700">
              <h3 className="text-xl font-bold text-white">
                {selectedAsset ? 'Edit Asset' : 'Add New Asset'}
              </h3>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Asset Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white"
                  required
                  placeholder="e.g., Weather & Tides"
                />
              </div>

              {/* Type */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Asset Type *
                </label>
                <select
                  value={formData.type}
                  onChange={(e) => setFormData({ ...formData, type: e.target.value as any })}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white"
                  required
                >
                  <option value="api_image">API Image (Dynamic)</option>
                  <option value="static_image">Static Image</option>
                  <option value="video">Video</option>
                  <option value="graphic">Graphic</option>
                </select>
              </div>

              {/* API URL (for api_image) */}
              {formData.type === 'api_image' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      API URL *
                    </label>
                    <input
                      type="url"
                      value={formData.api_url}
                      onChange={(e) => setFormData({ ...formData, api_url: e.target.value })}
                      className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white font-mono text-sm"
                      required
                      placeholder="https://api.example.com/weather.png"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Refresh Interval (seconds)
                    </label>
                    <input
                      type="number"
                      value={formData.api_refresh_interval}
                      onChange={(e) => setFormData({ ...formData, api_refresh_interval: Number(e.target.value) })}
                      className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white"
                      min="1"
                      max="3600"
                    />
                  </div>
                </>
              )}

              {/* File Path (for static_image/video) */}
              {(formData.type === 'static_image' || formData.type === 'video' || formData.type === 'graphic') && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    File Path or URL *
                  </label>
                  <input
                    type="text"
                    value={formData.file_path}
                    onChange={(e) => setFormData({ ...formData, file_path: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white font-mono text-sm"
                    required
                    placeholder="/path/to/file.png or https://example.com/image.png"
                  />
                </div>
              )}

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white"
                  rows={2}
                  placeholder="Optional description..."
                />
              </div>

              {/* Position */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Position X (0=Left, 1=Right)
                  </label>
                  <input
                    type="number"
                    value={formData.position_x}
                    onChange={(e) => setFormData({ ...formData, position_x: Number(e.target.value) })}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white"
                    min="0"
                    max="1"
                    step="0.01"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Position Y (0=Top, 1=Bottom)
                  </label>
                  <input
                    type="number"
                    value={formData.position_y}
                    onChange={(e) => setFormData({ ...formData, position_y: Number(e.target.value) })}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white"
                    min="0"
                    max="1"
                    step="0.01"
                  />
                </div>
              </div>

              {/* Opacity */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Opacity ({Math.round(formData.opacity * 100)}%)
                </label>
                <input
                  type="range"
                  value={formData.opacity}
                  onChange={(e) => setFormData({ ...formData, opacity: Number(e.target.value) })}
                  className="w-full"
                  min="0"
                  max="1"
                  step="0.05"
                />
              </div>

              {/* Buttons */}
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-md transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-md transition-colors"
                >
                  {selectedAsset ? 'Update Asset' : 'Create Asset'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AssetManagement;

