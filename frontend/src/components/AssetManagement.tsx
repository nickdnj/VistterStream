import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { CloudArrowUpIcon, XMarkIcon } from '@heroicons/react/24/outline';

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
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    setSelectedFile(null);
    setPreviewUrl(null);
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
    setSelectedFile(null);
    setPreviewUrl(null);
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

  const handleFileSelect = (file: File) => {
    // Validate file type
    const validImageTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
    const validVideoTypes = ['video/mp4', 'video/mpeg', 'video/quicktime', 'video/webm'];
    
    if (formData.type === 'static_image' && !validImageTypes.includes(file.type)) {
      alert('❌ Invalid file type! Please select an image file (PNG, JPEG, GIF, WebP)');
      return;
    }
    
    if (formData.type === 'video' && !validVideoTypes.includes(file.type)) {
      alert('❌ Invalid file type! Please select a video file (MP4, MOV, WebM)');
      return;
    }

    // Validate file size (50MB max)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      alert('❌ File too large! Maximum size is 50MB');
      return;
    }

    setSelectedFile(file);

    // Generate preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreviewUrl(e.target?.result as string);
    };
    reader.readAsDataURL(file);

    // Auto-fill name if empty
    if (!formData.name) {
      const nameWithoutExt = file.name.replace(/\.[^/.]+$/, "");
      setFormData({ ...formData, name: nameWithoutExt });
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // For file-based assets, upload file first
    if ((formData.type === 'static_image' || formData.type === 'video') && selectedFile) {
      setUploading(true);
      try {
        const uploadFormData = new FormData();
        uploadFormData.append('file', selectedFile);
        uploadFormData.append('asset_type', formData.type);

        const uploadResponse = await axios.post('/api/assets/upload', uploadFormData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            const progress = progressEvent.total 
              ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
              : 0;
            setUploadProgress(progress);
          },
        });

        // Use uploaded file path
        formData.file_path = uploadResponse.data.file_path;
      } catch (error: any) {
        console.error('Upload failed:', error);
        alert(`❌ Upload failed:\n${error.response?.data?.detail || error.message}`);
        setUploading(false);
        return;
      } finally {
        setUploading(false);
        setUploadProgress(0);
      }
    }

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
      setSelectedFile(null);
      setPreviewUrl(null);
      loadAssets();
    } catch (error: any) {
      console.error('Failed to save asset:', error);
      alert(`❌ Failed to save asset:\n${error.response?.data?.detail || error.message}`);
    }
  };

  const handleDeleteAsset = async (assetId: number) => {
    if (!window.confirm('⚠️  Are you sure you want to delete this asset?')) {
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
          <p className="text-gray-400 mt-1">Manage overlay graphics, images, videos, and dynamic content</p>
        </div>
        <button
          onClick={handleAddAsset}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-md transition-colors font-medium flex items-center gap-2"
        >
          <span className="text-xl">+</span>
          Add Asset
        </button>
      </div>

      {assets.length === 0 ? (
        <div className="bg-dark-800 rounded-lg p-12 border border-dark-700 text-center">
          <div className="text-6xl mb-4">🎨</div>
          <h3 className="text-xl font-semibold text-white mb-2">No Assets Yet</h3>
          <p className="text-gray-400 mb-6">
            Create assets to overlay on your streams - images, videos, graphics, weather data, and more!
          </p>
          <button
            onClick={handleAddAsset}
            className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-md transition-colors font-medium"
          >
            Create First Asset
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {assets.map((asset) => (
            <div key={asset.id} className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden hover:border-dark-600 transition-colors">
              {/* Preview/Icon */}
              <div className="aspect-video bg-dark-700 flex items-center justify-center relative">
                {asset.type === 'api_image' && asset.api_url ? (
                  <img 
                    src={asset.api_url} 
                    alt={asset.name}
                    className="w-full h-full object-contain"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                      (e.target as HTMLImageElement).parentElement!.innerHTML = `<div class="text-6xl">${getAssetTypeIcon(asset.type)}</div>`;
                    }}
                  />
                ) : asset.type === 'static_image' && asset.file_path ? (
                  <img 
                    src={asset.file_path} 
                    alt={asset.name}
                    className="w-full h-full object-contain"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                      (e.target as HTMLImageElement).parentElement!.innerHTML = `<div class="text-6xl">${getAssetTypeIcon(asset.type)}</div>`;
                    }}
                  />
                ) : asset.type === 'video' && asset.file_path ? (
                  <video 
                    src={asset.file_path} 
                    className="w-full h-full object-contain"
                    muted
                    preload="metadata"
                    onError={(e) => {
                      (e.target as HTMLVideoElement).style.display = 'none';
                      (e.target as HTMLVideoElement).parentElement!.innerHTML = `<div class="text-6xl">${getAssetTypeIcon(asset.type)}</div>`;
                    }}
                  />
                ) : (
                  <div className="text-6xl">{getAssetTypeIcon(asset.type)}</div>
                )}
                <div className="absolute top-2 right-2 px-2 py-1 bg-black/70 rounded text-xs text-white font-semibold">
                  {asset.type.replace('_', ' ').toUpperCase()}
                </div>
              </div>

              {/* Details */}
              <div className="p-4">
                <h3 className="text-lg font-semibold text-white mb-2 truncate">{asset.name}</h3>
                {asset.description && (
                  <p className="text-sm text-gray-400 mb-3 line-clamp-2">{asset.description}</p>
                )}

                <div className="space-y-2 text-sm text-gray-400 mb-4">
                  <div className="flex justify-between">
                    <span>Position:</span>
                    <span className="text-white">{getPositionLabel(asset.position_x, asset.position_y)}</span>
                  </div>
                  {(asset.width || asset.height) && (
                    <div className="flex justify-between">
                      <span>Size:</span>
                      <span className="text-white">
                        {asset.width || 'Auto'} × {asset.height || 'Auto'}px
                      </span>
                    </div>
                  )}
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
                    className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors font-medium"
                  >
                    ✏️ Edit
                  </button>
                  {asset.type === 'api_image' && (
                    <button
                      onClick={() => handleTestAsset(asset.id)}
                      disabled={testing}
                      className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition-colors disabled:opacity-50 font-medium"
                      title="Test API connection"
                    >
                      🔍
                    </button>
                  )}
                  <button
                    onClick={() => handleDeleteAsset(asset.id)}
                    className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors font-medium"
                    title="Delete asset"
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
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-800 rounded-lg border border-dark-700 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-dark-800 px-6 py-4 border-b border-dark-700 flex items-center justify-between z-10">
              <h3 className="text-xl font-bold text-white">
                {selectedAsset ? 'Edit Asset' : 'Add New Asset'}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Asset Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                  placeholder="e.g., Weather & Tides"
                />
              </div>

              {/* Type */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Asset Type *
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { value: 'api_image', label: 'API Image', icon: '🌐', desc: 'Dynamic content from API' },
                    { value: 'static_image', label: 'Static Image', icon: '🖼️', desc: 'Upload PNG, JPEG, etc.' },
                    { value: 'video', label: 'Video', icon: '🎥', desc: 'Upload MP4, MOV, etc.' },
                    { value: 'graphic', label: 'Graphic', icon: '🎨', desc: 'Custom graphic overlay' },
                  ].map((type) => (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => {
                        setFormData({ ...formData, type: type.value as any });
                        setSelectedFile(null);
                        setPreviewUrl(null);
                      }}
                      className={`p-4 rounded-lg border-2 transition-all text-left ${
                        formData.type === type.value
                          ? 'border-primary-500 bg-primary-500/10'
                          : 'border-dark-600 bg-dark-700 hover:border-dark-500'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-2xl">{type.icon}</span>
                        <span className="font-semibold text-white">{type.label}</span>
                      </div>
                      <p className="text-xs text-gray-400">{type.desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* API Configuration */}
              {formData.type === 'api_image' && (
                <div className="space-y-4 p-4 bg-dark-700/50 rounded-lg border border-dark-600">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      API URL *
                    </label>
                    <input
                      type="url"
                      value={formData.api_url}
                      onChange={(e) => setFormData({ ...formData, api_url: e.target.value })}
                      className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
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
                      className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      min="1"
                      max="3600"
                    />
                    <p className="mt-1 text-xs text-gray-400">How often to fetch updated content (1-3600 seconds)</p>
                  </div>
                </div>
              )}

              {/* File Upload */}
              {(formData.type === 'static_image' || formData.type === 'video' || formData.type === 'graphic') && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Upload File *
                    </label>
                    <div
                      className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                        dragActive
                          ? 'border-primary-500 bg-primary-500/10'
                          : 'border-dark-600 bg-dark-700 hover:border-dark-500'
                      }`}
                      onDragEnter={handleDrag}
                      onDragLeave={handleDrag}
                      onDragOver={handleDrag}
                      onDrop={handleDrop}
                    >
                      <input
                        ref={fileInputRef}
                        type="file"
                        onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                        accept={formData.type === 'static_image' ? 'image/*' : 'video/*'}
                        className="hidden"
                      />
                      
                      {previewUrl ? (
                        <div className="space-y-3">
                          {formData.type === 'static_image' ? (
                            <img src={previewUrl} alt="Preview" className="max-h-48 mx-auto rounded" />
                          ) : (
                            <video src={previewUrl} controls className="max-h-48 mx-auto rounded" />
                          )}
                          <p className="text-sm text-green-400 font-medium">✓ {selectedFile?.name}</p>
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedFile(null);
                              setPreviewUrl(null);
                            }}
                            className="text-sm text-red-400 hover:text-red-300"
                          >
                            Remove
                          </button>
                        </div>
                      ) : (
                        <>
                          <CloudArrowUpIcon className="h-12 w-12 mx-auto text-gray-400 mb-3" />
                          <p className="text-gray-300 mb-2">
                            Drop your {formData.type === 'static_image' ? 'image' : 'video'} here or{' '}
                            <button
                              type="button"
                              onClick={() => fileInputRef.current?.click()}
                              className="text-primary-500 hover:text-primary-400 font-medium"
                            >
                              browse
                            </button>
                          </p>
                          <p className="text-xs text-gray-400">
                            {formData.type === 'static_image'
                              ? 'PNG, JPEG, GIF, WebP (max 50MB)'
                              : 'MP4, MOV, WebM (max 50MB)'}
                          </p>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Optional: Manual URL input as fallback */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Or enter URL
                    </label>
                    <input
                      type="text"
                      value={formData.file_path}
                      onChange={(e) => setFormData({ ...formData, file_path: e.target.value })}
                      className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder="https://example.com/image.png (optional if uploading)"
                      disabled={!!selectedFile}
                    />
                  </div>
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
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  rows={2}
                  placeholder="Optional description..."
                />
              </div>

              {/* Dimensions (Scale) */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Overlay Size (Optional)
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Width (pixels)
                    </label>
                    <input
                      type="number"
                      value={formData.width || ''}
                      onChange={(e) => setFormData({ ...formData, width: e.target.value ? Number(e.target.value) : null })}
                      className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      min="1"
                      max="3840"
                      placeholder="Auto"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Height (pixels)
                    </label>
                    <input
                      type="number"
                      value={formData.height || ''}
                      onChange={(e) => setFormData({ ...formData, height: e.target.value ? Number(e.target.value) : null })}
                      className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      min="1"
                      max="2160"
                      placeholder="Auto"
                    />
                  </div>
                </div>
                <p className="mt-2 text-xs text-gray-400">
                  💡 Leave blank for original size, or set one dimension to scale proportionally
                </p>
              </div>

              {/* Position */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Overlay Position
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Horizontal (0=Left, 1=Right)
                    </label>
                    <input
                      type="number"
                      value={formData.position_x}
                      onChange={(e) => setFormData({ ...formData, position_x: Number(e.target.value) })}
                      className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      min="0"
                      max="1"
                      step="0.01"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Vertical (0=Top, 1=Bottom)
                    </label>
                    <input
                      type="number"
                      value={formData.position_y}
                      onChange={(e) => setFormData({ ...formData, position_y: Number(e.target.value) })}
                      className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      min="0"
                      max="1"
                      step="0.01"
                    />
                  </div>
                </div>
                <p className="mt-2 text-xs text-gray-400">
                  Current: {getPositionLabel(formData.position_x, formData.position_y)}
                </p>
              </div>

              {/* Opacity */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Opacity: {Math.round(formData.opacity * 100)}%
                </label>
                <input
                  type="range"
                  value={formData.opacity}
                  onChange={(e) => setFormData({ ...formData, opacity: Number(e.target.value) })}
                  className="w-full h-2 bg-dark-700 rounded-lg appearance-none cursor-pointer"
                  min="0"
                  max="1"
                  step="0.05"
                  style={{
                    background: `linear-gradient(to right, #3B82F6 0%, #3B82F6 ${formData.opacity * 100}%, #374151 ${formData.opacity * 100}%, #374151 100%)`
                  }}
                />
              </div>

              {/* Upload Progress */}
              {uploading && (
                <div className="bg-dark-700 p-4 rounded-lg border border-dark-600">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white font-medium">Uploading...</span>
                    <span className="text-sm text-white font-medium">{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-dark-600 rounded-full h-2">
                    <div
                      className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                </div>
              )}

              {/* Buttons */}
              <div className="flex gap-3 pt-4 border-t border-dark-700">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-md transition-colors font-medium"
                  disabled={uploading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-md transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={uploading || (formData.type === 'api_image' && !formData.api_url) || ((formData.type === 'static_image' || formData.type === 'video') && !selectedFile && !formData.file_path)}
                >
                  {uploading ? 'Uploading...' : selectedAsset ? 'Update Asset' : 'Create Asset'}
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
