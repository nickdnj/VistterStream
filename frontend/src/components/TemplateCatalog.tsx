import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import SlideOver from './shared/SlideOver';
import PositionPicker from './shared/PositionPicker';
import {
  CloudIcon,
  ClockIcon,
  MegaphoneIcon,
  ChatBubbleLeftRightIcon,
  Bars3BottomLeftIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  LockClosedIcon,
} from '@heroicons/react/24/outline';

interface OverlayTemplate {
  id: number;
  name: string;
  category: string;
  description: string | null;
  config_schema: string;
  default_config: string;
  preview_path: string | null;
  version: number;
  is_bundled: boolean;
  is_active: boolean;
}

interface ConfigField {
  key: string;
  label: string;
  type: string;
  required?: boolean;
  default?: any;
  placeholder?: string;
  help?: string;
  options?: { value: string; label: string }[];
  min?: number;
  max?: number;
}

const CATEGORY_ICONS: Record<string, React.FC<{ className?: string }>> = {
  weather: CloudIcon,
  marine: CloudIcon,
  time_date: ClockIcon,
  sponsor_ad: MegaphoneIcon,
  lower_third: Bars3BottomLeftIcon,
  social_media: ChatBubbleLeftRightIcon,
};

const CATEGORY_LABELS: Record<string, string> = {
  weather: 'Weather',
  marine: 'Marine',
  time_date: 'Time & Date',
  sponsor_ad: 'Sponsor / Ad',
  lower_third: 'Lower Third',
  social_media: 'Social Media',
};

const CATEGORIES = ['', 'weather', 'marine', 'time_date', 'sponsor_ad', 'lower_third', 'social_media'];
const COMING_SOON_CATEGORIES = ['social_media'];

const TemplateCatalog: React.FC = () => {
  const [templates, setTemplates] = useState<OverlayTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<OverlayTemplate | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [configValues, setConfigValues] = useState<Record<string, any>>({});
  const [positionX, setPositionX] = useState(0.02);
  const [positionY, setPositionY] = useState(0.02);
  const [opacity, setOpacity] = useState(1.0);
  const [assetName, setAssetName] = useState('');
  const [creating, setCreating] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      setLoading(true);
      const response = await api.get('/templates');
      setTemplates(response.data);
    } catch (err) {
      console.error('Failed to fetch templates:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredTemplates = categoryFilter
    ? templates.filter(t => t.category === categoryFilter)
    : templates;

  const openWizard = (template: OverlayTemplate) => {
    setSelectedTemplate(template);
    const defaults = JSON.parse(template.default_config);
    setConfigValues(defaults);
    setAssetName(template.name);
    setPositionX(0.02);
    setPositionY(0.02);
    setOpacity(1.0);
    setTestResult(null);
    setWizardOpen(true);
  };

  const closeWizard = () => {
    setWizardOpen(false);
    setSelectedTemplate(null);
  };

  const handleCreate = async () => {
    if (!selectedTemplate) return;
    setCreating(true);
    try {
      await api.post('/templates/instances', {
        template_id: selectedTemplate.id,
        config_values: JSON.stringify(configValues),
        name: assetName,
        position_x: positionX,
        position_y: positionY,
        opacity,
      });
      closeWizard();
      // Navigate to My Assets to see the created asset
      window.location.href = '/assets';
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create asset from template');
    } finally {
      setCreating(false);
    }
  };

  const renderField = (field: ConfigField) => {
    const value = configValues[field.key] ?? field.default ?? '';

    switch (field.type) {
      case 'text':
        return (
          <input
            type="text"
            value={value}
            placeholder={field.placeholder}
            onChange={(e) => setConfigValues({ ...configValues, [field.key]: e.target.value })}
            className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        );
      case 'select':
        return (
          <select
            value={value}
            onChange={(e) => setConfigValues({ ...configValues, [field.key]: e.target.value })}
            className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {field.options?.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        );
      case 'number':
        return (
          <input
            type="number"
            value={value}
            min={field.min}
            max={field.max}
            onChange={(e) => setConfigValues({ ...configValues, [field.key]: parseInt(e.target.value) || 0 })}
            className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        );
      default:
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => setConfigValues({ ...configValues, [field.key]: e.target.value })}
            className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        );
    }
  };

  const schema = selectedTemplate ? JSON.parse(selectedTemplate.config_schema) : null;
  const fields: ConfigField[] = schema?.fields || [];

  return (
    <div className="space-y-4">
      {/* Category filters */}
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => {
          const isComingSoon = COMING_SOON_CATEGORIES.includes(cat);
          const label = cat === '' ? 'All' : CATEGORY_LABELS[cat] || cat;
          return (
            <button
              key={cat}
              onClick={() => !isComingSoon && setCategoryFilter(cat)}
              disabled={isComingSoon}
              className={`flex items-center px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                categoryFilter === cat
                  ? 'bg-primary-600 text-white'
                  : isComingSoon
                    ? 'bg-dark-700 text-gray-600 cursor-not-allowed'
                    : 'bg-dark-700 text-gray-400 hover:bg-dark-600 hover:text-gray-300'
              }`}
            >
              {isComingSoon && <LockClosedIcon className="h-3 w-3 mr-1" />}
              {label}
              {isComingSoon && <span className="ml-1 text-[10px]">Soon</span>}
            </button>
          );
        })}
      </div>

      {/* Template grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden animate-pulse">
              <div className="aspect-video bg-dark-700" />
              <div className="p-4 space-y-3">
                <div className="h-4 bg-dark-700 rounded w-2/3" />
                <div className="h-3 bg-dark-700 rounded w-full" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTemplates.map((template) => {
            const CatIcon = CATEGORY_ICONS[template.category] || CloudIcon;
            return (
              <div
                key={template.id}
                className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden hover:border-dark-600 transition-colors"
              >
                {/* Preview */}
                <div className="aspect-video bg-dark-900 flex items-center justify-center">
                  {template.preview_path ? (
                    <img
                      src={template.preview_path}
                      alt={template.name}
                      className="w-full h-full object-contain"
                    />
                  ) : (
                    <CatIcon className="h-16 w-16 text-gray-700" />
                  )}
                </div>

                {/* Info */}
                <div className="p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs bg-dark-700 text-gray-400 px-2 py-0.5 rounded-full">
                      {CATEGORY_LABELS[template.category] || template.category}
                    </span>
                    {template.is_bundled && (
                      <span className="text-xs bg-primary-900/50 text-primary-400 px-2 py-0.5 rounded-full">
                        Built-in
                      </span>
                    )}
                  </div>
                  <h3 className="text-sm font-medium text-white mt-2">{template.name}</h3>
                  {template.description && (
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{template.description}</p>
                  )}
                  <button
                    onClick={() => openWizard(template)}
                    className="mt-3 w-full px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Use Template
                  </button>
                </div>
              </div>
            );
          })}

          {/* Coming Soon card for social media */}
          <div className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden opacity-60">
            <div className="aspect-video bg-dark-900 flex items-center justify-center">
              <ChatBubbleLeftRightIcon className="h-16 w-16 text-gray-700" />
            </div>
            <div className="p-4">
              <span className="text-xs bg-dark-700 text-gray-500 px-2 py-0.5 rounded-full">Social Media</span>
              <h3 className="text-sm font-medium text-gray-400 mt-2">Social Media Feed</h3>
              <p className="text-xs text-gray-600 mt-1">Display live social media feeds as stream overlays</p>
              <div className="mt-3 w-full px-3 py-2 bg-dark-700 text-gray-500 rounded-lg text-sm font-medium text-center">
                Coming Soon
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Template Configuration Wizard (SlideOver) */}
      <SlideOver
        isOpen={wizardOpen}
        onClose={closeWizard}
        title={selectedTemplate?.name || 'Configure Template'}
        subtitle="Set up your overlay"
        footer={
          <div className="flex gap-3">
            <button
              onClick={closeWizard}
              className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg text-sm transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={creating}
              className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              {creating ? 'Creating...' : 'Create Asset'}
            </button>
          </div>
        }
      >
        <div className="space-y-5">
          {/* Asset name */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Asset Name</label>
            <input
              type="text"
              value={assetName}
              onChange={(e) => setAssetName(e.target.value)}
              className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Dynamic config fields */}
          {fields.map((field) => (
            <div key={field.key}>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                {field.label}
                {field.required && <span className="text-red-400 ml-1">*</span>}
              </label>
              {renderField(field)}
              {field.help && <p className="text-xs text-gray-500 mt-1">{field.help}</p>}
            </div>
          ))}

          {/* Test Connection (for weather templates) */}
          {selectedTemplate?.category === 'weather' && (
            <div>
              <button
                onClick={async () => {
                  setTestResult(null);
                  try {
                    const resp = await api.post('/templates/test-connection', {
                      template_id: selectedTemplate.id,
                      config_values: JSON.stringify(configValues),
                      name: assetName,
                      position_x: positionX,
                      position_y: positionY,
                      opacity,
                    });
                    setTestResult({ success: resp.data.success, message: resp.data.message });
                  } catch (err: any) {
                    setTestResult({ success: false, message: err.response?.data?.detail || 'Connection failed' });
                  }
                }}
                className="flex items-center px-3 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg text-sm transition-colors"
              >
                Test Connection
              </button>
              {testResult && (
                <div className={`flex items-center gap-2 mt-2 text-sm ${testResult.success ? 'text-green-400' : 'text-red-400'}`}>
                  {testResult.success ? (
                    <CheckCircleIcon className="h-4 w-4" />
                  ) : (
                    <ExclamationCircleIcon className="h-4 w-4" />
                  )}
                  {testResult.message}
                </div>
              )}
            </div>
          )}

          {/* Position picker */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Position</label>
            <PositionPicker
              positionX={positionX}
              positionY={positionY}
              onChange={(x, y) => { setPositionX(x); setPositionY(y); }}
              showRawInputs
            />
          </div>

          {/* Opacity */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Opacity: {Math.round(opacity * 100)}%
            </label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={opacity}
              onChange={(e) => setOpacity(parseFloat(e.target.value))}
              className="w-full accent-primary-500"
            />
          </div>
        </div>
      </SlideOver>
    </div>
  );
};

export default TemplateCatalog;
