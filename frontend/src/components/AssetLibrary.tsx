import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { getAssetImageUrl } from '../utils/assetImageUrl';
import SlideOver from './shared/SlideOver';
import PositionPicker from './shared/PositionPicker';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  DocumentDuplicateIcon,
  BeakerIcon,
  MagnifyingGlassIcon,
  PaintBrushIcon,
} from '@heroicons/react/24/outline';

interface Asset {
  id: number;
  name: string;
  type: string;
  file_path: string | null;
  api_url: string | null;
  api_refresh_interval: number;
  width: number | null;
  height: number | null;
  position_x: number;
  position_y: number;
  opacity: number;
  description: string | null;
  template_instance_id: number | null;
  canvas_project_id: number | null;
  is_active: boolean;
  created_at: string;
  last_updated: string | null;
}

const TYPE_FILTERS = [
  { label: 'All', value: '' },
  { label: 'Images', value: 'static_image' },
  { label: 'API Images', value: 'api_image' },
  { label: 'Videos', value: 'video' },
  { label: 'Canvas', value: 'canvas_composite' },
  { label: 'Templates', value: 'template' },
  { label: 'Google Drawings', value: 'google_drawing' },
];

function getAssetTypeIcon(type: string): string {
  switch (type) {
    case 'api_image': return '🔄';
    case 'static_image': return '🖼️';
    case 'video': return '🎬';
    case 'graphic': return '✏️';
    case 'google_drawing': return '📐';
    case 'canvas_composite': return '🎨';
    case 'data_bound': return '📊';
    default: return '📄';
  }
}

function getPositionLabel(x: number, y: number): string {
  const col = x < 0.33 ? 'Left' : x > 0.66 ? 'Right' : 'Center';
  const row = y < 0.33 ? 'Top' : y > 0.66 ? 'Bottom' : 'Middle';
  return `${row} ${col}`;
}

const AssetLibrary: React.FC = () => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const navigate = useNavigate();
  const debounceTimer = useRef<NodeJS.Timeout>(undefined);

  // Edit state
  const [editOpen, setEditOpen] = useState(false);
  const [editAsset, setEditAsset] = useState<Asset | null>(null);
  const [editForm, setEditForm] = useState({
    name: '',
    api_url: '',
    api_refresh_interval: 30,
    width: null as number | null,
    height: null as number | null,
    position_x: 0,
    position_y: 0,
    opacity: 1,
    description: '',
  });
  const [saving, setSaving] = useState(false);
  const [replaceFile, setReplaceFile] = useState<File | null>(null);
  const [replacePreview, setReplacePreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  // Debounce search input
  useEffect(() => {
    debounceTimer.current = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(debounceTimer.current);
  }, [searchQuery]);

  const fetchAssets = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (typeFilter) params.set('type', typeFilter);
      if (debouncedSearch) params.set('search', debouncedSearch);
      const queryStr = params.toString();
      const response = await api.get(`/assets${queryStr ? `?${queryStr}` : ''}`);
      setAssets(response.data);
    } catch (err) {
      console.error('Failed to fetch assets:', err);
    } finally {
      setLoading(false);
    }
  }, [typeFilter, debouncedSearch]);

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete asset "${name}"?`)) return;
    try {
      await api.delete(`/assets/${id}`);
      setAssets(prev => prev.filter(a => a.id !== id));
    } catch (err) {
      console.error('Failed to delete asset:', err);
    }
  };

  const handleDuplicate = async (asset: Asset) => {
    try {
      const { id, is_active, created_at, last_updated, template_instance_id, canvas_project_id, ...data } = asset;
      const response = await api.post('/assets', { ...data, name: `${data.name} (Copy)` });
      setAssets(prev => [response.data, ...prev]);
    } catch (err) {
      console.error('Failed to duplicate asset:', err);
    }
  };

  const handleTest = async (id: number) => {
    try {
      const response = await api.post(`/assets/${id}/test`);
      const result = response.data;
      alert(result.success ? `Connection OK: ${result.content_type}` : `Failed: ${result.error}`);
    } catch (err) {
      alert('Test failed — could not reach the API endpoint.');
    }
  };

  const openEdit = (asset: Asset) => {
    setEditAsset(asset);
    setEditForm({
      name: asset.name,
      api_url: asset.api_url || '',
      api_refresh_interval: asset.api_refresh_interval,
      width: asset.width,
      height: asset.height,
      position_x: asset.position_x,
      position_y: asset.position_y,
      opacity: asset.opacity,
      description: asset.description || '',
    });
    setReplaceFile(null);
    setReplacePreview(null);
    setEditOpen(true);
  };

  const closeEdit = () => {
    setEditOpen(false);
    setEditAsset(null);
    setReplaceFile(null);
    setReplacePreview(null);
  };

  const handleReplaceFileSelect = (file: File) => {
    setReplaceFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setReplacePreview(e.target?.result as string);
    reader.readAsDataURL(file);
  };

  const handleSaveEdit = async () => {
    if (!editAsset) return;
    setSaving(true);
    try {
      let newFilePath: string | undefined;

      // Upload replacement file if selected
      if (replaceFile) {
        setUploading(true);
        const uploadData = new FormData();
        uploadData.append('file', replaceFile);
        uploadData.append('asset_type', editAsset.type);
        const uploadResp = await api.post('/assets/upload', uploadData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        newFilePath = uploadResp.data.file_path;
        setUploading(false);
      }

      const payload: Record<string, any> = {
        name: editForm.name,
        position_x: editForm.position_x,
        position_y: editForm.position_y,
        opacity: editForm.opacity,
        description: editForm.description || null,
        width: editForm.width,
        height: editForm.height,
      };
      if (newFilePath) {
        payload.file_path = newFilePath;
      }
      if (editAsset.type === 'api_image') {
        payload.api_url = editForm.api_url || null;
        payload.api_refresh_interval = editForm.api_refresh_interval;
      }
      const response = await api.put(`/assets/${editAsset.id}`, payload);
      setAssets(prev => prev.map(a => a.id === editAsset.id ? response.data : a));
      closeEdit();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update asset');
    } finally {
      setSaving(false);
      setUploading(false);
    }
  };

  // Skeleton cards for loading state
  const SkeletonCard = () => (
    <div className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden animate-pulse">
      <div className="aspect-video bg-dark-700" />
      <div className="p-4 space-y-3">
        <div className="h-4 bg-dark-700 rounded w-2/3" />
        <div className="h-3 bg-dark-700 rounded w-1/2" />
      </div>
    </div>
  );

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
        <div className="flex flex-wrap gap-2">
          {TYPE_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setTypeFilter(f.value)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                typeFilter === f.value
                  ? 'bg-primary-600 text-white'
                  : 'bg-dark-700 text-gray-400 hover:bg-dark-600 hover:text-gray-300'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex gap-2 items-center">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search assets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 w-48"
            />
          </div>
          <button
            onClick={() => navigate('/assets/editor/new')}
            className="flex items-center px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <PaintBrushIcon className="h-4 w-4 mr-1.5" />
            New Canvas
          </button>
        </div>
      </div>

      {/* Asset Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : assets.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-gray-500 text-lg mb-4">No assets found</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => navigate('/assets/templates')}
              className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg text-sm transition-colors"
            >
              Browse Templates
            </button>
            <button
              onClick={() => navigate('/assets/editor/new')}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm transition-colors"
            >
              Create in Editor
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {assets.map((asset) => {
            const imageUrl = getAssetImageUrl(asset);
            return (
              <div
                key={asset.id}
                className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden hover:border-dark-600 transition-colors group"
              >
                {/* Preview */}
                <div className="aspect-video bg-dark-900 flex items-center justify-center relative overflow-hidden">
                  {imageUrl ? (
                    <img
                      src={imageUrl}
                      alt={asset.name}
                      className="w-full h-full object-contain"
                      loading="lazy"
                    />
                  ) : (
                    <span className="text-4xl">{getAssetTypeIcon(asset.type)}</span>
                  )}
                  {/* Type badge */}
                  <span className="absolute top-2 left-2 text-xs bg-dark-800/80 text-gray-300 px-2 py-0.5 rounded-full">
                    {getAssetTypeIcon(asset.type)} {asset.type.replace('_', ' ')}
                  </span>
                  {/* Template badge */}
                  {asset.template_instance_id && (
                    <span className="absolute top-2 right-2 text-xs bg-primary-600/80 text-white px-2 py-0.5 rounded-full">
                      Template
                    </span>
                  )}
                </div>

                {/* Info */}
                <div className="p-4">
                  <h3 className="text-sm font-medium text-white truncate mb-2">{asset.name}</h3>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500 mb-3">
                    <span>Position: {getPositionLabel(asset.position_x, asset.position_y)}</span>
                    <span>Opacity: {Math.round(asset.opacity * 100)}%</span>
                    {asset.width && asset.height && (
                      <span>Size: {asset.width}x{asset.height}</span>
                    )}
                    {asset.type === 'api_image' && (
                      <span>Refresh: {asset.api_refresh_interval}s</span>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => openEdit(asset)}
                      title="Edit"
                      className="p-1.5 bg-dark-700 hover:bg-dark-600 text-gray-400 hover:text-white rounded transition-colors"
                    >
                      <PencilIcon className="h-4 w-4" />
                    </button>
                    {asset.canvas_project_id && (
                      <button
                        onClick={() => navigate(`/assets/editor/${asset.canvas_project_id}`)}
                        title="Edit in Canvas"
                        className="p-1.5 bg-dark-700 hover:bg-dark-600 text-gray-400 hover:text-white rounded transition-colors"
                      >
                        <PaintBrushIcon className="h-4 w-4" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDuplicate(asset)}
                      title="Duplicate"
                      className="p-1.5 bg-dark-700 hover:bg-dark-600 text-gray-400 hover:text-white rounded transition-colors"
                    >
                      <DocumentDuplicateIcon className="h-4 w-4" />
                    </button>
                    {asset.type === 'api_image' && (
                      <button
                        onClick={() => handleTest(asset.id)}
                        title="Test Connection"
                        className="p-1.5 bg-dark-700 hover:bg-dark-600 text-gray-400 hover:text-white rounded transition-colors"
                      >
                        <BeakerIcon className="h-4 w-4" />
                      </button>
                    )}
                    <div className="flex-1" />
                    <button
                      onClick={() => handleDelete(asset.id, asset.name)}
                      title="Delete"
                      className="p-1.5 bg-dark-700 hover:bg-red-900/50 text-gray-400 hover:text-red-400 rounded transition-colors"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Edit Asset SlideOver */}
      <SlideOver
        isOpen={editOpen}
        onClose={closeEdit}
        title={editAsset?.name || 'Edit Asset'}
        subtitle={editAsset ? `${getAssetTypeIcon(editAsset.type)} ${editAsset.type.replace('_', ' ')}` : ''}
        footer={
          <div className="flex gap-3">
            <button
              onClick={closeEdit}
              className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg text-sm transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSaveEdit}
              disabled={saving || !editForm.name.trim()}
              className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              {uploading ? 'Uploading...' : saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        }
      >
        {editAsset && (
          <div className="space-y-5">
            {/* Preview + Replace Image */}
            {(editAsset.type === 'static_image' || editAsset.type === 'video' || editAsset.type === 'canvas_composite') && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  {editAsset.type === 'video' ? 'Video File' : 'Image'}
                </label>
                {/* Show current or replacement preview */}
                <div className="bg-dark-900 border border-dark-700 rounded-lg overflow-hidden mb-2">
                  {replacePreview ? (
                    <img src={replacePreview} alt="New upload preview" className="w-full object-contain max-h-40" />
                  ) : (() => {
                    const url = getAssetImageUrl(editAsset);
                    return url ? (
                      <img src={url} alt={editAsset.name} className="w-full object-contain max-h-40" />
                    ) : (
                      <div className="flex items-center justify-center h-24 text-gray-600 text-sm">No preview</div>
                    );
                  })()}
                </div>
                {/* Replace button */}
                <label className="flex items-center justify-center gap-2 px-3 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg text-sm cursor-pointer transition-colors border border-dark-600 border-dashed">
                  <PlusIcon className="h-4 w-4" />
                  {replaceFile ? replaceFile.name : 'Replace Image...'}
                  <input
                    type="file"
                    accept={editAsset.type === 'video' ? 'video/*' : 'image/*'}
                    onChange={(e) => { if (e.target.files?.[0]) handleReplaceFileSelect(e.target.files[0]); }}
                    className="hidden"
                  />
                </label>
                {replaceFile && (
                  <button
                    onClick={() => { setReplaceFile(null); setReplacePreview(null); }}
                    className="mt-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    Cancel replacement
                  </button>
                )}
              </div>
            )}

            {/* Preview for non-replaceable types (api_image, google_drawing) */}
            {editAsset.type !== 'static_image' && editAsset.type !== 'video' && editAsset.type !== 'canvas_composite' && (() => {
              const url = getAssetImageUrl(editAsset);
              return url ? (
                <div className="bg-dark-900 border border-dark-700 rounded-lg overflow-hidden">
                  <img src={url} alt={editAsset.name} className="w-full object-contain max-h-40" />
                </div>
              ) : null;
            })()}

            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Name</label>
              <input
                type="text"
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            {/* API URL (only for api_image) */}
            {editAsset.type === 'api_image' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">API URL</label>
                  <input
                    type="text"
                    value={editForm.api_url}
                    onChange={(e) => setEditForm({ ...editForm, api_url: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Refresh Interval: {editForm.api_refresh_interval}s
                  </label>
                  <input
                    type="number"
                    value={editForm.api_refresh_interval}
                    min={1}
                    max={3600}
                    onChange={(e) => setEditForm({ ...editForm, api_refresh_interval: parseInt(e.target.value) || 30 })}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </>
            )}

            {/* Google Drawing URL */}
            {editAsset.type === 'google_drawing' && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Google Drawing URL</label>
                <p className="text-xs text-gray-500 mb-1">
                  The file_path for Google Drawings is set at creation and cannot be changed here.
                </p>
                <div className="px-3 py-2 bg-dark-900 border border-dark-700 rounded-md text-gray-400 text-sm font-mono truncate">
                  {editAsset.file_path || 'Not set'}
                </div>
              </div>
            )}

            {/* Dimensions */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Dimensions (px)</label>
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-xs text-gray-500 mb-0.5">Width</label>
                  <input
                    type="number"
                    value={editForm.width ?? ''}
                    min={1}
                    max={3840}
                    placeholder="Auto"
                    onChange={(e) => setEditForm({ ...editForm, width: e.target.value ? parseInt(e.target.value) : null })}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-xs text-gray-500 mb-0.5">Height</label>
                  <input
                    type="number"
                    value={editForm.height ?? ''}
                    min={1}
                    max={2160}
                    placeholder="Auto"
                    onChange={(e) => setEditForm({ ...editForm, height: e.target.value ? parseInt(e.target.value) : null })}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
            </div>

            {/* Position */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Position</label>
              <PositionPicker
                positionX={editForm.position_x}
                positionY={editForm.position_y}
                onChange={(x, y) => setEditForm({ ...editForm, position_x: x, position_y: y })}
                showRawInputs
              />
            </div>

            {/* Opacity */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Opacity: {Math.round(editForm.opacity * 100)}%
              </label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={editForm.opacity}
                onChange={(e) => setEditForm({ ...editForm, opacity: parseFloat(e.target.value) })}
                className="w-full accent-primary-500"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
              <textarea
                value={editForm.description}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                rows={2}
                className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                placeholder="Optional description..."
              />
            </div>
          </div>
        )}
      </SlideOver>
    </div>
  );
};

export default AssetLibrary;
