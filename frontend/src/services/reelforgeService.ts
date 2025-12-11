/**
 * ReelForge API Service
 * Client for the ReelForge automated social media content generation system
 * 
 * Note: This is the MVP version focused on content generation only.
 * Posts are downloaded manually and uploaded by the user to social platforms.
 */

import { api } from './api';

// Types
export interface Camera {
  id: number;
  name: string;
  type: string;
  presets: Preset[];
}

export interface Preset {
  id: number;
  name: string;
  camera_id: number;
  pan: number;
  tilt: number;
  zoom: number;
}

export interface AIConfig {
  tone: string;
  voice: string;
  instructions: string;
  prompt_1: string;
  prompt_2: string;
  prompt_3: string;
  prompt_4: string;
  prompt_5: string;
}

export interface ReelTemplate {
  id: number;
  name: string;
  description: string | null;
  camera_id: number | null;
  preset_id: number | null;
  clip_duration: number;
  pan_direction: 'left_to_right' | 'right_to_left' | 'center';
  pan_speed: number;
  ai_config: AIConfig;
  overlay_style: string;
  font_family: string;
  font_size: number;
  text_color: string;
  text_shadow: boolean;
  text_background: string;
  text_position_y: number;
  publish_mode: 'manual' | 'auto' | 'scheduled';
  schedule_times: string[];
  default_title_template: string;
  default_description_template: string | null;
  default_hashtags: string;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ReelTemplateCreate {
  name: string;
  description?: string;
  camera_id?: number;
  preset_id?: number;
  clip_duration?: number;
  pan_direction?: 'left_to_right' | 'right_to_left' | 'center';
  pan_speed?: number;
  ai_config?: Partial<AIConfig>;
  overlay_style?: string;
  font_family?: string;
  font_size?: number;
  text_color?: string;
  text_shadow?: boolean;
  text_background?: string;
  text_position_y?: number;
  publish_mode?: 'manual' | 'auto' | 'scheduled';
  schedule_times?: string[];
  default_title_template?: string;
  default_description_template?: string;
  default_hashtags?: string;
}

export interface ReelHeadline {
  text: string;
  start_time: number;
  duration: number;
}

export interface ReelPost {
  id: number;
  template_id: number | null;
  status: 'queued' | 'capturing' | 'processing' | 'ready' | 'failed';
  error_message: string | null;
  camera_id: number;
  preset_id: number | null;
  source_clip_path: string | null;
  portrait_clip_path: string | null;
  output_path: string | null;
  thumbnail_path: string | null;
  generated_headlines: ReelHeadline[];
  download_count: number;
  created_at: string;
  updated_at: string | null;
  capture_started_at: string | null;
  capture_completed_at: string | null;
  processing_started_at: string | null;
  processing_completed_at: string | null;
  camera_name?: string | null;
  preset_name?: string | null;
  template_name?: string | null;
}

export interface ReelPostQueue {
  camera_id: number;
  preset_id?: number;
  template_id?: number;
}

export interface ReelPostMetadata {
  title: string;
  description: string;
  hashtags: string;
  headlines: ReelHeadline[];
}

export interface ReelPublishTarget {
  id: number;
  name: string;
  platform: 'youtube_shorts' | 'instagram_reels' | 'tiktok' | 'facebook_reels';
  default_title_template: string;
  default_description_template: string | null;
  default_hashtags: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ReelPublishTargetCreate {
  name: string;
  platform: 'youtube_shorts' | 'instagram_reels' | 'tiktok' | 'facebook_reels';
  default_title_template?: string;
  default_description_template?: string;
  default_hashtags?: string;
}

export interface ReelExport {
  id: number;
  post_id: number;
  target_id: number | null;
  status: 'exported' | 'posted';
  platform_url: string | null;
  title: string | null;
  description: string | null;
  hashtags: string | null;
  exported_at: string;
  posted_at: string | null;
  created_at: string;
}

export interface ReelExportUpdate {
  status?: 'exported' | 'posted';
  platform_url?: string;
}

export interface CaptureQueueItem {
  id: number;
  post_id: number;
  camera_id: number;
  preset_id: number | null;
  status: string;
  priority: number;
  created_at: string;
  expires_at: string | null;
  camera_name?: string | null;
  preset_name?: string | null;
}

// API Service
export const reelforgeService = {
  // Cameras
  async getCamerasWithPresets(): Promise<Camera[]> {
    const response = await api.get('/reelforge/cameras');
    return response.data;
  },

  // Templates
  async getTemplates(activeOnly = false): Promise<ReelTemplate[]> {
    const response = await api.get('/reelforge/templates', {
      params: { active_only: activeOnly },
    });
    return response.data;
  },

  async getTemplate(id: number): Promise<ReelTemplate> {
    const response = await api.get(`/reelforge/templates/${id}`);
    return response.data;
  },

  async createTemplate(data: ReelTemplateCreate): Promise<ReelTemplate> {
    const response = await api.post('/reelforge/templates', data);
    return response.data;
  },

  async updateTemplate(id: number, data: Partial<ReelTemplateCreate>): Promise<ReelTemplate> {
    const response = await api.put(`/reelforge/templates/${id}`, data);
    return response.data;
  },

  async deleteTemplate(id: number): Promise<void> {
    await api.delete(`/reelforge/templates/${id}`);
  },

  // Posts
  async getPosts(status?: string, limit = 50): Promise<ReelPost[]> {
    const response = await api.get('/reelforge/posts', {
      params: { status, limit },
    });
    return response.data;
  },

  async getPost(id: number): Promise<ReelPost> {
    const response = await api.get(`/reelforge/posts/${id}`);
    return response.data;
  },

  async queueCapture(data: ReelPostQueue): Promise<ReelPost> {
    const response = await api.post('/reelforge/posts/queue', data);
    return response.data;
  },

  async deletePost(id: number): Promise<void> {
    await api.delete(`/reelforge/posts/${id}`);
  },

  // Download & Export
  getDownloadUrl(postId: number, targetId?: number): string {
    const base = `/api/reelforge/posts/${postId}/download`;
    return targetId ? `${base}?target_id=${targetId}` : base;
  },

  async getPostMetadata(postId: number, targetId?: number): Promise<ReelPostMetadata> {
    const response = await api.get(`/reelforge/posts/${postId}/metadata`, {
      params: targetId ? { target_id: targetId } : undefined,
    });
    return response.data;
  },

  async getPostExports(postId: number): Promise<ReelExport[]> {
    const response = await api.get(`/reelforge/posts/${postId}/exports`);
    return response.data;
  },

  async updateExport(exportId: number, data: ReelExportUpdate): Promise<ReelExport> {
    const response = await api.put(`/reelforge/exports/${exportId}`, data);
    return response.data;
  },

  // Platform Presets (Targets)
  async getTargets(activeOnly = false): Promise<ReelPublishTarget[]> {
    const response = await api.get('/reelforge/targets', {
      params: { active_only: activeOnly },
    });
    return response.data;
  },

  async getTarget(id: number): Promise<ReelPublishTarget> {
    const response = await api.get(`/reelforge/targets/${id}`);
    return response.data;
  },

  async createTarget(data: ReelPublishTargetCreate): Promise<ReelPublishTarget> {
    const response = await api.post('/reelforge/targets', data);
    return response.data;
  },

  async updateTarget(id: number, data: Partial<ReelPublishTargetCreate>): Promise<ReelPublishTarget> {
    const response = await api.put(`/reelforge/targets/${id}`, data);
    return response.data;
  },

  async deleteTarget(id: number): Promise<void> {
    await api.delete(`/reelforge/targets/${id}`);
  },

  // Capture Queue
  async getCaptureQueue(): Promise<CaptureQueueItem[]> {
    const response = await api.get('/reelforge/queue');
    return response.data;
  },

  async cancelQueuedCapture(queueId: number): Promise<void> {
    await api.delete(`/reelforge/queue/${queueId}`);
  },
};

export default reelforgeService;
