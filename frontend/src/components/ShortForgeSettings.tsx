import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { TrashIcon, PlusIcon } from '@heroicons/react/24/outline';

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

interface TimelineOption {
  id: number;
  name: string;
}

interface PresetInfo {
  camera_id: number;
  camera_name: string;
  preset_id: number;
  preset_name: string;
  snapshot_url: string | null;
}

interface WindowConfig {
  name: string;
  label: string;
  reference: 'sunrise' | 'sunset' | 'fixed';
  offset_minutes: number;
  duration_minutes: number;
  enabled: boolean;
}

interface CaptureWindowStatus {
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
  const [timelines, setTimelines] = useState<TimelineOption[]>([]);
  const [presets, setPresets] = useState<PresetInfo[]>([]);
  const [windowConfigs, setWindowConfigs] = useState<WindowConfig[]>([]);
  const [windowStatuses, setWindowStatuses] = useState<CaptureWindowStatus[]>([]);
  const [form, setForm] = useState<Partial<ShortForgeConfig> & { openai_api_key?: string; timeline_id?: number | null; narration_voice?: string; narration_speed?: number; narration_persona?: string; narration_prompt?: string }>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testingPreset, setTestingPreset] = useState<number | null>(null);
  const [narrationPresets, setNarrationPresets] = useState<Record<string, { label: string; voice: string; prompt: string }>>({});
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewAudio, setPreviewAudio] = useState<HTMLAudioElement | null>(null);

  useEffect(() => {
    Promise.all([
      api.get('/shortforge/config'),
      api.get('/cameras'),
      api.get('/timelines'),
      api.get('/shortforge/status'),
      api.get('/shortforge/capture-windows'),
      api.get('/shortforge/narration-presets').catch(() => ({ data: {} })),
    ]).then(([configRes, camerasRes, timelinesRes, statusRes, windowsRes, presetsRes]) => {
      setConfig(configRes.data);
      setCameras(camerasRes.data);
      setTimelines(timelinesRes.data || []);
      setWindowStatuses(statusRes.data.capture_windows || []);
      setWindowConfigs(windowsRes.data || []);
      setNarrationPresets(presetsRes.data || {});
      const cfg = configRes.data;
      setForm({
        enabled: cfg.enabled,
        camera_id: cfg.camera_id,
        timeline_id: cfg.timeline_id,
        max_shorts_per_day: cfg.max_shorts_per_day,
        default_tags: cfg.default_tags,
        description_template: cfg.description_template,
        safety_gate_enabled: cfg.safety_gate_enabled,
        ai_model: cfg.ai_model,
        narration_voice: cfg.narration_voice || 'shimmer',
        narration_speed: cfg.narration_speed ?? 0.95,
        narration_persona: cfg.narration_persona || 'chill_surfer',
        narration_prompt: cfg.narration_prompt || '',
        text_position: cfg.text_position || 'upper',
      });
      // Load presets if timeline is set
      if (cfg.timeline_id) {
        api.get(`/shortforge/timeline-presets/${cfg.timeline_id}`).then(res => {
          setPresets(res.data.presets || []);
        }).catch(() => {});
      }
    }).catch(console.error);
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await Promise.all([
        api.put('/shortforge/config', form),
        api.put('/shortforge/capture-windows', windowConfigs),
      ]);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error('Failed to save ShortForge config:', err);
    } finally {
      setSaving(false);
    }
  };

  const addWindow = () => {
    const id = Date.now();
    setWindowConfigs(prev => [...prev, {
      name: `custom_${id}`,
      label: 'New Window',
      reference: 'sunrise',
      offset_minutes: 120,
      duration_minutes: 60,
      enabled: true,
    }]);
  };

  const removeWindow = (index: number) => {
    setWindowConfigs(prev => prev.filter((_, i) => i !== index));
  };

  const updateWindow = (index: number, field: string, value: any) => {
    setWindowConfigs(prev => prev.map((w, i) => i === index ? { ...w, [field]: value } : w));
  };

  const formatOffset = (ref: string, offset: number): string => {
    const absMin = Math.abs(offset);
    const hrs = Math.floor(absMin / 60);
    const mins = absMin % 60;
    const timeStr = hrs > 0 ? `${hrs}h${mins > 0 ? ` ${mins}m` : ''}` : `${mins}m`;
    if (offset === 0) return `At ${ref}`;
    return offset > 0 ? `${timeStr} after ${ref}` : `${timeStr} before ${ref}`;
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
            <label className="text-sm text-gray-400">Timeline</label>
            <select
              className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
              value={form.timeline_id || ''}
              onChange={e => {
                const tid = e.target.value ? parseInt(e.target.value) : null;
                setForm(f => ({ ...f, timeline_id: tid }));
                if (tid) {
                  api.get(`/shortforge/timeline-presets/${tid}`).then(res => {
                    setPresets(res.data.presets || []);
                  }).catch(() => setPresets([]));
                } else {
                  setPresets([]);
                }
              }}
            >
              <option value="">Select timeline...</option>
              {timelines.map(t => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>

          {/* Presets from selected timeline */}
          {presets.length > 0 && (
            <div>
              <label className="text-sm text-gray-400 mb-2 block">Presets ({presets.length})</label>
              <div className="space-y-2">
                {presets.map(p => (
                  <div key={p.preset_id} className="flex items-center justify-between bg-dark-700 rounded-lg px-3 py-2">
                    <div>
                      <span className="text-sm text-gray-200">{p.preset_name}</span>
                      <span className="text-xs text-gray-500 ml-2">({p.camera_name})</span>
                    </div>
                    <button
                      onClick={async () => {
                        setTestingPreset(p.preset_id);
                        try {
                          const res = await api.post(`/shortforge/test-capture/${p.preset_id}`);
                          // Reset after short delay — pipeline runs in background
                          setTimeout(() => setTestingPreset(null), 5000);
                        } catch (err: any) {
                          const msg = err?.response?.data?.detail || 'Test capture failed';
                          alert(msg);
                          setTestingPreset(null);
                        }
                      }}
                      disabled={testingPreset === p.preset_id}
                      className={`text-xs px-2.5 py-1 rounded font-medium ${testingPreset === p.preset_id ? 'bg-green-600/80 text-green-100' : 'bg-dark-600 text-gray-300 hover:bg-primary-600 hover:text-white'}`}
                    >
                      {testingPreset === p.preset_id ? 'Building...' : 'Test'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

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
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Capture Windows</h2>
            <p className="text-sm text-gray-500 mt-1">Define when shorts are captured based on sunrise/sunset</p>
          </div>
          <button
            onClick={addWindow}
            className="flex items-center gap-1 px-3 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm"
          >
            <PlusIcon className="h-4 w-4" />
            Add Window
          </button>
        </div>

        <div className="space-y-3">
          {windowConfigs.map((w, i) => {
            const status = windowStatuses.find(s => s.name === w.name);
            return (
              <div key={w.name} className={`rounded-lg border p-4 ${w.enabled ? 'border-dark-600 bg-dark-700' : 'border-dark-700 bg-dark-800 opacity-60'}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 space-y-3">
                    {/* Label */}
                    <input
                      type="text"
                      className="bg-transparent text-sm font-medium text-gray-200 border-b border-dark-600 focus:border-primary-500 outline-none w-full pb-1"
                      value={w.label}
                      onChange={e => updateWindow(i, 'label', e.target.value)}
                    />

                    {/* Reference + Offset */}
                    <div className="flex flex-wrap gap-2">
                      <select
                        className="bg-dark-600 border border-dark-500 rounded px-2 py-1 text-xs text-gray-200"
                        value={w.reference}
                        onChange={e => updateWindow(i, 'reference', e.target.value)}
                      >
                        <option value="sunrise">Sunrise</option>
                        <option value="sunset">Sunset</option>
                        <option value="fixed">Fixed time</option>
                      </select>
                      {w.reference === 'fixed' ? (
                        <div className="flex items-center gap-1">
                          <input
                            type="time"
                            className="bg-dark-600 border border-dark-500 rounded px-2 py-1 text-xs text-gray-200"
                            value={`${String(Math.floor((w.offset_minutes + 240) / 60) % 24).padStart(2, '0')}:${String(Math.abs(w.offset_minutes + 240) % 60).padStart(2, '0')}`}
                            onChange={e => {
                              const [h, m] = e.target.value.split(':').map(Number);
                              // Convert local EDT (UTC-4) to minutes-from-midnight-UTC
                              updateWindow(i, 'offset_minutes', (h + 4) * 60 + m);
                            }}
                          />
                          <span className="text-xs text-gray-500">local time</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            className="bg-dark-600 border border-dark-500 rounded px-2 py-1 text-xs text-gray-200 w-20"
                            value={w.offset_minutes}
                            onChange={e => updateWindow(i, 'offset_minutes', parseInt(e.target.value) || 0)}
                          />
                          <span className="text-xs text-gray-500">min offset</span>
                        </div>
                      )}
                      <div className="flex items-center gap-1">
                        <input
                          type="number" min="15" max="480"
                          className="bg-dark-600 border border-dark-500 rounded px-2 py-1 text-xs text-gray-200 w-20"
                          value={w.duration_minutes}
                          onChange={e => updateWindow(i, 'duration_minutes', parseInt(e.target.value) || 60)}
                        />
                        <span className="text-xs text-gray-500">min duration</span>
                      </div>
                    </div>

                    {/* Computed info */}
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-gray-500">{formatOffset(w.reference, w.offset_minutes)}</span>
                      {status && <span className="text-gray-500">Today: {new Date(status.start).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })} – {new Date(status.end).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</span>}
                      {status?.active && <span className="text-yellow-400 font-medium">Active now</span>}
                      {status?.captured && <span className="text-green-400 font-medium">Captured</span>}
                    </div>
                  </div>

                  {/* Controls */}
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${w.enabled ? 'bg-primary-600' : 'bg-dark-500'}`}
                      onClick={() => updateWindow(i, 'enabled', !w.enabled)}
                    >
                      <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${w.enabled ? 'translate-x-5' : 'translate-x-1'}`} />
                    </button>
                    <button
                      onClick={() => removeWindow(i)}
                      className="text-gray-500 hover:text-red-400 p-1"
                      title="Remove window"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
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

      {/* Narration */}
      <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
        <h2 className="text-xl font-semibold text-white mb-4">Narration</h2>
        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400">Persona</label>
            <select
              className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
              value={form.narration_persona || 'chill_surfer'}
              onChange={e => {
                const key = e.target.value;
                const preset = narrationPresets[key];
                if (preset) {
                  setForm(f => ({ ...f, narration_persona: key, narration_voice: preset.voice }));
                } else {
                  setForm(f => ({ ...f, narration_persona: key }));
                }
              }}
            >
              {Object.entries(narrationPresets).map(([key, preset]) => (
                <option key={key} value={key}>{preset.label}</option>
              ))}
              <option value="custom">Custom</option>
            </select>
          </div>
          {form.narration_persona && form.narration_persona !== 'custom' && narrationPresets[form.narration_persona] && (
            <p className="text-xs text-gray-500 italic">{narrationPresets[form.narration_persona].prompt}</p>
          )}
          {form.narration_persona === 'custom' && (
            <div>
              <label className="text-sm text-gray-400">Custom prompt</label>
              <textarea
                rows={4}
                className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
                value={form.narration_prompt || ''}
                onChange={e => setForm(f => ({ ...f, narration_prompt: e.target.value }))}
                placeholder="Describe the personality and style for the narration..."
              />
            </div>
          )}
          <div>
            <label className="text-sm text-gray-400">Voice</label>
            <select
              className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
              value={form.narration_voice || 'shimmer'}
              onChange={e => setForm(f => ({ ...f, narration_voice: e.target.value }))}
            >
              {[
                { id: 'alloy', desc: 'Neutral, balanced — great for weather anchor' },
                { id: 'echo', desc: 'Warm, smooth male — relaxed and conversational' },
                { id: 'fable', desc: 'Expressive, storytelling — British-accented' },
                { id: 'nova', desc: 'Friendly, upbeat female — energetic and clear' },
                { id: 'onyx', desc: 'Deep, authoritative male — captain vibes' },
                { id: 'shimmer', desc: 'Soft, pleasant female — calm and inviting' },
              ].map(v => (
                <option key={v.id} value={v.id}>{v.id.charAt(0).toUpperCase() + v.id.slice(1)} — {v.desc}</option>
              ))}
            </select>
          </div>
          <div>
            <div className="flex justify-between text-sm text-gray-400 mb-1">
              <span>Speed</span>
              <span>{(form.narration_speed || 0.95).toFixed(2)}x</span>
            </div>
            <input
              type="range"
              min="0.5" max="2.0" step="0.05"
              value={form.narration_speed || 0.95}
              onChange={e => setForm(f => ({ ...f, narration_speed: parseFloat(e.target.value) }))}
              className="w-full accent-primary-600"
            />
          </div>
          <button
            onClick={async () => {
              if (previewAudio) { previewAudio.pause(); setPreviewAudio(null); }
              setPreviewLoading(true);
              try {
                const res = await api.get(
                  `/shortforge/voice-preview?voice=${form.narration_voice || 'shimmer'}&speed=${form.narration_speed || 0.95}`,
                  { responseType: 'blob' }
                );
                const url = URL.createObjectURL(res.data);
                const audio = new Audio(url);
                setPreviewAudio(audio);
                audio.play();
                audio.onended = () => { URL.revokeObjectURL(url); setPreviewAudio(null); };
              } catch (err) {
                console.error('Preview failed:', err);
                alert('Preview failed — check OpenAI API key');
              } finally {
                setPreviewLoading(false);
              }
            }}
            disabled={previewLoading}
            className={`w-full px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              previewLoading ? 'bg-dark-600 text-gray-400' :
              previewAudio ? 'bg-yellow-600 text-white' :
              'bg-dark-700 text-gray-300 hover:bg-primary-600 hover:text-white'
            }`}
          >
            {previewLoading ? 'Generating preview...' : previewAudio ? 'Playing...' : 'Preview Voice'}
          </button>
          <div>
            <label className="text-sm text-gray-400">Text Position</label>
            <select
              className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
              value={form.text_position || 'upper'}
              onChange={e => setForm(f => ({ ...f, text_position: e.target.value }))}
            >
              <option value="upper">Upper — near the top of the frame</option>
              <option value="center">Center — middle of the frame</option>
              <option value="lower">Lower — near the bottom of the frame</option>
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
