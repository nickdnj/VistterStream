import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

interface ShortForgeConfig {
  id: number;
  enabled: boolean;
  camera_id: number | null;
  motion_threshold: number;
  brightness_threshold: number;
  activity_threshold: number;
  cooldown_seconds: number;
  detector_interval_seconds: number;
  max_shorts_per_day: number;
  quiet_hours_start: string;
  quiet_hours_end: string;
  min_posting_interval_minutes: number;
  default_tags: string;
  description_template: string;
  safety_gate_enabled: boolean;
  raw_clip_retention_days: number;
  rendered_clip_retention_days: number;
  snapshot_retention_days: number;
  ai_model: string;
  has_openai_key: boolean;
}

interface Camera {
  id: number;
  name: string;
}

interface CaptureWindow {
  name: string;
  label: string;
  start: string;
  end: string;
  active: boolean;
  captured: boolean;
  best_score: number | null;
}

const ShortForgeSettings: React.FC = () => {
  const [config, setConfig] = useState<ShortForgeConfig | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [captureWindows, setCaptureWindows] = useState<CaptureWindow[]>([]);
  const [form, setForm] = useState<Partial<ShortForgeConfig> & { openai_api_key?: string }>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get('/shortforge/config'),
      api.get('/cameras'),
      api.get('/shortforge/status'),
    ]).then(([configRes, camerasRes, statusRes]) => {
      setConfig(configRes.data);
      setCameras(camerasRes.data);
      setCaptureWindows(statusRes.data.capture_windows || []);
      setForm({
        enabled: configRes.data.enabled,
        camera_id: configRes.data.camera_id,
        motion_threshold: configRes.data.motion_threshold,
        brightness_threshold: configRes.data.brightness_threshold,
        activity_threshold: configRes.data.activity_threshold,
        cooldown_seconds: configRes.data.cooldown_seconds,
        max_shorts_per_day: configRes.data.max_shorts_per_day,
        min_posting_interval_minutes: configRes.data.min_posting_interval_minutes,
        default_tags: configRes.data.default_tags,
        description_template: configRes.data.description_template,
        safety_gate_enabled: configRes.data.safety_gate_enabled,
        ai_model: configRes.data.ai_model,
      });
    }).catch(console.error);
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/shortforge/config', form);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error('Failed to save ShortForge config:', err);
    } finally {
      setSaving(false);
    }
  };

  if (!config) return <div className="text-gray-400 text-center py-8">Loading ShortForge settings...</div>;

  return (
    <div className="space-y-6">
      {/* Pipeline Control */}
      <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
        <h2 className="text-xl font-semibold text-white mb-4">Pipeline Control</h2>
        <div className="space-y-4">
          <label className="flex items-center justify-between">
            <span className="text-sm text-gray-300">Enable ShortForge</span>
            <button
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${form.enabled ? 'bg-primary-600' : 'bg-dark-600'}`}
              onClick={() => setForm(f => ({ ...f, enabled: !f.enabled }))}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${form.enabled ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </label>
          <div>
            <label className="text-sm text-gray-400">Camera</label>
            <select
              className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
              value={form.camera_id || ''}
              onChange={e => setForm(f => ({ ...f, camera_id: e.target.value ? parseInt(e.target.value) : null }))}
            >
              <option value="">Select camera...</option>
              {cameras.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm text-gray-400">Max shorts per day</label>
            <input
              type="number" min="1" max="50"
              className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
              value={form.max_shorts_per_day || 6}
              onChange={e => setForm(f => ({ ...f, max_shorts_per_day: parseInt(e.target.value) || 6 }))}
            />
          </div>
        </div>
      </div>

      {/* Capture Windows */}
      <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
        <h2 className="text-xl font-semibold text-white mb-2">Capture Windows</h2>
        <p className="text-sm text-gray-500 mb-4">Shorts are captured during these windows based on sunrise/sunset at your location. Best-scoring snapshot wins each window.</p>
        <div className="space-y-2">
          {captureWindows.map(w => {
            const start = new Date(w.start).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
            const end = new Date(w.end).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
            return (
              <div key={w.name} className={`flex items-center justify-between rounded-lg px-4 py-3 ${w.active ? 'bg-yellow-500/10 border border-yellow-500/30' : 'bg-dark-700'}`}>
                <div>
                  <p className="text-sm text-gray-200 font-medium">{w.label}</p>
                  <p className="text-xs text-gray-500">{start} – {end}</p>
                </div>
                <div className="flex items-center gap-3">
                  {w.captured && <span className="text-xs text-green-400 font-medium">Captured</span>}
                  {w.active && <span className="text-xs text-yellow-400 font-medium">Active now</span>}
                  {w.best_score !== null && <span className="text-xs text-gray-400">Best: {w.best_score.toFixed(3)}</span>}
                  {!w.active && !w.captured && <span className="text-xs text-gray-600">Scheduled</span>}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Content & Safety */}
      <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
        <h2 className="text-xl font-semibold text-white mb-4">Content & Safety</h2>
        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400">Default tags (comma-separated)</label>
            <input
              type="text"
              className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
              value={form.default_tags || ''}
              onChange={e => setForm(f => ({ ...f, default_tags: e.target.value }))}
              placeholder="marina, live camera, jersey shore"
            />
          </div>
          <div>
            <label className="text-sm text-gray-400">Description template</label>
            <textarea
              rows={2}
              className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
              value={form.description_template || ''}
              onChange={e => setForm(f => ({ ...f, description_template: e.target.value }))}
              placeholder="{{headline}} | {{location}} | {{conditions}}"
            />
          </div>
          <label className="flex items-center justify-between">
            <span className="text-sm text-gray-300">Safety gate (AI content review)</span>
            <button
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${form.safety_gate_enabled ? 'bg-primary-600' : 'bg-dark-600'}`}
              onClick={() => setForm(f => ({ ...f, safety_gate_enabled: !f.safety_gate_enabled }))}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${form.safety_gate_enabled ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </label>
          <label className="flex items-center justify-between">
            <span className="text-sm text-gray-300">Person detection filter</span>
            <span className="text-xs text-green-400">Always on</span>
          </label>
        </div>
      </div>

      {/* AI Configuration */}
      <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
        <h2 className="text-xl font-semibold text-white mb-4">AI Configuration</h2>
        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400">OpenAI API Key</label>
            <input
              type="password"
              className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
              placeholder={config.has_openai_key ? '••••••••' : 'Enter API key...'}
              onChange={e => setForm(f => ({ ...f, openai_api_key: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-sm text-gray-400">AI Model</label>
            <select
              className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
              value={form.ai_model || 'gpt-4o-mini'}
              onChange={e => setForm(f => ({ ...f, ai_model: e.target.value }))}
            >
              <option value="gpt-4o-mini">GPT-4o Mini (fast, low cost)</option>
              <option value="gpt-4o">GPT-4o (better quality)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Save button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className={`px-6 py-2 rounded-lg font-medium text-sm transition-colors ${
            saved ? 'bg-green-600 text-white' :
            saving ? 'bg-dark-600 text-gray-400' :
            'bg-primary-600 text-white hover:bg-primary-700'
          }`}
        >
          {saved ? 'Saved!' : saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
};

export default ShortForgeSettings;
