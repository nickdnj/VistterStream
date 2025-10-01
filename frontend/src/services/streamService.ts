import { api } from './api';

export interface Stream {
  id: number;
  camera_id: number;
  destination: 'youtube' | 'facebook' | 'twitch';
  stream_key: string;
  rtmp_url: string;
  status: 'stopped' | 'starting' | 'running' | 'error';
  started_at?: string;
  stopped_at?: string;
  error_message?: string;
}

export interface StreamCreate {
  camera_id: number;
  destination: 'youtube' | 'facebook' | 'twitch';
  stream_key: string;
  rtmp_url: string;
}

export interface StreamStatus {
  id: number;
  camera_id: number;
  destination: string;
  status: string;
  started_at?: string;
  stopped_at?: string;
  error_message?: string;
  metrics?: {
    bitrate_current: number;
    bitrate_target: number;
    framerate_actual: number;
    framerate_target: number;
    dropped_frames: number;
    encoding_time_ms: number;
    buffer_fullness: number;
    uptime_seconds: number;
    total_bytes_sent: number;
    last_update: string;
  };
  retry_count: number;
}

export const streamService = {
  async getStreams(): Promise<Stream[]> {
    const response = await api.get('/streams');
    return response.data;
  },

  async getStream(id: number): Promise<Stream> {
    const response = await api.get(`/streams/${id}`);
    return response.data;
  },

  async createStream(stream: StreamCreate): Promise<Stream> {
    const response = await api.post('/streams', stream);
    return response.data;
  },

  async deleteStream(id: number): Promise<void> {
    await api.delete(`/streams/${id}`);
  },

  async startStream(id: number): Promise<{ success: boolean; message: string }> {
    const response = await api.post(`/streams/${id}/start`);
    return response.data;
  },

  async stopStream(id: number): Promise<{ success: boolean; message: string }> {
    const response = await api.post(`/streams/${id}/stop`);
    return response.data;
  },

  async getStreamStatus(id: number): Promise<StreamStatus> {
    const response = await api.get(`/streams/${id}/status`);
    return response.data;
  },
};

