import { api } from './api';

export interface Camera {
  id: number;
  name: string;
  type: 'stationary' | 'ptz';
  protocol: 'rtsp' | 'rtmp';
  address: string;
  username?: string;
  port: number;
  stream_path: string;
  snapshot_url?: string;
  is_active: boolean;
  created_at: string;
  last_seen?: string;
}

export interface CameraWithStatus extends Camera {
  status: 'online' | 'offline' | 'error';
  last_error?: string;
}

export interface CameraCreate {
  name: string;
  type: 'stationary' | 'ptz';
  protocol: 'rtsp' | 'rtmp';
  address: string;
  username?: string;
  password?: string;
  port: number;
  stream_path: string;
  snapshot_url?: string;
}

export interface CameraTestResponse {
  success: boolean;
  message: string;
  rtsp_accessible: boolean;
  snapshot_accessible: boolean;
  error_details?: string;
}

export const cameraService = {
  async getCameras(): Promise<CameraWithStatus[]> {
    const response = await api.get('/cameras/');
    return Array.isArray(response.data) ? response.data : [];
  },

  async getCamera(id: number): Promise<CameraWithStatus> {
    const response = await api.get(`/cameras/${id}`);
    return response.data;
  },

  async createCamera(camera: CameraCreate): Promise<Camera> {
    const response = await api.post('/cameras', camera);
    return response.data;
  },

  async updateCamera(id: number, camera: Partial<CameraCreate>): Promise<Camera> {
    const response = await api.put(`/cameras/${id}`, camera);
    return response.data;
  },

  async deleteCamera(id: number): Promise<void> {
    await api.delete(`/cameras/${id}`);
  },

  async testCameraConnection(id: number): Promise<CameraTestResponse> {
    const response = await api.post(`/cameras/${id}/test`);
    return response.data;
  },

  async testCameraConnectionDirect(camera: CameraCreate): Promise<CameraTestResponse> {
    const response = await api.post('/cameras/test-connection', camera);
    return response.data;
  },

  async getCameraSnapshot(id: number): Promise<{ image_data: string; content_type: string; timestamp: string }> {
    const response = await api.get(`/cameras/${id}/snapshot`);
    return response.data;
  },
};
