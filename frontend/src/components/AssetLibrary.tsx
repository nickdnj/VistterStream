import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { getAssetImageUrl } from '../utils/assetImageUrl';
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
    </div>
  );
};

export default AssetLibrary;
