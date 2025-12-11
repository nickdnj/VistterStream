import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  SparklesIcon,
  DocumentDuplicateIcon,
  QueueListIcon,
  Cog6ToothIcon,
  PlusIcon,
  PlayIcon,
  TrashIcon,
  PencilIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  VideoCameraIcon,
  EyeIcon,
  ArrowDownTrayIcon,
  ClipboardDocumentIcon,
} from '@heroicons/react/24/outline';

// Types
interface Camera {
  id: number;
  name: string;
  type: string;
  presets: Preset[];
}

interface Preset {
  id: number;
  name: string;
  camera_id: number;
}

interface ReelTemplate {
  id: number;
  name: string;
  description: string | null;
  camera_id: number | null;
  preset_id: number | null;
  clip_duration: number;
  pan_direction: string;
  publish_mode: string;
  is_active: boolean;
  created_at: string;
}

interface ReelPost {
  id: number;
  template_id: number | null;
  status: string;
  error_message: string | null;
  camera_id: number;
  preset_id: number | null;
  output_path: string | null;
  thumbnail_path: string | null;
  generated_headlines: { text: string; start_time: number; duration: number }[];
  download_count: number;
  created_at: string;
  camera_name: string | null;
  preset_name: string | null;
  template_name: string | null;
}

interface ReelPublishTarget {
  id: number;
  name: string;
  platform: string;
  is_active: boolean;
  created_at: string;
}

interface QueueItem {
  id: number;
  post_id: number;
  camera_id: number;
  preset_id: number | null;
  status: string;
  camera_name: string | null;
  preset_name: string | null;
  created_at: string;
}

type TabType = 'posts' | 'templates' | 'targets';

const ReelForge: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('posts');
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [templates, setTemplates] = useState<ReelTemplate[]>([]);
  const [posts, setPosts] = useState<ReelPost[]>([]);
  const [targets, setTargets] = useState<ReelPublishTarget[]>([]);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Post Modal State
  const [showNewPostModal, setShowNewPostModal] = useState(false);
  const [selectedCameraId, setSelectedCameraId] = useState<number | null>(null);
  const [selectedPresetId, setSelectedPresetId] = useState<number | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [queueingPost, setQueueingPost] = useState(false);

  // Load data on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [camerasRes, templatesRes, postsRes, targetsRes, queueRes] = await Promise.all([
        api.get('/reelforge/cameras'),
        api.get('/reelforge/templates'),
        api.get('/reelforge/posts'),
        api.get('/reelforge/targets'),
        api.get('/reelforge/queue'),
      ]);

      setCameras(camerasRes.data || []);
      setTemplates(templatesRes.data || []);
      setPosts(postsRes.data || []);
      setTargets(targetsRes.data || []);
      setQueue(queueRes.data || []);
    } catch (err) {
      console.error('Failed to load ReelForge data:', err);
      setError('Failed to load data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleQueueCapture = async () => {
    if (!selectedCameraId) return;

    setQueueingPost(true);
    try {
      await api.post('/reelforge/posts/queue', {
        camera_id: selectedCameraId,
        preset_id: selectedPresetId || undefined,
        template_id: selectedTemplateId || undefined,
      });

      setShowNewPostModal(false);
      setSelectedCameraId(null);
      setSelectedPresetId(null);
      setSelectedTemplateId(null);
      loadData();
    } catch (err) {
      console.error('Failed to queue capture:', err);
      setError('Failed to queue capture. Please try again.');
    } finally {
      setQueueingPost(false);
    }
  };

  const handleDeletePost = async (postId: number) => {
    if (!window.confirm('Are you sure you want to delete this post?')) return;

    try {
      await api.delete(`/reelforge/posts/${postId}`);
      loadData();
    } catch (err) {
      console.error('Failed to delete post:', err);
    }
  };

  const handleCancelQueue = async (queueId: number) => {
    try {
      await api.delete(`/reelforge/queue/${queueId}`);
      loadData();
    } catch (err) {
      console.error('Failed to cancel queue item:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const badges: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
      queued: { color: 'bg-yellow-500/20 text-yellow-400', icon: <ClockIcon className="w-4 h-4" />, label: 'Queued' },
      capturing: { color: 'bg-blue-500/20 text-blue-400', icon: <VideoCameraIcon className="w-4 h-4" />, label: 'Capturing' },
      processing: { color: 'bg-purple-500/20 text-purple-400', icon: <ArrowPathIcon className="w-4 h-4 animate-spin" />, label: 'Processing' },
      ready: { color: 'bg-green-500/20 text-green-400', icon: <CheckCircleIcon className="w-4 h-4" />, label: 'Ready to Download' },
      failed: { color: 'bg-red-500/20 text-red-400', icon: <ExclamationCircleIcon className="w-4 h-4" />, label: 'Failed' },
    };

    const badge = badges[status] || badges.queued;
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
        {badge.icon}
        {badge.label}
      </span>
    );
  };

  const handleDownload = (postId: number) => {
    // Open download URL in new tab - browser will handle the download
    window.open(`/api/reelforge/posts/${postId}/download`, '_blank');
  };

  const handleCopyMetadata = async (postId: number) => {
    try {
      const response = await api.get(`/reelforge/posts/${postId}/metadata`);
      const { title, description, hashtags } = response.data;
      const text = `${title}\n\n${description}\n\n${hashtags}`;
      await navigator.clipboard.writeText(text);
      // Could add a toast notification here
    } catch (err) {
      console.error('Failed to copy metadata:', err);
    }
  };

  const selectedCamera = cameras.find(c => c.id === selectedCameraId);

  const tabs = [
    { id: 'posts' as TabType, name: 'Posts', icon: QueueListIcon, count: posts.length },
    { id: 'templates' as TabType, name: 'Templates', icon: DocumentDuplicateIcon, count: templates.length },
    { id: 'targets' as TabType, name: 'Platform Presets', icon: Cog6ToothIcon, count: targets.length },
  ];

  return (
    <div className="h-full overflow-auto bg-dark-900 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-600/20 rounded-lg">
            <SparklesIcon className="w-8 h-8 text-primary-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">ReelForge</h1>
            <p className="text-gray-400 text-sm">Automated social media content generation</p>
          </div>
        </div>
        <button
          onClick={() => setShowNewPostModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          New Post
        </button>
      </div>

      {/* Capture Queue Alert */}
      {queue.length > 0 && (
        <div className="mb-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <div className="flex items-center gap-2 text-yellow-400 mb-2">
            <ClockIcon className="w-5 h-5" />
            <span className="font-medium">{queue.length} capture(s) waiting in queue</span>
          </div>
          <div className="space-y-2">
            {queue.map(item => (
              <div key={item.id} className="flex items-center justify-between text-sm">
                <span className="text-gray-300">
                  {item.camera_name} {item.preset_name && `> ${item.preset_name}`}
                </span>
                <button
                  onClick={() => handleCancelQueue(item.id)}
                  className="text-red-400 hover:text-red-300"
                >
                  Cancel
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-dark-700 mb-6">
        <nav className="flex gap-4">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-500 text-white'
                  : 'border-transparent text-gray-400 hover:text-white'
              }`}
            >
              <tab.icon className="w-5 h-5" />
              {tab.name}
              <span className="px-2 py-0.5 bg-dark-700 rounded-full text-xs">{tab.count}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <ArrowPathIcon className="w-8 h-8 text-gray-400 animate-spin" />
        </div>
      )}

      {/* Posts Tab */}
      {!loading && activeTab === 'posts' && (
        <div className="space-y-4">
          {posts.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <QueueListIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No posts yet</p>
              <p className="text-sm">Create your first post to get started</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {posts.map(post => (
                <div
                  key={post.id}
                  className="bg-dark-800 rounded-lg p-4 border border-dark-700"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        {getStatusBadge(post.status)}
                        <span className="text-gray-400 text-sm">
                          {new Date(post.created_at).toLocaleString()}
                        </span>
                      </div>
                      <div className="text-white font-medium">
                        {post.camera_name} {post.preset_name && `> ${post.preset_name}`}
                      </div>
                      {post.template_name && (
                        <div className="text-gray-400 text-sm">
                          Template: {post.template_name}
                        </div>
                      )}
                      {post.error_message && (
                        <div className="text-red-400 text-sm mt-2">
                          Error: {post.error_message}
                        </div>
                      )}
                      {post.generated_headlines && post.generated_headlines.length > 0 && (
                        <div className="mt-3 space-y-1">
                          {post.generated_headlines.slice(0, 2).map((h, i) => (
                            <div key={i} className="text-gray-400 text-sm truncate">
                              "{h.text}"
                            </div>
                          ))}
                          {post.generated_headlines.length > 2 && (
                            <div className="text-gray-500 text-xs">
                              +{post.generated_headlines.length - 2} more...
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {post.status === 'ready' && (
                        <>
                          <button
                            onClick={() => handleDownload(post.id)}
                            className="p-2 text-green-400 hover:bg-green-400/10 rounded-lg transition-colors"
                            title="Download Video"
                          >
                            <ArrowDownTrayIcon className="w-5 h-5" />
                          </button>
                          <button
                            onClick={() => handleCopyMetadata(post.id)}
                            className="p-2 text-primary-400 hover:bg-primary-400/10 rounded-lg transition-colors"
                            title="Copy Caption & Hashtags"
                          >
                            <ClipboardDocumentIcon className="w-5 h-5" />
                          </button>
                        </>
                      )}
                      <button
                        onClick={() => handleDeletePost(post.id)}
                        className="p-2 text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                        title="Delete"
                      >
                        <TrashIcon className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Templates Tab */}
      {!loading && activeTab === 'templates' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button className="flex items-center gap-2 px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-lg transition-colors">
              <PlusIcon className="w-5 h-5" />
              New Template
            </button>
          </div>
          {templates.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <DocumentDuplicateIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No templates yet</p>
              <p className="text-sm">Templates help you configure reusable post settings</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {templates.map(template => (
                <div
                  key={template.id}
                  className="bg-dark-800 rounded-lg p-4 border border-dark-700"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-white font-medium">{template.name}</div>
                      {template.description && (
                        <div className="text-gray-400 text-sm">{template.description}</div>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-gray-500 text-sm">
                        <span>{template.clip_duration}s clip</span>
                        <span>{template.pan_direction.replace('_', ' ')}</span>
                        <span>{template.publish_mode} publish</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button className="p-2 text-gray-400 hover:bg-dark-600 rounded-lg transition-colors">
                        <PencilIcon className="w-5 h-5" />
                      </button>
                      <button className="p-2 text-red-400 hover:bg-red-400/10 rounded-lg transition-colors">
                        <TrashIcon className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Targets Tab (Platform Presets) */}
      {!loading && activeTab === 'targets' && (
        <div className="space-y-4">
          {/* Info Banner */}
          <div className="p-4 bg-primary-500/10 border border-primary-500/30 rounded-lg">
            <p className="text-primary-300 text-sm">
              Platform presets store default hashtags and description templates for each platform.
              Download your video and copy the metadata when manually posting.
            </p>
          </div>
          
          <div className="flex justify-end">
            <button className="flex items-center gap-2 px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-lg transition-colors">
              <PlusIcon className="w-5 h-5" />
              Add Preset
            </button>
          </div>
          {targets.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Cog6ToothIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No platform presets configured</p>
              <p className="text-sm">Add presets with default hashtags for YouTube Shorts, Instagram, or TikTok</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {targets.map(target => (
                <div
                  key={target.id}
                  className="bg-dark-800 rounded-lg p-4 border border-dark-700"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-white font-medium">{target.name}</div>
                      <div className="text-gray-400 text-sm capitalize">{target.platform.replace(/_/g, ' ')}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2 h-2 rounded-full ${target.is_active ? 'bg-green-500' : 'bg-gray-500'}`}
                      />
                      <button className="p-2 text-gray-400 hover:bg-dark-600 rounded-lg transition-colors">
                        <PencilIcon className="w-5 h-5" />
                      </button>
                      <button className="p-2 text-red-400 hover:bg-red-400/10 rounded-lg transition-colors">
                        <TrashIcon className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* New Post Modal */}
      {showNewPostModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-dark-800 rounded-lg p-6 w-full max-w-md border border-dark-700">
            <h2 className="text-xl font-bold text-white mb-4">Create New Post</h2>

            {/* Camera Selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Select Camera
              </label>
              <select
                value={selectedCameraId || ''}
                onChange={e => {
                  setSelectedCameraId(e.target.value ? Number(e.target.value) : null);
                  setSelectedPresetId(null);
                }}
                className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white"
              >
                <option value="">Choose a camera...</option>
                {cameras.map(camera => (
                  <option key={camera.id} value={camera.id}>
                    {camera.name} ({camera.type})
                  </option>
                ))}
              </select>
            </div>

            {/* Preset Selection (for PTZ cameras) */}
            {selectedCamera && selectedCamera.presets.length > 0 && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Select Preset (optional)
                </label>
                <select
                  value={selectedPresetId || ''}
                  onChange={e => setSelectedPresetId(e.target.value ? Number(e.target.value) : null)}
                  className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white"
                >
                  <option value="">Any preset...</option>
                  {selectedCamera.presets.map(preset => (
                    <option key={preset.id} value={preset.id}>
                      {preset.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Template Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Template (optional)
              </label>
              <select
                value={selectedTemplateId || ''}
                onChange={e => setSelectedTemplateId(e.target.value ? Number(e.target.value) : null)}
                className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white"
              >
                <option value="">No template (use defaults)</option>
                {templates.map(template => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Info */}
            <div className="mb-6 p-3 bg-primary-500/10 border border-primary-500/30 rounded-lg text-sm text-primary-300">
              <p>The capture will be queued and executed when the timeline naturally switches to this camera/preset.</p>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowNewPostModal(false);
                  setSelectedCameraId(null);
                  setSelectedPresetId(null);
                  setSelectedTemplateId(null);
                }}
                className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleQueueCapture}
                disabled={!selectedCameraId || queueingPost}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-600/50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
              >
                {queueingPost ? (
                  <ArrowPathIcon className="w-5 h-5 animate-spin" />
                ) : (
                  <PlayIcon className="w-5 h-5" />
                )}
                Queue Capture
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReelForge;
