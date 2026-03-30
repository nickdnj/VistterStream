import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import {
  SparklesIcon,
  Cog6ToothIcon,
  XMarkIcon,
  PlayIcon,
  PauseIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  ArrowPathIcon,
  TrashIcon,
  ArrowTopRightOnSquareIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  VideoCameraIcon,
  SignalIcon,
} from '@heroicons/react/24/outline';

// Types
interface PipelineStatus {
  enabled: boolean;
  camera_id: number | null;
  camera_name: string | null;
  state: string;
  shorts_today: number;
  max_shorts_per_day: number;
  moments_today: number;
  next_post: string | null;
  disk_usage_mb: number;
  timezone: string;
}

interface ShortItem {
  id: number;
  clip_id: number;
  youtube_video_id: string | null;
  title: string | null;
  description: string | null;
  views: number;
  published_at: string | null;
  status: string;
  error_message: string | null;
  headline: string | null;
  rendered_path: string | null;
  duration_seconds: number | null;
  safe_to_publish: boolean | null;
  moment_id: number | null;
  trigger_type: string | null;
  score: number | null;
  frame_path: string | null;
  moment_timestamp: string | null;
}

interface MomentItem {
  id: number;
  camera_id: number;
  timestamp: string;
  trigger_type: string;
  score: number;
  frame_path: string | null;
  status: string;
  error_message: string | null;
}

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

// Status badge component
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, string> = {
    published: 'bg-green-900/50 text-green-400',
    queued: 'bg-yellow-900/50 text-yellow-400',
    failed: 'bg-red-900/50 text-red-400',
    removed: 'bg-gray-800 text-gray-500',
    detected: 'bg-blue-900/50 text-blue-400',
    captured: 'bg-cyan-900/50 text-cyan-400',
    rendered: 'bg-purple-900/50 text-purple-400',
    skipped: 'bg-gray-800 text-gray-500',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-800 text-gray-400'}`}>
      {status}
    </span>
  );
};

// Trigger type badge
const TriggerBadge: React.FC<{ type: string }> = ({ type }) => {
  const colors: Record<string, string> = {
    motion: 'bg-blue-900/50 text-blue-400',
    brightness: 'bg-amber-900/50 text-amber-400',
    activity: 'bg-green-900/50 text-green-400',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[type] || 'bg-gray-800 text-gray-400'}`}>
      {type}
    </span>
  );
};

// Pipeline status bar
const PipelineStatusBar: React.FC<{ status: PipelineStatus }> = ({ status }) => {
  const stateColors: Record<string, string> = {
    running: 'bg-green-500',
    idle: 'bg-yellow-500',
    paused: 'bg-yellow-500',
    error: 'bg-red-500',
    disabled: 'bg-gray-500',
  };

  const stateLabels: Record<string, string> = {
    running: 'Running',
    idle: 'Idle — start timeline to detect',
    paused: 'Paused',
    error: 'Error',
    disabled: 'Disabled',
  };

  return (
    <div className="bg-dark-800 border-b border-dark-700 px-6 py-3">
      <div className="flex flex-wrap items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${stateColors[status.state] || 'bg-gray-500'}`} />
          <span className="text-gray-300 font-medium">{stateLabels[status.state] || status.state}</span>
        </div>
        <div className="text-gray-400">
          <span className="text-white font-medium">{status.shorts_today}</span>/{status.max_shorts_per_day} shorts today
        </div>
        <div className="text-gray-400">
          <span className="text-white font-medium">{status.moments_today}</span> moments
        </div>
        {status.camera_name && (
          <div className="text-gray-400 flex items-center gap-1">
            <VideoCameraIcon className="h-4 w-4" />
            {status.camera_name}
          </div>
        )}
        <div className="text-gray-400">
          Disk: <span className="text-white">{status.disk_usage_mb.toFixed(1)}</span> MB
        </div>
      </div>
    </div>
  );
};

// Short card
const ShortCard: React.FC<{ short: ShortItem; onClick: () => void }> = ({ short, onClick }) => {
  const formatViews = (v: number) => {
    if (v >= 1000000) return `${(v / 1000000).toFixed(1)}M`;
    if (v >= 1000) return `${(v / 1000).toFixed(1)}K`;
    return v.toString();
  };

  const formatTime = (ts: string | null) => {
    if (!ts) return '';
    return new Date(ts).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  };

  return (
    <div
      className="bg-dark-800 rounded-lg border border-dark-700 hover:border-dark-600 cursor-pointer transition-colors overflow-hidden"
      onClick={onClick}
    >
      {/* Video thumbnail (9:16 aspect) */}
      <div className="relative bg-dark-700 w-full" style={{ aspectRatio: '9/16', maxHeight: '12rem' }}>
        {short.clip_id ? (
          <video
            className="absolute inset-0 w-full h-full object-cover"
            src={`/api/shortforge/clips/${short.clip_id}/video`}
            muted
            loop
            playsInline
            onMouseEnter={e => (e.target as HTMLVideoElement).play().catch(() => {})}
            onMouseLeave={e => { const v = e.target as HTMLVideoElement; v.pause(); v.currentTime = 0; }}
            preload="metadata"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-gray-500">
            <SparklesIcon className="h-8 w-8" />
          </div>
        )}
        <div className="absolute top-2 left-2">
          <StatusBadge status={short.status} />
        </div>
        {short.score !== null && (
          <div className="absolute top-2 right-2 bg-dark-900/80 px-1.5 py-0.5 rounded text-xs text-gray-300">
            {short.score.toFixed(2)}
          </div>
        )}
      </div>
      <div className="p-3">
        <p className="text-sm text-gray-200 line-clamp-2 mb-1">{short.headline || short.title || 'Untitled'}</p>
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span>{formatViews(short.views)} views</span>
          <span>{formatTime(short.published_at)}</span>
        </div>
      </div>
    </div>
  );
};

// Short detail slide-over
const ShortDetailSlideOver: React.FC<{
  short: ShortItem | null;
  isOpen: boolean;
  onClose: () => void;
  onDelete: (id: number) => void;
}> = ({ short, isOpen, onClose, onDelete }) => {
  if (!short) return null;

  const formatDate = (ts: string | null) => {
    if (!ts) return '—';
    return new Date(ts).toLocaleString();
  };

  return (
    <>
      {isOpen && <div className="fixed inset-0 bg-dark-900/75 z-40" onClick={onClose} />}
      <div className={`fixed inset-y-0 right-0 w-full max-w-md bg-dark-800 shadow-xl z-50 transform transition-transform duration-300 ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-dark-700 shrink-0">
            <h2 className="text-lg font-semibold text-white">Short Detail</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-white">
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Video preview */}
            <div className="bg-dark-900 rounded-lg mx-auto overflow-hidden" style={{ width: '220px', aspectRatio: '9/16' }}>
              {short.clip_id ? (
                <video
                  className="w-full h-full object-contain"
                  style={{ objectFit: 'contain', backgroundColor: '#000' }}
                  src={`/api/shortforge/clips/${short.clip_id}/video`}
                  controls
                  playsInline
                  preload="metadata"
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <SparklesIcon className="h-12 w-12" />
                </div>
              )}
            </div>

            {/* Headline */}
            <div>
              <h3 className="text-xl font-semibold text-white">{short.headline || short.title || 'Untitled'}</h3>
              <p className="text-sm text-gray-400 mt-1">
                Published {formatDate(short.published_at)} · {short.views.toLocaleString()} views
              </p>
            </div>

            {/* Quality score */}
            {short.score !== null && (
              <div>
                <p className="text-sm text-gray-400 mb-1">Quality score: {short.score.toFixed(2)}</p>
                <div className="w-full bg-dark-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${short.score >= 0.7 ? 'bg-green-500' : short.score >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${Math.min(100, short.score * 100)}%` }}
                  />
                </div>
              </div>
            )}

            {/* Trigger info */}
            <div className="bg-dark-900 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-3">Trigger Moment</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-gray-500">Type</p>
                  <p className="text-gray-200">{short.trigger_type || '—'}</p>
                </div>
                <div>
                  <p className="text-gray-500">Score</p>
                  <p className="text-gray-200">{short.score?.toFixed(3) || '—'}</p>
                </div>
                <div>
                  <p className="text-gray-500">Duration</p>
                  <p className="text-gray-200">{short.duration_seconds ? `${short.duration_seconds.toFixed(1)}s` : '—'}</p>
                </div>
                <div>
                  <p className="text-gray-500">Status</p>
                  <StatusBadge status={short.status} />
                </div>
              </div>
            </div>

            {/* Error message */}
            {short.error_message && (
              <div className="bg-red-900/20 border border-red-800 rounded-lg p-4">
                <p className="text-sm text-red-400">{short.error_message}</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center gap-3 px-6 py-4 border-t border-dark-700 shrink-0">
            {short.youtube_video_id && (
              <a
                href={`https://youtube.com/shorts/${short.youtube_video_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium"
              >
                <ArrowTopRightOnSquareIcon className="h-4 w-4" />
                Open on YouTube
              </a>
            )}
            <button
              onClick={() => onDelete(short.id)}
              className="flex items-center justify-center gap-2 px-4 py-2 bg-dark-700 text-gray-300 rounded-lg hover:bg-dark-600 text-sm"
            >
              <TrashIcon className="h-4 w-4" />
              Delete
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

// Settings slide-over
const SettingsSlideOver: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  config: ShortForgeConfig | null;
  cameras: Camera[];
  onSave: (update: Partial<ShortForgeConfig> & { openai_api_key?: string }) => void;
}> = ({ isOpen, onClose, config, cameras, onSave }) => {
  const [form, setForm] = useState<Partial<ShortForgeConfig> & { openai_api_key?: string }>({});

  useEffect(() => {
    if (config) {
      setForm({
        enabled: config.enabled,
        camera_id: config.camera_id,
        motion_threshold: config.motion_threshold,
        brightness_threshold: config.brightness_threshold,
        activity_threshold: config.activity_threshold,
        cooldown_seconds: config.cooldown_seconds,
        max_shorts_per_day: config.max_shorts_per_day,
        quiet_hours_start: config.quiet_hours_start,
        quiet_hours_end: config.quiet_hours_end,
        min_posting_interval_minutes: config.min_posting_interval_minutes,
        default_tags: config.default_tags,
        description_template: config.description_template,
        safety_gate_enabled: config.safety_gate_enabled,
        ai_model: config.ai_model,
      });
    }
  }, [config]);

  const handleSave = () => {
    onSave(form);
    onClose();
  };

  return (
    <>
      {isOpen && <div className="fixed inset-0 bg-dark-900/75 z-40" onClick={onClose} />}
      <div className={`fixed inset-y-0 right-0 w-full max-w-lg bg-dark-800 shadow-xl z-50 transform transition-transform duration-300 ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-dark-700 shrink-0">
            <h2 className="text-lg font-semibold text-white">ShortForge Settings</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-white">
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Pipeline Control */}
            <section>
              <h3 className="text-sm font-medium text-gray-300 mb-3">Pipeline Control</h3>
              <div className="space-y-3">
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
                  <label className="text-xs text-gray-400">Camera</label>
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
              </div>
            </section>

            {/* Detection Thresholds */}
            <section>
              <h3 className="text-sm font-medium text-gray-300 mb-3">Detection Thresholds</h3>
              <div className="space-y-3">
                {[
                  { label: 'Motion', key: 'motion_threshold' as const },
                  { label: 'Brightness', key: 'brightness_threshold' as const },
                  { label: 'Activity', key: 'activity_threshold' as const },
                ].map(({ label, key }) => (
                  <div key={key}>
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                      <span>{label}</span>
                      <span>{((form[key] as number) || 0).toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0" max="1" step="0.05"
                      value={(form[key] as number) || 0}
                      onChange={e => setForm(f => ({ ...f, [key]: parseFloat(e.target.value) }))}
                      className="w-full accent-primary-600"
                    />
                  </div>
                ))}
                <div>
                  <label className="text-xs text-gray-400">Cooldown (seconds between moments)</label>
                  <input
                    type="number" min="10" max="3600"
                    className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
                    value={form.cooldown_seconds || 120}
                    onChange={e => setForm(f => ({ ...f, cooldown_seconds: parseInt(e.target.value) || 120 }))}
                  />
                </div>
              </div>
            </section>

            {/* Posting Rules */}
            <section>
              <h3 className="text-sm font-medium text-gray-300 mb-3">Posting Rules</h3>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400">Max shorts per day</label>
                  <input
                    type="number" min="1" max="50"
                    className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
                    value={form.max_shorts_per_day || 6}
                    onChange={e => setForm(f => ({ ...f, max_shorts_per_day: parseInt(e.target.value) || 6 }))}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-400">Quiet hours start</label>
                    <input
                      type="time"
                      className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
                      value={form.quiet_hours_start || '22:00'}
                      onChange={e => setForm(f => ({ ...f, quiet_hours_start: e.target.value }))}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400">Quiet hours end</label>
                    <input
                      type="time"
                      className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
                      value={form.quiet_hours_end || '06:00'}
                      onChange={e => setForm(f => ({ ...f, quiet_hours_end: e.target.value }))}
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-gray-400">Min interval between posts (minutes)</label>
                  <input
                    type="number" min="5" max="1440"
                    className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
                    value={form.min_posting_interval_minutes || 60}
                    onChange={e => setForm(f => ({ ...f, min_posting_interval_minutes: parseInt(e.target.value) || 60 }))}
                  />
                </div>
              </div>
            </section>

            {/* Content Defaults */}
            <section>
              <h3 className="text-sm font-medium text-gray-300 mb-3">Content Defaults</h3>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400">Default tags (comma-separated)</label>
                  <input
                    type="text"
                    className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
                    value={form.default_tags || ''}
                    onChange={e => setForm(f => ({ ...f, default_tags: e.target.value }))}
                    placeholder="marina, live camera, jersey shore"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400">Description template</label>
                  <textarea
                    rows={3}
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
              </div>
            </section>

            {/* AI Config */}
            <section>
              <h3 className="text-sm font-medium text-gray-300 mb-3">AI Configuration</h3>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400">OpenAI API Key</label>
                  <input
                    type="password"
                    className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
                    placeholder={config?.has_openai_key ? '••••••••' : 'sk-...'}
                    onChange={e => setForm(f => ({ ...f, openai_api_key: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400">AI Model</label>
                  <select
                    className="w-full mt-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-200"
                    value={form.ai_model || 'gpt-4o-mini'}
                    onChange={e => setForm(f => ({ ...f, ai_model: e.target.value }))}
                  >
                    <option value="gpt-4o-mini">GPT-4o Mini</option>
                    <option value="gpt-4o">GPT-4o</option>
                  </select>
                </div>
              </div>
            </section>
          </div>

          {/* Footer */}
          <div className="flex items-center gap-3 px-6 py-4 border-t border-dark-700 shrink-0">
            <button
              onClick={handleSave}
              className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium"
            >
              Save Settings
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-dark-700 text-gray-300 rounded-lg hover:bg-dark-600 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

// First-run guided state
const FirstRunState: React.FC<{ status: PipelineStatus }> = ({ status }) => {
  const steps = [
    { label: 'Camera connected', done: !!status.camera_name, icon: VideoCameraIcon },
    { label: 'Moment detector running', done: status.state === 'running', icon: SignalIcon },
    { label: 'Waiting for first moment...', done: status.moments_today > 0, icon: ClockIcon },
    { label: 'First short published', done: status.shorts_today > 0, icon: CheckCircleIcon },
  ];

  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="bg-dark-800 rounded-xl p-8 max-w-md w-full border border-dark-700">
        <h2 className="text-xl font-semibold text-white mb-1">ShortForge is starting up...</h2>
        <p className="text-sm text-gray-400 mb-6">Watching the camera for interesting moments.</p>
        <div className="space-y-4">
          {steps.map((step, i) => (
            <div key={i} className="flex items-center gap-3">
              {step.done ? (
                <CheckCircleIcon className="h-5 w-5 text-green-400 shrink-0" />
              ) : i === steps.findIndex(s => !s.done) ? (
                <ArrowPathIcon className="h-5 w-5 text-primary-400 animate-spin shrink-0" />
              ) : (
                <div className="h-5 w-5 rounded-full border border-dark-600 shrink-0" />
              )}
              <span className={`text-sm ${step.done ? 'text-gray-200' : 'text-gray-500'}`}>{step.label}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-6">
          First short expected in ~30 min based on typical moment frequency.
        </p>
      </div>
    </div>
  );
};

// Main ShortForge component
const ShortForge: React.FC = () => {
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);
  const [shorts, setShorts] = useState<ShortItem[]>([]);
  const [moments, setMoments] = useState<MomentItem[]>([]);
  const [config, setConfig] = useState<ShortForgeConfig | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedShort, setSelectedShort] = useState<ShortItem | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showMoments, setShowMoments] = useState(true);
  const [showScores, setShowScores] = useState(false);
  const [scoreHistory, setScoreHistory] = useState<Record<string, Array<{time: string; preset_id: number; type: string; score: number; threshold: number; triggered: boolean}>>>({});
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, shortsRes, momentsRes, scoresRes] = await Promise.all([
        api.get('/shortforge/status'),
        api.get('/shortforge/shorts?limit=12'),
        api.get('/shortforge/moments?limit=30'),
        api.get('/shortforge/scores').catch(() => ({ data: {} })),
      ]);
      setPipelineStatus(statusRes.data);
      setShorts(shortsRes.data);
      setMoments(momentsRes.data);
      setScoreHistory(scoresRes.data || {});
    } catch (err) {
      console.error('Failed to fetch ShortForge data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch + polling every 15s
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Fetch config and cameras when settings opens
  useEffect(() => {
    if (showSettings) {
      Promise.all([
        api.get('/shortforge/config'),
        api.get('/cameras'),
      ]).then(([configRes, camerasRes]) => {
        setConfig(configRes.data);
        setCameras(camerasRes.data);
      });
    }
  }, [showSettings]);

  const handleSaveConfig = async (update: Partial<ShortForgeConfig> & { openai_api_key?: string }) => {
    try {
      await api.put('/shortforge/config', update);
      fetchData();
    } catch (err) {
      console.error('Failed to save config:', err);
    }
  };

  const handleDeleteShort = async (id: number) => {
    try {
      await api.delete(`/shortforge/shorts/${id}`);
      setSelectedShort(null);
      fetchData();
    } catch (err) {
      console.error('Failed to delete short:', err);
    }
  };

  const formatTime = (ts: string) => {
    const tz = pipelineStatus?.timezone || 'America/New_York';
    return new Date(ts + (ts.endsWith('Z') ? '' : 'Z')).toLocaleTimeString([], {
      hour: 'numeric', minute: '2-digit', timeZone: tz,
    });
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className="h-full">
        <div className="bg-dark-800 border-b border-dark-700 px-6 py-3">
          <div className="flex gap-6">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-5 w-24 bg-dark-700 rounded animate-pulse" />
            ))}
          </div>
        </div>
        <div className="p-6 grid grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden">
              <div className="bg-dark-700 animate-pulse" style={{ aspectRatio: '9/16', maxHeight: '12rem' }} />
              <div className="p-3 space-y-2">
                <div className="h-4 bg-dark-700 rounded animate-pulse" />
                <div className="h-3 bg-dark-700 rounded animate-pulse w-2/3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const isFirstRun = pipelineStatus?.enabled && shorts.length === 0;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-dark-700 shrink-0">
        <div className="flex items-center gap-2">
          <SparklesIcon className="h-6 w-6 text-primary-400" />
          <h1 className="text-xl font-bold text-white">ShortForge</h1>
        </div>
        <button
          onClick={() => setShowSettings(true)}
          className="flex items-center gap-2 px-3 py-1.5 bg-dark-700 text-gray-300 rounded-lg hover:bg-dark-600 text-sm"
        >
          <Cog6ToothIcon className="h-4 w-4" />
          Settings
        </button>
      </div>

      {/* Pipeline Status Bar */}
      {pipelineStatus && <PipelineStatusBar status={pipelineStatus} />}

      {/* Disabled state */}
      {pipelineStatus && !pipelineStatus.enabled && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <SparklesIcon className="h-12 w-12 text-gray-600 mx-auto mb-4" />
            <h2 className="text-lg font-medium text-gray-300 mb-2">ShortForge is disabled</h2>
            <p className="text-sm text-gray-500 mb-4">Enable it in Settings to start generating YouTube Shorts automatically.</p>
            <button
              onClick={() => setShowSettings(true)}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium"
            >
              Open Settings
            </button>
          </div>
        </div>
      )}

      {/* First-run guided state */}
      {isFirstRun && <FirstRunState status={pipelineStatus!} />}

      {/* Main content (split layout) */}
      {pipelineStatus?.enabled && shorts.length > 0 && (
        <div className="flex-1 flex min-h-0">
          {/* Recent Shorts (60%) */}
          <div className="w-3/5 p-6 overflow-y-auto border-r border-dark-700">
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">Recent Shorts</h2>
            <div className="grid grid-cols-3 gap-4">
              {shorts.map(s => (
                <ShortCard key={s.id} short={s} onClick={() => setSelectedShort(s)} />
              ))}
            </div>
          </div>

          {/* Moment Log (40%) */}
          <div className="w-2/5 flex flex-col min-h-0">
            <div className="flex items-center justify-between px-4 py-3 border-b border-dark-700 shrink-0">
              <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider">
                Moment Log
                <span className="ml-2 text-gray-500">({moments.length})</span>
              </h2>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowScores(!showScores)}
                  className={`text-xs ${showScores ? 'text-primary-400' : 'text-gray-500'} hover:text-gray-300`}
                >
                  {showScores ? 'Hide Scores' : 'Scores'}
                </button>
                <button
                  onClick={() => setShowMoments(!showMoments)}
                  className="text-xs text-gray-500 hover:text-gray-300"
                >
                  {showMoments ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>
            {showScores && Object.keys(scoreHistory).length > 0 && (
              <div className="mb-4 space-y-2">
                {Object.entries(scoreHistory).map(([presetId, scores]) => {
                  const latest = scores[scores.length - 1];
                  const maxScore = Math.max(...scores.map(s => s.score));
                  const avgScore = scores.reduce((sum, s) => sum + s.score, 0) / scores.length;
                  return (
                    <div key={presetId} className="bg-dark-700 rounded px-3 py-2">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-gray-300">Preset {presetId}</span>
                        <span className="text-xs text-gray-500">
                          latest: <span className={`font-mono ${latest?.triggered ? 'text-green-400' : 'text-gray-400'}`}>{latest?.score?.toFixed(4)}</span>
                          {' / '}thresh: {latest?.threshold?.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex items-end gap-px h-6">
                        {scores.slice(-20).map((s, i) => (
                          <div
                            key={i}
                            className={`flex-1 rounded-t ${s.triggered ? 'bg-green-500' : s.score > (s.threshold * 0.5) ? 'bg-yellow-500/60' : 'bg-gray-600'}`}
                            style={{ height: `${Math.max(2, Math.min(100, (s.score / Math.max(s.threshold, 0.01)) * 100))}%` }}
                            title={`${s.type}=${s.score.toFixed(4)} @ ${new Date(s.time + 'Z').toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', timeZone: pipelineStatus?.timezone || 'America/New_York' })}`}
                          />
                        ))}
                      </div>
                      <div className="flex justify-between text-xs text-gray-600 mt-1">
                        <span>avg: {avgScore.toFixed(4)}</span>
                        <span>peak: {maxScore.toFixed(4)}</span>
                        <span>{scores.length} readings</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {showMoments && (
              <div className="flex-1 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-dark-800">
                    <tr className="text-gray-500 text-xs uppercase">
                      <th className="px-4 py-2 text-left">Time</th>
                      <th className="px-2 py-2 text-left">Type</th>
                      <th className="px-2 py-2 text-right">Score</th>
                      <th className="px-2 py-2 text-left">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark-700">
                    {moments.map(m => (
                      <tr key={m.id} className={`${m.status === 'failed' ? 'bg-red-900/10' : ''} ${m.status === 'skipped' ? 'text-gray-500' : ''}`}>
                        <td className="px-4 py-2 text-gray-300">{formatTime(m.timestamp)}</td>
                        <td className="px-2 py-2"><TriggerBadge type={m.trigger_type} /></td>
                        <td className={`px-2 py-2 text-right font-mono ${m.score >= 0.8 ? 'text-green-400' : m.score >= 0.5 ? 'text-yellow-400' : 'text-gray-500'}`}>
                          {m.score.toFixed(2)}
                        </td>
                        <td className="px-2 py-2"><StatusBadge status={m.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Short detail slide-over */}
      <ShortDetailSlideOver
        short={selectedShort}
        isOpen={!!selectedShort}
        onClose={() => setSelectedShort(null)}
        onDelete={handleDeleteShort}
      />

      {/* Settings slide-over */}
      <SettingsSlideOver
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        config={config}
        cameras={cameras}
        onSave={handleSaveConfig}
      />
    </div>
  );
};

export default ShortForge;
