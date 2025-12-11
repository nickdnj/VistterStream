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
  trigger_mode: string;
  scheduled_at: string | null;
  status: string;
  camera_name: string | null;
  preset_name: string | null;
  created_at: string;
}

interface ReelForgeSettings {
  id: number;
  openai_model: string;
  system_prompt: string;
  temperature: number;
  max_tokens: number;
  default_template_id: number | null;
  has_api_key: boolean;
  created_at: string;
  updated_at: string | null;
}

type TabType = 'posts' | 'templates' | 'targets' | 'settings';

const ReelForge: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('posts');
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [templates, setTemplates] = useState<ReelTemplate[]>([]);
  const [posts, setPosts] = useState<ReelPost[]>([]);
  const [targets, setTargets] = useState<ReelPublishTarget[]>([]);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [settings, setSettings] = useState<ReelForgeSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Settings form state
  const [settingsApiKey, setSettingsApiKey] = useState('');
  const [settingsModel, setSettingsModel] = useState('gpt-4o-mini');
  const [settingsSystemPrompt, setSettingsSystemPrompt] = useState('');
  const [settingsTemperature, setSettingsTemperature] = useState(0.8);
  const [savingSettings, setSavingSettings] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionTestResult, setConnectionTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // New Post Modal State
  const [showNewPostModal, setShowNewPostModal] = useState(false);
  const [selectedCameraId, setSelectedCameraId] = useState<number | null>(null);
  const [selectedPresetId, setSelectedPresetId] = useState<number | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [triggerMode, setTriggerMode] = useState<'next_view' | 'scheduled'>('next_view');
  const [scheduledAt, setScheduledAt] = useState<string>('');
  const [queueingPost, setQueueingPost] = useState(false);

  // Template Modal State
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ReelTemplate | null>(null);
  const [templateName, setTemplateName] = useState('');
  const [templateDescription, setTemplateDescription] = useState('');
  const [templateCameraId, setTemplateCameraId] = useState<number | null>(null);
  const [templatePresetId, setTemplatePresetId] = useState<number | null>(null);
  const [templateClipDuration, setTemplateClipDuration] = useState(30);
  const [templatePanDirection, setTemplatePanDirection] = useState('left_to_right');
  const [templateTone, setTemplateTone] = useState('casual');
  const [templateVoice, setTemplateVoice] = useState('friendly guide');
  const [templateInstructions, setTemplateInstructions] = useState('');
  const [templatePrompt1, setTemplatePrompt1] = useState('Morning greeting');
  const [templatePrompt2, setTemplatePrompt2] = useState('Current conditions update');
  const [templatePrompt3, setTemplatePrompt3] = useState('Highlight of the day');
  const [templatePrompt4, setTemplatePrompt4] = useState('Call to action');
  const [templatePrompt5, setTemplatePrompt5] = useState('Sign off');
  const [savingTemplate, setSavingTemplate] = useState(false);

  // Load data on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [camerasRes, templatesRes, postsRes, targetsRes, queueRes, settingsRes] = await Promise.all([
        api.get('/reelforge/cameras'),
        api.get('/reelforge/templates'),
        api.get('/reelforge/posts'),
        api.get('/reelforge/targets'),
        api.get('/reelforge/queue'),
        api.get('/reelforge/settings'),
      ]);

      setCameras(camerasRes.data || []);
      setTemplates(templatesRes.data || []);
      setPosts(postsRes.data || []);
      setTargets(targetsRes.data || []);
      setQueue(queueRes.data || []);
      
      const loadedSettings = settingsRes.data;
      setSettings(loadedSettings);
      setSettingsModel(loadedSettings?.openai_model || 'gpt-4o-mini');
      setSettingsSystemPrompt(loadedSettings?.system_prompt || '');
      setSettingsTemperature(loadedSettings?.temperature || 0.8);
    } catch (err) {
      console.error('Failed to load ReelForge data:', err);
      setError('Failed to load data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleQueueCapture = async () => {
    if (!selectedCameraId) return;
    
    // Validate scheduled time for scheduled mode
    if (triggerMode === 'scheduled' && !scheduledAt) {
      setError('Please select a scheduled time');
      return;
    }

    setQueueingPost(true);
    try {
      const queueData: Record<string, unknown> = {
        camera_id: selectedCameraId,
        preset_id: selectedPresetId || undefined,
        template_id: selectedTemplateId || undefined,
        trigger_mode: triggerMode,
      };
      
      if (triggerMode === 'scheduled' && scheduledAt) {
        // Convert local datetime to ISO string
        queueData.scheduled_at = new Date(scheduledAt).toISOString();
      }
      
      await api.post('/reelforge/posts/queue', queueData);

      setShowNewPostModal(false);
      setSelectedCameraId(null);
      setSelectedPresetId(null);
      setSelectedTemplateId(null);
      setTriggerMode('next_view');
      setScheduledAt('');
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

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    try {
      const updateData: Record<string, unknown> = {
        openai_model: settingsModel,
        system_prompt: settingsSystemPrompt,
        temperature: settingsTemperature,
      };
      
      // Only include API key if it was changed (not empty)
      if (settingsApiKey) {
        updateData.openai_api_key = settingsApiKey;
      }
      
      const response = await api.post('/reelforge/settings', updateData);
      setSettings(response.data);
      setSettingsApiKey(''); // Clear the API key field after save
      setConnectionTestResult(null);
    } catch (err) {
      console.error('Failed to save settings:', err);
      setError('Failed to save settings. Please try again.');
    } finally {
      setSavingSettings(false);
    }
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setConnectionTestResult(null);
    try {
      const response = await api.post('/reelforge/settings/test');
      setConnectionTestResult(response.data);
    } catch (err) {
      setConnectionTestResult({ success: false, message: 'Failed to test connection' });
    } finally {
      setTestingConnection(false);
    }
  };

  const openNewTemplateModal = () => {
    setEditingTemplate(null);
    setTemplateName('');
    setTemplateDescription('');
    setTemplateCameraId(null);
    setTemplatePresetId(null);
    setTemplateClipDuration(30);
    setTemplatePanDirection('left_to_right');
    setTemplateTone('casual');
    setTemplateVoice('friendly guide');
    setTemplateInstructions('');
    setTemplatePrompt1('Morning greeting');
    setTemplatePrompt2('Current conditions update');
    setTemplatePrompt3('Highlight of the day');
    setTemplatePrompt4('Call to action');
    setTemplatePrompt5('Sign off');
    setShowTemplateModal(true);
  };

  const openEditTemplateModal = (template: ReelTemplate) => {
    setEditingTemplate(template);
    setTemplateName(template.name);
    setTemplateDescription(template.description || '');
    setTemplateCameraId(template.camera_id);
    setTemplatePresetId(template.preset_id);
    setTemplateClipDuration(template.clip_duration);
    setTemplatePanDirection(template.pan_direction);
    // Load AI config (need to fetch full template)
    api.get(`/reelforge/templates/${template.id}`).then(res => {
      const fullTemplate = res.data;
      const aiConfig = fullTemplate.ai_config || {};
      setTemplateTone(aiConfig.tone || 'casual');
      setTemplateVoice(aiConfig.voice || 'friendly guide');
      setTemplateInstructions(aiConfig.instructions || '');
      setTemplatePrompt1(aiConfig.prompt_1 || 'Morning greeting');
      setTemplatePrompt2(aiConfig.prompt_2 || 'Current conditions update');
      setTemplatePrompt3(aiConfig.prompt_3 || 'Highlight of the day');
      setTemplatePrompt4(aiConfig.prompt_4 || 'Call to action');
      setTemplatePrompt5(aiConfig.prompt_5 || 'Sign off');
    });
    setShowTemplateModal(true);
  };

  const handleSaveTemplate = async () => {
    if (!templateName.trim()) return;
    
    setSavingTemplate(true);
    try {
      const templateData = {
        name: templateName,
        description: templateDescription || null,
        camera_id: templateCameraId,
        preset_id: templatePresetId,
        clip_duration: templateClipDuration,
        pan_direction: templatePanDirection,
        ai_config: {
          tone: templateTone,
          voice: templateVoice,
          instructions: templateInstructions,
          prompt_1: templatePrompt1,
          prompt_2: templatePrompt2,
          prompt_3: templatePrompt3,
          prompt_4: templatePrompt4,
          prompt_5: templatePrompt5,
        },
      };

      if (editingTemplate) {
        await api.put(`/reelforge/templates/${editingTemplate.id}`, templateData);
      } else {
        await api.post('/reelforge/templates', templateData);
      }

      setShowTemplateModal(false);
      loadData();
    } catch (err) {
      console.error('Failed to save template:', err);
      setError('Failed to save template. Please try again.');
    } finally {
      setSavingTemplate(false);
    }
  };

  const handleDeleteTemplate = async (templateId: number) => {
    if (!window.confirm('Are you sure you want to delete this template?')) return;

    try {
      await api.delete(`/reelforge/templates/${templateId}`);
      loadData();
    } catch (err) {
      console.error('Failed to delete template:', err);
    }
  };

  // Helper to format UTC dates to local time
  const formatDate = (dateStr: string) => {
    // Append 'Z' if not present to treat as UTC
    const utcDate = dateStr.endsWith('Z') ? dateStr : dateStr + 'Z';
    return new Date(utcDate).toLocaleString();
  };

  const selectedCamera = cameras.find(c => c.id === selectedCameraId);

  const tabs = [
    { id: 'posts' as TabType, name: 'Posts', icon: QueueListIcon, count: posts.length },
    { id: 'templates' as TabType, name: 'Templates', icon: DocumentDuplicateIcon, count: templates.length },
    { id: 'targets' as TabType, name: 'Platform Presets', icon: Cog6ToothIcon, count: targets.length },
    { id: 'settings' as TabType, name: 'Settings', icon: Cog6ToothIcon, count: undefined },
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
              {tab.count !== undefined && (
                <span className="px-2 py-0.5 bg-dark-700 rounded-full text-xs">{tab.count}</span>
              )}
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
                          {formatDate(post.created_at)}
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
            <button
              onClick={openNewTemplateModal}
              className="flex items-center gap-2 px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-lg transition-colors"
            >
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
                      <button
                        onClick={() => openEditTemplateModal(template)}
                        className="p-2 text-gray-400 hover:bg-dark-600 rounded-lg transition-colors"
                      >
                        <PencilIcon className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleDeleteTemplate(template.id)}
                        className="p-2 text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
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

      {/* Settings Tab */}
      {!loading && activeTab === 'settings' && (
        <div className="space-y-6 max-w-2xl">
          {/* API Configuration */}
          <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
            <h3 className="text-lg font-medium text-white mb-4">OpenAI Configuration</h3>
            
            {/* API Key Status */}
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-medium text-gray-400">API Key Status:</span>
                {settings?.has_api_key ? (
                  <span className="flex items-center gap-1 text-green-400 text-sm">
                    <CheckCircleIcon className="w-4 h-4" /> Configured
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-yellow-400 text-sm">
                    <ExclamationCircleIcon className="w-4 h-4" /> Not configured
                  </span>
                )}
              </div>
            </div>
            
            {/* API Key Input */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                OpenAI API Key {settings?.has_api_key && '(leave empty to keep current)'}
              </label>
              <input
                type="password"
                value={settingsApiKey}
                onChange={e => setSettingsApiKey(e.target.value)}
                placeholder={settings?.has_api_key ? '••••••••••••••••' : 'sk-...'}
                className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-gray-500"
              />
            </div>
            
            {/* Model Selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                AI Model
              </label>
              <select
                value={settingsModel}
                onChange={e => setSettingsModel(e.target.value)}
                className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white"
              >
                <option value="gpt-4o-mini">GPT-4o Mini (Fast & Cheap)</option>
                <option value="gpt-4o">GPT-4o (Best Quality)</option>
                <option value="gpt-4-turbo">GPT-4 Turbo</option>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Fastest)</option>
              </select>
            </div>
            
            {/* Temperature */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Creativity (Temperature): {settingsTemperature.toFixed(1)}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={settingsTemperature}
                onChange={e => setSettingsTemperature(parseFloat(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>Focused</span>
                <span>Creative</span>
              </div>
            </div>
            
            {/* Test Connection Button */}
            <div className="flex items-center gap-4">
              <button
                onClick={handleTestConnection}
                disabled={testingConnection || !settings?.has_api_key}
                className="px-4 py-2 bg-dark-600 hover:bg-dark-500 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                {testingConnection ? 'Testing...' : 'Test Connection'}
              </button>
              {connectionTestResult && (
                <span className={connectionTestResult.success ? 'text-green-400' : 'text-red-400'}>
                  {connectionTestResult.message}
                </span>
              )}
            </div>
          </div>
          
          {/* System Prompt */}
          <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
            <h3 className="text-lg font-medium text-white mb-4">System Prompt</h3>
            <p className="text-gray-400 text-sm mb-4">
              This is the instruction given to the AI before generating headlines. 
              Customize it to change the AI's behavior and output style.
            </p>
            <textarea
              value={settingsSystemPrompt}
              onChange={e => setSettingsSystemPrompt(e.target.value)}
              rows={10}
              className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white font-mono text-sm"
              placeholder="Enter system prompt..."
            />
          </div>
          
          {/* Save Button */}
          <div className="flex justify-end">
            <button
              onClick={handleSaveSettings}
              disabled={savingSettings}
              className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {savingSettings ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
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

            {/* Trigger Mode */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                When to Capture
              </label>
              <div className="space-y-2">
                <label className="flex items-center gap-3 p-3 bg-dark-700 rounded-lg cursor-pointer hover:bg-dark-600 transition-colors">
                  <input
                    type="radio"
                    name="triggerMode"
                    value="next_view"
                    checked={triggerMode === 'next_view'}
                    onChange={() => setTriggerMode('next_view')}
                    className="w-4 h-4 text-primary-600"
                  />
                  <div>
                    <div className="text-white text-sm font-medium">Next Timeline View</div>
                    <div className="text-gray-400 text-xs">Capture when timeline switches to this camera/preset</div>
                  </div>
                </label>
                <label className="flex items-center gap-3 p-3 bg-dark-700 rounded-lg cursor-pointer hover:bg-dark-600 transition-colors">
                  <input
                    type="radio"
                    name="triggerMode"
                    value="scheduled"
                    checked={triggerMode === 'scheduled'}
                    onChange={() => setTriggerMode('scheduled')}
                    className="w-4 h-4 text-primary-600"
                  />
                  <div>
                    <div className="text-white text-sm font-medium">Schedule for Later</div>
                    <div className="text-gray-400 text-xs">Capture at a specific date and time</div>
                  </div>
                </label>
              </div>
            </div>

            {/* Scheduled Time */}
            {triggerMode === 'scheduled' && (
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Scheduled Time
                </label>
                <input
                  type="datetime-local"
                  value={scheduledAt}
                  onChange={e => setScheduledAt(e.target.value)}
                  className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white"
                />
              </div>
            )}

            {/* Info */}
            <div className="mb-6 p-3 bg-primary-500/10 border border-primary-500/30 rounded-lg text-sm text-primary-300">
              {triggerMode === 'next_view' ? (
                <p>The capture will be queued and executed when the timeline naturally switches to this camera/preset.</p>
              ) : (
                <p>The capture will be executed at the scheduled time, regardless of the current timeline position.</p>
              )}
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

      {/* Template Modal */}
      {showTemplateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-auto py-8">
          <div className="bg-dark-800 rounded-lg p-6 w-full max-w-2xl border border-dark-700 mx-4 my-auto">
            <h2 className="text-xl font-bold text-white mb-4">
              {editingTemplate ? 'Edit Template' : 'New Template'}
            </h2>

            <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Template Name *
                  </label>
                  <input
                    type="text"
                    value={templateName}
                    onChange={e => setTemplateName(e.target.value)}
                    placeholder="e.g., Morning Update"
                    className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Clip Duration (seconds)
                  </label>
                  <input
                    type="number"
                    value={templateClipDuration}
                    onChange={e => setTemplateClipDuration(parseInt(e.target.value) || 30)}
                    min={10}
                    max={60}
                    className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Description
                </label>
                <input
                  type="text"
                  value={templateDescription}
                  onChange={e => setTemplateDescription(e.target.value)}
                  placeholder="Optional description..."
                  className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white"
                />
              </div>

              {/* Video Settings */}
              <div className="border-t border-dark-600 pt-4">
                <h3 className="text-sm font-medium text-white mb-3">Video Settings</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-2">
                      Default Camera
                    </label>
                    <select
                      value={templateCameraId || ''}
                      onChange={e => {
                        setTemplateCameraId(e.target.value ? Number(e.target.value) : null);
                        setTemplatePresetId(null);
                      }}
                      className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white"
                    >
                      <option value="">Select camera (optional)</option>
                      {cameras.map(camera => (
                        <option key={camera.id} value={camera.id}>
                          {camera.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-2">
                      Pan Direction
                    </label>
                    <select
                      value={templatePanDirection}
                      onChange={e => setTemplatePanDirection(e.target.value)}
                      className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white"
                    >
                      <option value="left_to_right">Left to Right</option>
                      <option value="right_to_left">Right to Left</option>
                      <option value="center">Center (No Pan)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* AI Configuration */}
              <div className="border-t border-dark-600 pt-4">
                <h3 className="text-sm font-medium text-white mb-3">AI Content Configuration</h3>
                
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-2">
                      Tone
                    </label>
                    <select
                      value={templateTone}
                      onChange={e => setTemplateTone(e.target.value)}
                      className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white"
                    >
                      <option value="casual">Casual</option>
                      <option value="professional">Professional</option>
                      <option value="excited">Excited</option>
                      <option value="informative">Informative</option>
                      <option value="friendly">Friendly</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-2">
                      Voice/Persona
                    </label>
                    <input
                      type="text"
                      value={templateVoice}
                      onChange={e => setTemplateVoice(e.target.value)}
                      placeholder="e.g., friendly surf instructor"
                      className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                </div>

                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-400 mb-2">
                    Instructions
                  </label>
                  <textarea
                    value={templateInstructions}
                    onChange={e => setTemplateInstructions(e.target.value)}
                    placeholder="General instructions for AI content generation..."
                    rows={3}
                    className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white"
                  />
                </div>

                <div className="space-y-3">
                  <p className="text-xs text-gray-500">
                    Define 5 headline prompts (6 seconds each in the video):
                  </p>
                  {[
                    { label: 'Headline 1', value: templatePrompt1, setter: setTemplatePrompt1 },
                    { label: 'Headline 2', value: templatePrompt2, setter: setTemplatePrompt2 },
                    { label: 'Headline 3', value: templatePrompt3, setter: setTemplatePrompt3 },
                    { label: 'Headline 4', value: templatePrompt4, setter: setTemplatePrompt4 },
                    { label: 'Headline 5', value: templatePrompt5, setter: setTemplatePrompt5 },
                  ].map((prompt, i) => (
                    <div key={i}>
                      <label className="block text-sm font-medium text-gray-400 mb-1">
                        {prompt.label}
                      </label>
                      <input
                        type="text"
                        value={prompt.value}
                        onChange={e => prompt.setter(e.target.value)}
                        className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm"
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-dark-600">
              <button
                onClick={() => setShowTemplateModal(false)}
                className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveTemplate}
                disabled={savingTemplate || !templateName.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                {savingTemplate ? (
                  <ArrowPathIcon className="w-5 h-5 animate-spin" />
                ) : (
                  <CheckCircleIcon className="w-5 h-5" />
                )}
                {editingTemplate ? 'Update Template' : 'Create Template'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReelForge;
