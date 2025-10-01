import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Camera {
  id: number;
  name: string;
  type: string;
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

interface Cue {
  id?: number;
  cue_order: number;
  start_time: number;
  duration: number;
  action_type: string;
  action_params: {
    camera_id?: number;
    preset_id?: number;
    transition?: string;
  };
  transition_type: string;
  transition_duration: number;
}

interface Track {
  id?: number;
  track_type: string;
  layer: number;
  is_enabled: boolean;
  cues: Cue[];
}

interface Timeline {
  id?: number;
  name: string;
  description: string;
  duration: number;
  fps: number;
  resolution: string;
  loop: boolean;
  is_active?: boolean;
  tracks: Track[];
}

interface Destination {
  id: number;
  name: string;
  platform: string;
  rtmp_url: string;
  is_active: boolean;
}

const TimelineEditor: React.FC = () => {
  const [timelines, setTimelines] = useState<Timeline[]>([]);
  const [selectedTimeline, setSelectedTimeline] = useState<Timeline | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [selectedDestinations, setSelectedDestinations] = useState<number[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [showNewTimelineModal, setShowNewTimelineModal] = useState(false);

  // New timeline form
  const [newTimeline, setNewTimeline] = useState<Timeline>({
    name: '',
    description: '',
    duration: 120,
    fps: 30,
    resolution: '1920x1080',
    loop: true,
    tracks: [{
      track_type: 'video',
      layer: 0,
      is_enabled: true,
      cues: []
    }]
  });

  useEffect(() => {
    loadTimelines();
    loadCameras();
    loadPresets();
    loadDestinations();
  }, []);

  const loadTimelines = async () => {
    try {
      const response = await axios.get('/api/timelines/');
      setTimelines(response.data);
    } catch (error) {
      console.error('Failed to load timelines:', error);
    }
  };

  const loadCameras = async () => {
    try {
      const response = await axios.get('/api/cameras/');
      setCameras(response.data);
    } catch (error) {
      console.error('Failed to load cameras:', error);
    }
  };

  const loadPresets = async () => {
    try {
      const response = await axios.get('/api/presets/');
      setPresets(response.data);
    } catch (error) {
      console.error('Failed to load presets:', error);
    }
  };

  const loadDestinations = async () => {
    try {
      const response = await axios.get('/api/destinations/');
      setDestinations(response.data.filter((d: Destination) => d.is_active));
    } catch (error) {
      console.error('Failed to load destinations:', error);
    }
  };

  const createTimeline = async () => {
    try {
      const response = await axios.post('/api/timelines/', newTimeline);
      setTimelines([...timelines, response.data]);
      setShowNewTimelineModal(false);
      setNewTimeline({
        name: '',
        description: '',
        duration: 120,
        fps: 30,
        resolution: '1920x1080',
        loop: true,
        tracks: [{
          track_type: 'video',
          layer: 0,
          is_enabled: true,
          cues: []
        }]
      });
    } catch (error) {
      console.error('Failed to create timeline:', error);
      alert('Failed to create timeline');
    }
  };

  const addCueToTimeline = (camera: Camera, preset?: Preset) => {
    if (!selectedTimeline) return;

    const videoTrack = selectedTimeline.tracks.find(t => t.track_type === 'video');
    if (!videoTrack) return;

    const lastCue = videoTrack.cues[videoTrack.cues.length - 1];
    const startTime = lastCue ? lastCue.start_time + lastCue.duration : 0;

    const newCue: Cue = {
      cue_order: videoTrack.cues.length + 1,
      start_time: startTime,
      duration: 60,
      action_type: 'show_camera',
      action_params: {
        camera_id: camera.id,
        preset_id: preset?.id,
        transition: 'cut'
      },
      transition_type: 'cut',
      transition_duration: 0
    };

    videoTrack.cues.push(newCue);
    setSelectedTimeline({ ...selectedTimeline });
  };

  const getPresetsForCamera = (cameraId: number): Preset[] => {
    return presets.filter(p => p.camera_id === cameraId);
  };

  const getCameraById = (cameraId: number): Camera | undefined => {
    return cameras.find(c => c.id === cameraId);
  };

  const getPresetById = (presetId: number): Preset | undefined => {
    return presets.find(p => p.id === presetId);
  };

  const removeCue = (trackIndex: number, cueIndex: number) => {
    if (!selectedTimeline) return;
    
    selectedTimeline.tracks[trackIndex].cues.splice(cueIndex, 1);
    
    // Reorder cues
    selectedTimeline.tracks[trackIndex].cues.forEach((cue, idx) => {
      cue.cue_order = idx + 1;
    });
    
    setSelectedTimeline({ ...selectedTimeline });
  };

  const saveTimeline = async () => {
    if (!selectedTimeline || !selectedTimeline.id) return;

    try {
      await axios.put(`/api/timelines/${selectedTimeline.id}`, selectedTimeline);
      alert('Timeline saved successfully!');
      loadTimelines();
    } catch (error) {
      console.error('Failed to save timeline:', error);
      alert('Failed to save timeline');
    }
  };

  const startTimeline = async () => {
    if (!selectedTimeline || !selectedTimeline.id || selectedDestinations.length === 0) {
      alert('Please select a timeline and at least one destination');
      return;
    }

    try {
      const response = await axios.post('/api/timeline-execution/start', {
        timeline_id: selectedTimeline.id,
        destination_ids: selectedDestinations
      });
      setIsRunning(true);
      alert(`Timeline started!\nStreaming to: ${response.data.destinations.join(', ')}`);
    } catch (error) {
      console.error('Failed to start timeline:', error);
      alert('Failed to start timeline');
    }
  };

  const stopTimeline = async () => {
    if (!selectedTimeline || !selectedTimeline.id) return;

    try {
      await axios.post(`/api/timeline-execution/stop/${selectedTimeline.id}`);
      setIsRunning(false);
      alert('Timeline stopped!');
    } catch (error) {
      console.error('Failed to stop timeline:', error);
      alert('Failed to stop timeline');
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getCameraName = (cameraId: number) => {
    const camera = cameras.find(c => c.id === cameraId);
    return camera ? camera.name : `Camera ${cameraId}`;
  };

  const getPresetName = (presetId: number) => {
    const preset = presets.find(p => p.id === presetId);
    return preset ? preset.name : `Preset ${presetId}`;
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">🎬 Timeline Editor</h1>
        <p className="text-gray-400">Create and manage composite streams with camera switching</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar: Timelines List */}
        <div className="lg:col-span-1">
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-white">Timelines</h2>
              <button
                onClick={() => setShowNewTimelineModal(true)}
                className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
              >
                + New
              </button>
            </div>
            
            <div className="space-y-2">
              {timelines.map((timeline) => (
                <div
                  key={timeline.id}
                  onClick={() => setSelectedTimeline(timeline)}
                  className={`p-3 rounded cursor-pointer transition-colors ${
                    selectedTimeline?.id === timeline.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  <div className="font-medium">{timeline.name}</div>
                  <div className="text-xs text-gray-400 mt-1">
                    {formatTime(timeline.duration)} • {timeline.loop ? 'Loop' : 'Once'}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Camera Palette */}
          <div className="bg-gray-800 rounded-lg p-4 mt-4">
            <h2 className="text-xl font-semibold text-white mb-4">📷 Cameras</h2>
            <div className="space-y-2">
              {cameras.map((camera) => {
                const cameraPresets = getPresetsForCamera(camera.id);
                const isPTZ = camera.type === 'ptz';
                
                return (
                  <div key={camera.id} className="bg-gray-700 rounded overflow-hidden">
                    {/* Camera Header */}
                    <div
                      onClick={() => addCueToTimeline(camera)}
                      className="hover:bg-gray-600 p-3 cursor-pointer transition-colors"
                    >
                      <div className="text-white font-medium flex items-center justify-between">
                        <span>
                          {isPTZ && '🎯 '}
                          {camera.name}
                          {isPTZ && ` (${cameraPresets.length} presets)`}
                        </span>
                        <span className="text-xs bg-gray-600 px-2 py-1 rounded capitalize">
                          {camera.type}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        Click to add at current position
                      </div>
                    </div>
                    
                    {/* Presets (for PTZ cameras) */}
                    {isPTZ && cameraPresets.length > 0 && (
                      <div className="bg-gray-800 border-t border-gray-600 p-2">
                        <div className="text-xs text-gray-400 mb-2 px-2">Presets:</div>
                        <div className="space-y-1">
                          {cameraPresets.map((preset) => (
                            <div
                              key={preset.id}
                              onClick={(e) => {
                                e.stopPropagation();
                                addCueToTimeline(camera, preset);
                              }}
                              className="bg-gray-700 hover:bg-blue-600 p-2 rounded cursor-pointer transition-colors text-sm"
                            >
                              <div className="text-white">🎯 {preset.name}</div>
                              <div className="text-xs text-gray-400">
                                Pan: {preset.pan.toFixed(1)}, Tilt: {preset.tilt.toFixed(1)}, Zoom: {preset.zoom.toFixed(1)}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            {cameras.length === 0 && (
              <p className="text-gray-500 text-sm">No cameras available</p>
            )}
          </div>
        </div>

        {/* Main Editor Area */}
        <div className="lg:col-span-3">
          {selectedTimeline ? (
            <div className="bg-gray-800 rounded-lg p-6">
              {/* Timeline Header */}
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-white mb-2">{selectedTimeline.name}</h2>
                <p className="text-gray-400">{selectedTimeline.description}</p>
                
                {/* Timeline Controls */}
                <div className="mt-4 flex gap-4 items-center flex-wrap">
                  <button
                    onClick={saveTimeline}
                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded"
                  >
                    💾 Save Timeline
                  </button>
                  
                  <div className="flex gap-2 items-center">
                    <select
                      multiple
                      value={selectedDestinations.map(String)}
                      onChange={(e) => {
                        const selected = Array.from(e.target.selectedOptions, option => parseInt(option.value));
                        setSelectedDestinations(selected);
                      }}
                      className="bg-gray-700 text-white px-3 py-2 rounded w-64 h-24"
                    >
                      {destinations.map((dest) => (
                        <option key={dest.id} value={dest.id}>
                          {dest.platform === 'youtube' && '📺'}
                          {dest.platform === 'facebook' && '👥'}
                          {dest.platform === 'twitch' && '🎮'}
                          {dest.platform === 'custom' && '🔧'}
                          {' '}{dest.name}
                        </option>
                      ))}
                    </select>
                    <div className="text-gray-400 text-sm">
                      Hold Cmd/Ctrl<br />to select multiple
                    </div>
                    {!isRunning ? (
                      <button
                        onClick={startTimeline}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
                      >
                        ▶️ Start
                      </button>
                    ) : (
                      <button
                        onClick={stopTimeline}
                        className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
                      >
                        ⏹️ Stop
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Timeline Tracks */}
              {selectedTimeline.tracks.map((track, trackIdx) => (
                <div key={trackIdx} className="mb-6">
                  <div className="flex items-center mb-3">
                    <h3 className="text-lg font-semibold text-white capitalize">
                      {track.track_type} Track
                    </h3>
                  </div>

                  {/* Cues */}
                  <div className="space-y-2">
                    {track.cues.length === 0 ? (
                      <div className="bg-gray-700 p-6 rounded text-center text-gray-400">
                        Click a camera to add it to the timeline
                      </div>
                    ) : (
                      track.cues.map((cue, cueIdx) => (
                        <div
                          key={cueIdx}
                          className="bg-gray-700 p-4 rounded flex justify-between items-center"
                        >
                          <div className="flex-1">
                            <div className="flex items-center gap-3">
                              <span className="text-gray-400 font-mono">
                                {formatTime(cue.start_time)}
                              </span>
                              <span className="text-white font-medium">
                                {cue.action_type === 'show_camera' && (
                                  <>
                                    {getCameraName(cue.action_params.camera_id!)}
                                    {cue.action_params.preset_id && (
                                      <span className="text-blue-400 ml-2">
                                        🎯 {getPresetName(cue.action_params.preset_id)}
                                      </span>
                                    )}
                                  </>
                                )}
                              </span>
                              <span className="text-gray-400 text-sm">
                                ({cue.duration}s)
                              </span>
                            </div>
                          </div>
                          
                          <div className="flex gap-2">
                            <input
                              type="number"
                              value={cue.duration}
                              onChange={(e) => {
                                cue.duration = parseFloat(e.target.value);
                                setSelectedTimeline({ ...selectedTimeline });
                              }}
                              className="bg-gray-600 text-white px-2 py-1 rounded w-20"
                            />
                            <button
                              onClick={() => removeCue(trackIdx, cueIdx)}
                              className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded"
                            >
                              🗑️
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-gray-800 rounded-lg p-12 text-center">
              <p className="text-gray-400 text-lg">Select a timeline to edit</p>
            </div>
          )}
        </div>
      </div>

      {/* New Timeline Modal */}
      {showNewTimelineModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-2xl font-bold text-white mb-4">Create New Timeline</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-gray-300 mb-2">Name</label>
                <input
                  type="text"
                  value={newTimeline.name}
                  onChange={(e) => setNewTimeline({ ...newTimeline, name: e.target.value })}
                  className="w-full bg-gray-700 text-white px-3 py-2 rounded"
                  placeholder="My Awesome Timeline"
                />
              </div>
              
              <div>
                <label className="block text-gray-300 mb-2">Description</label>
                <textarea
                  value={newTimeline.description}
                  onChange={(e) => setNewTimeline({ ...newTimeline, description: e.target.value })}
                  className="w-full bg-gray-700 text-white px-3 py-2 rounded h-20"
                  placeholder="What's this timeline for?"
                />
              </div>
              
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={newTimeline.loop}
                  onChange={(e) => setNewTimeline({ ...newTimeline, loop: e.target.checked })}
                  className="w-4 h-4"
                />
                <label className="text-gray-300">Loop forever</label>
              </div>
            </div>
            
            <div className="mt-6 flex gap-3">
              <button
                onClick={createTimeline}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
              >
                Create
              </button>
              <button
                onClick={() => setShowNewTimelineModal(false)}
                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelineEditor;

