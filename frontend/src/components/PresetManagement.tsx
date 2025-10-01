import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Camera {
  id: number;
  name: string;
  type: string;
  address: string;
  port: number;
  status: string;
}

interface Preset {
  id: number;
  camera_id: number;
  name: string;
  pan: number;
  tilt: number;
  zoom: number;
  created_at: string;
}

const PresetManagement: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCamera, setSelectedCamera] = useState<number | null>(null);
  const [showCaptureModal, setShowCaptureModal] = useState(false);
  const [presetName, setPresetName] = useState('');
  const [capturing, setCapturing] = useState(false);
  const [testingPreset, setTestingPreset] = useState<number | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [camerasRes, presetsRes] = await Promise.all([
        axios.get('/api/cameras/', { headers }),
        axios.get('/api/presets/', { headers })
      ]);

      if (camerasRes.data) {
        // Filter to only PTZ cameras
        const ptzCameras = camerasRes.data.filter((c: Camera) => c.type === 'ptz');
        setCameras(ptzCameras);
        
        // Auto-select first PTZ camera
        if (ptzCameras.length > 0 && !selectedCamera) {
          setSelectedCamera(ptzCameras[0].id);
        }
      }

      if (presetsRes.data) {
        setPresets(presetsRes.data);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCapturePreset = async () => {
    if (!selectedCamera || !presetName.trim()) {
      alert('Please select a camera and enter a preset name');
      return;
    }

    setCapturing(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        '/api/presets/capture',
        null,
        {
          params: {
            camera_id: selectedCamera,
            preset_name: presetName
          },
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );

      setPresetName('');
      setShowCaptureModal(false);
      loadData();
      alert('✅ Preset captured successfully!');
    } catch (error: any) {
      console.error('Failed to capture preset:', error);
      alert(`Failed to capture preset: ${error.response?.data?.detail || 'Unknown error'}`);
    } finally {
      setCapturing(false);
    }
  };

  const handleMoveToPreset = async (presetId: number, presetName: string) => {
    if (!window.confirm(`Move camera to preset "${presetName}"?`)) {
      return;
    }

    setTestingPreset(presetId);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `/api/presets/${presetId}/move`,
        null,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );

      alert(`✅ ${response.data.message}`);
    } catch (error: any) {
      console.error('Failed to move to preset:', error);
      alert(`Failed to move camera: ${error.response?.data?.detail || 'Unknown error'}`);
    } finally {
      setTestingPreset(null);
    }
  };

  const handleDeletePreset = async (presetId: number, presetName: string) => {
    if (!window.confirm(`Delete preset "${presetName}"?`)) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      await axios.delete(`/api/presets/${presetId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      loadData();
      alert('✅ Preset deleted successfully');
    } catch (error: any) {
      console.error('Failed to delete preset:', error);
      alert(`Failed to delete preset: ${error.response?.data?.detail || 'Unknown error'}`);
    }
  };

  const getCameraName = (cameraId: number): string => {
    const camera = cameras.find(c => c.id === cameraId);
    return camera?.name || `Camera ${cameraId}`;
  };

  const getPresetsForCamera = (cameraId: number): Preset[] => {
    return presets.filter(p => p.camera_id === cameraId);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading presets...</div>
      </div>
    );
  }

  if (cameras.length === 0) {
    return (
      <div className="bg-dark-800 rounded-lg p-8 text-center">
        <div className="text-6xl mb-4">📷</div>
        <h3 className="text-xl font-semibold text-white mb-2">No PTZ Cameras Found</h3>
        <p className="text-gray-400 mb-4">
          PTZ presets require cameras with pan/tilt/zoom capabilities.
        </p>
        <p className="text-sm text-gray-500">
          Add PTZ cameras in the Camera Management page.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">PTZ Presets</h2>
          <p className="text-gray-400 mt-1">
            Save and recall camera positions for your PTZ cameras
          </p>
        </div>
        <button
          onClick={() => setShowCaptureModal(true)}
          disabled={!selectedCamera}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            selectedCamera
              ? 'bg-primary-600 hover:bg-primary-700 text-white'
              : 'bg-gray-700 text-gray-500 cursor-not-allowed'
          }`}
        >
          📸 Capture Preset
        </button>
      </div>

      {/* Camera Selector */}
      <div className="bg-dark-800 rounded-lg p-4">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Select PTZ Camera
        </label>
        <select
          value={selectedCamera || ''}
          onChange={(e) => setSelectedCamera(parseInt(e.target.value))}
          className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          {cameras.map((camera) => (
            <option key={camera.id} value={camera.id}>
              {camera.name} - {camera.address}
            </option>
          ))}
        </select>
      </div>

      {/* Presets List */}
      {cameras.map((camera) => {
        const cameraPresets = getPresetsForCamera(camera.id);
        
        return (
          <div key={camera.id} className="bg-dark-800 rounded-lg overflow-hidden">
            <div className="px-6 py-4 bg-dark-700 border-b border-dark-600">
              <h3 className="text-lg font-semibold text-white flex items-center">
                <span className="text-2xl mr-3">📹</span>
                {camera.name}
                <span className="ml-3 px-2 py-1 bg-dark-600 text-xs text-gray-400 rounded">
                  {cameraPresets.length} {cameraPresets.length === 1 ? 'preset' : 'presets'}
                </span>
              </h3>
            </div>

            {cameraPresets.length === 0 ? (
              <div className="px-6 py-8 text-center text-gray-500">
                <div className="text-4xl mb-2">🎯</div>
                <p>No presets saved for this camera</p>
                <p className="text-sm mt-1">Capture a preset to get started</p>
              </div>
            ) : (
              <div className="divide-y divide-dark-600">
                {cameraPresets.map((preset) => (
                  <div
                    key={preset.id}
                    className="px-6 py-4 hover:bg-dark-700 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h4 className="text-white font-medium text-lg mb-1">
                          {preset.name}
                        </h4>
                        <div className="flex gap-4 text-sm text-gray-400">
                          <span>Pan: {preset.pan.toFixed(2)}</span>
                          <span>Tilt: {preset.tilt.toFixed(2)}</span>
                          <span>Zoom: {preset.zoom.toFixed(2)}</span>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          Created {new Date(preset.created_at).toLocaleString()}
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <button
                          onClick={() => handleMoveToPreset(preset.id, preset.name)}
                          disabled={testingPreset === preset.id}
                          className={`px-4 py-2 rounded-md font-medium transition-colors ${
                            testingPreset === preset.id
                              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                              : 'bg-blue-600 hover:bg-blue-700 text-white'
                          }`}
                        >
                          {testingPreset === preset.id ? '⏳ Moving...' : '🎯 Go To'}
                        </button>
                        <button
                          onClick={() => handleDeletePreset(preset.id, preset.name)}
                          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md font-medium transition-colors"
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}

      {/* Capture Preset Modal */}
      {showCaptureModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-dark-800 rounded-lg p-6 w-full max-w-md">
            <h3 className="text-xl font-bold text-white mb-4">📸 Capture Preset</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Camera
                </label>
                <div className="px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white">
                  {getCameraName(selectedCamera!)}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Position the camera using its web interface or controls, then capture
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Preset Name *
                </label>
                <input
                  type="text"
                  value={presetName}
                  onChange={(e) => setPresetName(e.target.value)}
                  placeholder="e.g. Wide Shot, Close Up, Stage Left"
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  autoFocus
                />
              </div>

              <div className="bg-blue-900 bg-opacity-20 border border-blue-700 rounded-md p-3">
                <p className="text-sm text-blue-300">
                  💡 <strong>Tip:</strong> Position your camera first, then click "Capture" to save the current position
                </p>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowCaptureModal(false);
                  setPresetName('');
                }}
                className="flex-1 px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-md font-medium transition-colors"
                disabled={capturing}
              >
                Cancel
              </button>
              <button
                onClick={handleCapturePreset}
                disabled={capturing || !presetName.trim()}
                className={`flex-1 px-4 py-2 rounded-md font-medium transition-colors ${
                  capturing || !presetName.trim()
                    ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                    : 'bg-primary-600 hover:bg-primary-700 text-white'
                }`}
              >
                {capturing ? '⏳ Capturing...' : '📸 Capture'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PresetManagement;
