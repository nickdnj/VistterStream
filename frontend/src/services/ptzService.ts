import { api } from './api';

export interface Preset {
  id: number;
  camera_id: number;
  name: string;
  pan: number;
  tilt: number;
  zoom: number;
  created_at: string;
  camera_preset_token?: string;
}

export interface PTZStatus {
  camera_id: number;
  available: boolean;
  pan?: number;
  tilt?: number;
  zoom?: number;
}

export const ptzService = {
  async continuousMove(cameraId: number, panSpeed: number, tiltSpeed: number, zoomSpeed: number): Promise<void> {
    await api.post(`/cameras/${cameraId}/ptz/continuous`, {
      pan_speed: panSpeed,
      tilt_speed: tiltSpeed,
      zoom_speed: zoomSpeed,
    });
  },

  async stopMovement(cameraId: number): Promise<void> {
    await api.post(`/cameras/${cameraId}/ptz/stop`);
  },

  async absoluteMove(cameraId: number, pan: number, tilt: number, zoom: number): Promise<void> {
    await api.post(`/cameras/${cameraId}/ptz/absolute`, { pan, tilt, zoom });
  },

  async getStatus(cameraId: number): Promise<PTZStatus> {
    const response = await api.get(`/cameras/${cameraId}/ptz/status`);
    return response.data;
  },

  async capturePreset(cameraId: number, presetName: string): Promise<Preset> {
    const response = await api.post('/presets/capture', null, {
      params: { camera_id: cameraId, preset_name: presetName },
    });
    return response.data?.preset || response.data;
  },

  async moveToPreset(presetId: number): Promise<void> {
    await api.post(`/presets/${presetId}/move`);
  },

  async getPresets(cameraId: number): Promise<Preset[]> {
    const response = await api.get('/presets', { params: { camera_id: cameraId } });
    return Array.isArray(response.data) ? response.data : [];
  },

  async deletePreset(presetId: number): Promise<void> {
    await api.delete(`/presets/${presetId}`);
  },

  async updatePreset(presetId: number, data: Partial<Pick<Preset, 'name' | 'pan' | 'tilt' | 'zoom'>>): Promise<Preset> {
    const response = await api.patch(`/presets/${presetId}`, data);
    return response.data;
  },
};
