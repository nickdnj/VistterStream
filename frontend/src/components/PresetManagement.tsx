import React, { useEffect, useState } from 'react';
import { api } from '../services/api';

interface Camera {
  id: number;
  name: string;
  type: string;
  address: string;
  port: number;
  status: string;
  username?: string;
}

interface Preset {
  id: number;
  camera_id: number;
  name: string;
  pan: number;
  tilt: number;
  zoom: number;
  created_at: string;
  camera_preset_token?: string;
}

interface PTZStatus {
  available: boolean;
  pan?: number;
  tilt?: number;
  zoom?: number;
}

interface PresetEditorState {
  preset: Preset;
  pan: string;
  tilt: string;
  zoom: string;
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
  const [liveStatus, setLiveStatus] = useState<PTZStatus>({ available: false });
  const [statusError, setStatusError] = useState<string | null>(null);
  const [editorState, setEditorState] = useState<PresetEditorState | null>(null);
  const [editorSaving, setEditorSaving] = useState(false);
  const [editorError, setEditorError] = useState<string | null>(null);

  useEffect(() => {
    void loadData(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!showCaptureModal) {
      setLiveStatus({ available: false });
      setStatusError(null);
      return;
    }

    if (!selectedCamera) {
      return;
    }

    let interval: ReturnType<typeof setInterval> | undefined;

    const fetchStatus = async () => {
      try {
        const response = await api.get(`/presets/cameras/${selectedCamera}/status`);
        const data = response.data as PTZStatus & { camera_id: number };
        if (data.available) {
          setLiveStatus({
            available: true,
            pan: data.pan,
            tilt: data.tilt,
            zoom: data.zoom,
          });
          setStatusError(null);
        } else {
          setLiveStatus({ available: false });
          setStatusError(null);
        }
      } catch (error: any) {
        const detail = error?.response?.data?.detail || 'Failed to fetch PTZ status';
        setStatusError(detail);
      }
    };

    fetchStatus();
    interval = setInterval(fetchStatus, 2000);

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [selectedCamera, showCaptureModal]);

  const loadData = async (showSpinner = false) => {
    if (showSpinner) {
      setLoading(true);
    }

    let ptzCameras: Camera[] = [];
    let fetchedPresets: Preset[] = [];

    try {
      const token = localStorage.getItem('token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};

      const [camerasRes, presetsRes] = await Promise.all([
        api.get('/cameras', { headers }),
        api.get('/presets', { headers }),
      ]);

      if (camerasRes.data) {
        ptzCameras = (camerasRes.data as Camera[]).filter((camera) => camera.type === 'ptz');
        setCameras(ptzCameras);

        let nextSelected: number | null = selectedCamera;
        if (ptzCameras.length === 0) {
          nextSelected = null;
        } else if (!selectedCamera || !ptzCameras.some((camera) => camera.id === selectedCamera)) {
          nextSelected = ptzCameras[0].id;
        }

        if (nextSelected !== selectedCamera) {
          setSelectedCamera(nextSelected);
        }
      }

      if (presetsRes.data) {
        fetchedPresets = presetsRes.data as Preset[];
        setPresets(fetchedPresets);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      if (showSpinner) {
        setLoading(false);
      }
    }

    return { cameras: ptzCameras, presets: fetchedPresets };
  };

  const openEditor = (preset: Preset) => {
    setEditorState({
      preset,
      pan: (preset.pan ?? 0).toString(),
      tilt: (preset.tilt ?? 0).toString(),
      zoom: (preset.zoom ?? 0).toString(),
    });
    setEditorError(null);
  };

  const closeEditor = () => {
    if (editorSaving) {
      return;
    }
    setEditorState(null);
    setEditorError(null);
  };

  const handleEditorSave = async () => {
    if (!editorState) {
      return;
    }

    const parsedPan = parseFloat(editorState.pan);
    const parsedTilt = parseFloat(editorState.tilt);
    const parsedZoom = parseFloat(editorState.zoom);

    if (!Number.isFinite(parsedPan) || !Number.isFinite(parsedTilt) || !Number.isFinite(parsedZoom)) {
      setEditorError('Pan, tilt, and zoom must be numeric values.');
      return;
    }

    if (parsedPan < -180 || parsedPan > 180) {
      setEditorError('Pan must be between -180 and 180.');
      return;
    }
    if (parsedTilt < -90 || parsedTilt > 90) {
      setEditorError('Tilt must be between -90 and 90.');
      return;
    }
    if (parsedZoom < 0 || parsedZoom > 10) {
      setEditorError('Zoom must be between 0 and 10.');
      return;
    }

    setEditorSaving(true);
    try {
      const response = await api.patch(`/presets/${editorState.preset.id}`, {
        pan: parsedPan,
        tilt: parsedTilt,
        zoom: parsedZoom,
      });
      const updatedPreset = response.data as Preset;

      setPresets((prev) =>
        prev.map((preset) => (preset.id === updatedPreset.id ? updatedPreset : preset))
      );
      alert('✅ Preset updated successfully!');
      setEditorState(null);
      setEditorError(null);
    } catch (error: any) {
      console.error('Failed to update preset:', error);
      const detail = error.response?.data?.detail || 'Failed to update preset';
      setEditorError(detail);
    } finally {
      setEditorSaving(false);
    }
  };

  const handleCapturePreset = async () => {
    if (!selectedCamera || !presetName.trim()) {
      alert('Please select a camera and enter a preset name');
      return;
    }

    setCapturing(true);
    try {
      const response = await api.post('/presets/capture', null, {
        params: {
          camera_id: selectedCamera,
          preset_name: presetName.trim(),
        },
      });

      setPresetName('');
      setShowCaptureModal(false);
      setLiveStatus({ available: false });

      const newPreset = (response.data?.preset || response.data) as Preset;

      const data = await loadData();
      const resolvedPreset =
        data.presets.find((preset) => preset.id === newPreset.id) ?? newPreset;

      setSelectedCamera(resolvedPreset.camera_id);
      openEditor(resolvedPreset);
      alert('✅ Preset captured successfully! Verify the coordinates before saving.');
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
      const response = await api.post(`/presets/${presetId}/move`);
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
      await api.delete(`/presets/${presetId}`);
      await loadData();
      alert('✅ Preset deleted successfully');
    } catch (error: any) {
      console.error('Failed to delete preset:', error);
      alert(`Failed to delete preset: ${error.response?.data?.detail || 'Unknown error'}`);
    }
  };

  const getCameraName = (cameraId: number): string => {
    const camera = cameras.find((c) => c.id === cameraId);
    return camera?.name || `Camera ${cameraId}`;
  };

  const getPresetsForCamera = (cameraId: number): Preset[] => {
    return presets.filter((p) => p.camera_id === cameraId).sort((a, b) => a.id - b.id);
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
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">PTZ Presets</h2>
          <p className="text-gray-400 mt-1">
            Save, edit, and recall camera positions for your PTZ cameras
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

      <div className="bg-dark-800 rounded-lg p-4">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Select PTZ Camera
        </label>
        <select
          value={selectedCamera ?? ''}
          onChange={(event) => setSelectedCamera(parseInt(event.target.value, 10))}
          className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          {cameras.map((camera) => (
            <option key={camera.id} value={camera.id}>
              {camera.name} - {camera.address}
            </option>
          ))}
        </select>
      </div>

      {cameras.map((camera) => {
        const cameraPresets = getPresetsForCamera(camera.id);

        return (
          <div key={camera.id} className="bg-dark-800 rounded-lg overflow-hidden">
            <div className="px-6 py-4 bg-dark-700 border-b border-dark-600 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white flex items-center gap-3">
                <span className="text-2xl">📹</span>
                {camera.name}
              </h3>
              <span className="px-2 py-1 bg-dark-600 text-xs text-gray-400 rounded">
                {cameraPresets.length} {cameraPresets.length === 1 ? 'preset' : 'presets'}
              </span>
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
                    className="px-6 py-4 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4"
                  >
                    <div>
                      <h4 className="text-white font-medium text-lg">{preset.name}</h4>
                      <div className="mt-2 grid grid-cols-3 gap-4 text-sm text-gray-300">
                        <div>
                          <span className="block text-xs uppercase text-gray-500">Pan</span>
                          <span>{(preset.pan ?? 0).toFixed(3)}</span>
                        </div>
                        <div>
                          <span className="block text-xs uppercase text-gray-500">Tilt</span>
                          <span>{(preset.tilt ?? 0).toFixed(3)}</span>
                        </div>
                        <div>
                          <span className="block text-xs uppercase text-gray-500">Zoom</span>
                          <span>{(preset.zoom ?? 0).toFixed(3)}</span>
                        </div>
                      </div>
                      <div className="text-xs text-gray-500 mt-2">
                        Created {new Date(preset.created_at).toLocaleString()}
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => openEditor(preset)}
                        className="px-4 py-2 bg-dark-600 hover:bg-dark-500 text-white rounded-md font-medium transition-colors"
                      >
                        ✏️ Edit
                      </button>
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
                ))}
              </div>
            )}
          </div>
        );
      })}

      {showCaptureModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-dark-800 rounded-lg p-6 w-full max-w-md space-y-4">
            <h3 className="text-xl font-bold text-white">📸 Capture Preset</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Camera
                </label>
                <div className="px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white">
                  {selectedCamera ? getCameraName(selectedCamera) : 'Select a camera'}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Position the camera using its controls, then capture.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Preset Name *
                </label>
                <input
                  type="text"
                  value={presetName}
                  onChange={(event) => setPresetName(event.target.value)}
                  placeholder="e.g. Wide Shot, Close Up, Stage Left"
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  autoFocus
                />
              </div>

              <div className="bg-blue-900 bg-opacity-20 border border-blue-700 rounded-md p-3">
                <p className="text-sm text-blue-300">
                  💡 <strong>Tip:</strong> Verify the camera position before capturing.
                </p>
              </div>

              <div className="bg-dark-700 border border-dark-600 rounded-md p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-300">Live PTZ status</span>
                  {statusError ? (
                    <span className="text-xs text-red-400">{statusError}</span>
                  ) : (
                    <span className="text-xs text-gray-400">Updates every 2s</span>
                  )}
                </div>
                {liveStatus.available ? (
                  <div className="mt-2 flex gap-4 text-sm text-blue-300">
                    <span>Pan: {liveStatus.pan?.toFixed(3)}</span>
                    <span>Tilt: {liveStatus.tilt?.toFixed(3)}</span>
                    <span>Zoom: {liveStatus.zoom?.toFixed(3)}</span>
                  </div>
                ) : (
                  <div className="mt-2 text-sm text-gray-400">
                    PTZ position not available yet.
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => {
                  setShowCaptureModal(false);
                  setPresetName('');
                  setLiveStatus({ available: false });
                  setStatusError(null);
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

      {editorState && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-dark-800 rounded-lg p-6 w-full max-w-lg space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-bold text-white">🛠 Edit PTZ Coordinates</h3>
              <span className="text-sm text-gray-400">
                {getCameraName(editorState.preset.camera_id)} • {editorState.preset.name}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <label className="flex flex-col text-sm text-gray-300">
                <span className="mb-1 uppercase tracking-wide text-xs text-gray-500">Pan</span>
                <input
                  type="number"
                  min={-180}
                  max={180}
                  step={0.001}
                  value={editorState.pan}
                  onChange={(event) =>
                    setEditorState((prev) =>
                      prev
                        ? {
                            ...prev,
                            pan: event.target.value,
                          }
                        : prev
                    )
                  }
                  className="px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </label>

              <label className="flex flex-col text-sm text-gray-300">
                <span className="mb-1 uppercase tracking-wide text-xs text-gray-500">Tilt</span>
                <input
                  type="number"
                  min={-90}
                  max={90}
                  step={0.001}
                  value={editorState.tilt}
                  onChange={(event) =>
                    setEditorState((prev) =>
                      prev
                        ? {
                            ...prev,
                            tilt: event.target.value,
                          }
                        : prev
                    )
                  }
                  className="px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </label>

              <label className="flex flex-col text-sm text-gray-300">
                <span className="mb-1 uppercase tracking-wide text-xs text-gray-500">Zoom</span>
                <input
                  type="number"
                  min={0}
                  max={10}
                  step={0.01}
                  value={editorState.zoom}
                  onChange={(event) =>
                    setEditorState((prev) =>
                      prev
                        ? {
                            ...prev,
                            zoom: event.target.value,
                          }
                        : prev
                    )
                  }
                  className="px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </label>
            </div>

            {editorError && (
              <div className="bg-red-900 bg-opacity-30 border border-red-700 rounded-md p-3 text-sm text-red-300">
                {editorError}
              </div>
            )}

            <div className="flex gap-3 justify-end">
              <button
                onClick={closeEditor}
                disabled={editorSaving}
                className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-md font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleEditorSave}
                disabled={editorSaving}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${
                  editorSaving
                    ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                    : 'bg-green-600 hover:bg-green-700 text-white'
                }`}
              >
                {editorSaving ? '💾 Saving…' : '💾 Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PresetManagement;
