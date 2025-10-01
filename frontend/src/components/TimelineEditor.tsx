import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ChevronDownIcon, ChevronRightIcon, PlusIcon, TrashIcon, PlayIcon, StopIcon } from '@heroicons/react/24/outline';

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

  // Sidebar collapse states
  const [camerasExpanded, setCamerasExpanded] = useState(true);
  const [assetsExpanded, setAssetsExpanded] = useState(false);
  const [expandedCameras, setExpandedCameras] = useState<Set<number>>(new Set());

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
      if (response.data.length > 0 && !selectedTimeline) {
        setSelectedTimeline(response.data[0]);
      }
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
    if (!newTimeline.name.trim()) {
      alert('Please enter a timeline name');
      return;
    }

    try {
      const response = await axios.post('/api/timelines/', newTimeline);
      setTimelines([...timelines, response.data]);
      setSelectedTimeline(response.data);
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

  const removeCue = (trackIndex: number, cueIndex: number) => {
    if (!selectedTimeline) return;
    
    selectedTimeline.tracks[trackIndex].cues.splice(cueIndex, 1);
    
    // Recalculate start times
    selectedTimeline.tracks[trackIndex].cues.forEach((cue, idx) => {
      if (idx === 0) {
        cue.start_time = 0;
      } else {
        const prevCue = selectedTimeline.tracks[trackIndex].cues[idx - 1];
        cue.start_time = prevCue.start_time + prevCue.duration;
      }
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
      // First, try to stop the timeline if it's already running
      try {
        await axios.post(`/api/timeline-execution/stop/${selectedTimeline.id}`);
        console.log('Stopped existing timeline instance');
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
      } catch (stopError) {
        // Timeline wasn't running, that's fine
        console.log('No existing timeline to stop');
      }

      // Now start the timeline
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

  // Drag and drop handlers
  const handleDragStart = (e: React.DragEvent, camera: Camera, preset?: Preset) => {
    e.dataTransfer.setData('camera', JSON.stringify(camera));
    if (preset) {
      e.dataTransfer.setData('preset', JSON.stringify(preset));
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const cameraData = e.dataTransfer.getData('camera');
    const presetData = e.dataTransfer.getData('preset');
    
    if (cameraData) {
      const camera = JSON.parse(cameraData);
      const preset = presetData ? JSON.parse(presetData) : undefined;
      addCueToTimeline(camera, preset);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  return (
    <div className="h-screen flex flex-col bg-dark-900">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-6 py-4 bg-dark-800 border-b border-dark-700">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-white">🎬 Timeline Editor</h1>
          {selectedTimeline && (
            <span className="text-gray-400">→ {selectedTimeline.name}</span>
          )}
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowNewTimelineModal(true)}
            className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-md flex items-center gap-2"
          >
            <PlusIcon className="h-4 w-4" />
            New Timeline
          </button>
          
          {selectedTimeline && (
            <>
              <button
                onClick={saveTimeline}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md"
              >
                💾 Save
              </button>
              
              <div className="flex items-center gap-2">
                <select
                  multiple
                  value={selectedDestinations.map(String)}
                  onChange={(e) => {
                    const selected = Array.from(e.target.selectedOptions, option => parseInt(option.value));
                    setSelectedDestinations(selected);
                  }}
                  className="bg-dark-700 text-white px-3 py-2 rounded h-20 w-48"
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
                
                {!isRunning ? (
                  <button
                    onClick={startTimeline}
                    className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md font-semibold"
                  >
                    ▶️ Start
                  </button>
                ) : (
                  <button
                    onClick={stopTimeline}
                    className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md font-semibold"
                  >
                    ⏹️ Stop
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - VistterStudio Style */}
        <div className="w-80 bg-dark-800 border-r border-dark-700 flex flex-col overflow-hidden">
          {/* Studio Label */}
          <div className="px-4 py-3 bg-dark-900 border-b border-dark-700">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Studio</h2>
          </div>

          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto">
            {/* Cameras Section */}
            <div className="border-b border-dark-700">
              <button
                onClick={() => setCamerasExpanded(!camerasExpanded)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-dark-700 transition-colors"
              >
                <div className="flex items-center gap-2">
                  {camerasExpanded ? (
                    <ChevronDownIcon className="h-4 w-4 text-gray-400" />
                  ) : (
                    <ChevronRightIcon className="h-4 w-4 text-gray-400" />
                  )}
                  <span className="text-white font-medium">📷 Cameras</span>
                </div>
                <span className="text-xs text-gray-500">{cameras.length} cameras</span>
              </button>

              {camerasExpanded && (
                <div className="bg-dark-900 px-2 py-2">
                  {cameras.map((camera) => {
                    const cameraPresets = getPresetsForCamera(camera.id);
                    const isPTZ = camera.type === 'ptz';
                    const cameraExpanded = expandedCameras.has(camera.id);

                    return (
                      <div key={camera.id} className="mb-1">
                        <div
                          draggable
                          onDragStart={(e) => handleDragStart(e, camera)}
                          className="flex items-center justify-between px-3 py-2 bg-dark-800 hover:bg-dark-700 rounded cursor-move transition-colors group"
                        >
                          <div className="flex items-center gap-2 flex-1">
                            {isPTZ && cameraPresets.length > 0 && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  const newExpanded = new Set(expandedCameras);
                                  if (cameraExpanded) {
                                    newExpanded.delete(camera.id);
                                  } else {
                                    newExpanded.add(camera.id);
                                  }
                                  setExpandedCameras(newExpanded);
                                }}
                                className="hover:bg-dark-600 rounded p-0.5"
                              >
                                {cameraExpanded ? (
                                  <ChevronDownIcon className="h-3 w-3 text-gray-400" />
                                ) : (
                                  <ChevronRightIcon className="h-3 w-3 text-gray-400" />
                                )}
                              </button>
                            )}
                            <div className="w-8 h-8 bg-blue-600 rounded flex items-center justify-center text-white text-xs">
                              📹
                            </div>
                            <div className="flex-1">
                              <div className="text-white text-sm font-medium">{camera.name}</div>
                              <div className="text-xs text-gray-500 capitalize">{camera.type}</div>
                            </div>
                          </div>
                          {isPTZ && cameraPresets.length > 0 && (
                            <span className="text-xs text-gray-500">{cameraPresets.length} presets</span>
                          )}
                        </div>

                        {/* Presets under camera */}
                        {isPTZ && cameraExpanded && cameraPresets.length > 0 && (
                          <div className="ml-6 mt-1 space-y-1">
                            {cameraPresets.map((preset) => (
                              <div
                                key={preset.id}
                                draggable
                                onDragStart={(e) => handleDragStart(e, camera, preset)}
                                className="flex items-center gap-2 px-3 py-1.5 bg-dark-700 hover:bg-blue-600 rounded cursor-move transition-colors text-sm"
                              >
                                <span className="text-gray-400">🎯</span>
                                <span className="text-white">{preset.name}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Assets Section (Placeholder) */}
            <div className="border-b border-dark-700">
              <button
                onClick={() => setAssetsExpanded(!assetsExpanded)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-dark-700 transition-colors"
              >
                <div className="flex items-center gap-2">
                  {assetsExpanded ? (
                    <ChevronDownIcon className="h-4 w-4 text-gray-400" />
                  ) : (
                    <ChevronRightIcon className="h-4 w-4 text-gray-400" />
                  )}
                  <span className="text-white font-medium">🖼️ Assets</span>
                </div>
                <span className="text-xs text-gray-500">Coming soon</span>
              </button>

              {assetsExpanded && (
                <div className="bg-dark-900 px-4 py-3">
                  <p className="text-sm text-gray-500">Overlay assets and media files</p>
                </div>
              )}
            </div>
          </div>

          {/* Timeline List at Bottom */}
          <div className="border-t border-dark-700 bg-dark-900 max-h-64 overflow-y-auto">
            <div className="px-4 py-2 border-b border-dark-700">
              <h3 className="text-xs font-semibold text-gray-400 uppercase">Timelines</h3>
            </div>
            {timelines.map((timeline) => (
              <div
                key={timeline.id}
                onClick={() => setSelectedTimeline(timeline)}
                className={`px-4 py-2 cursor-pointer transition-colors ${
                  selectedTimeline?.id === timeline.id
                    ? 'bg-primary-600 text-white'
                    : 'hover:bg-dark-700 text-gray-300'
                }`}
              >
                <div className="text-sm font-medium">{timeline.name}</div>
                <div className="text-xs text-gray-500">{timeline.tracks[0]?.cues.length || 0} cues</div>
              </div>
            ))}
          </div>
        </div>

        {/* Main Timeline Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {selectedTimeline ? (
            <>
              {/* Timeline Header */}
              <div className="px-6 py-4 bg-dark-800 border-b border-dark-700">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-white">{selectedTimeline.name}</h2>
                    <p className="text-sm text-gray-400">{selectedTimeline.description || 'No description'}</p>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-gray-400">
                      <span className="font-semibold">{selectedTimeline.resolution}</span> • {selectedTimeline.fps}fps
                    </span>
                    <label className="flex items-center gap-2 text-gray-300">
                      <input
                        type="checkbox"
                        checked={selectedTimeline.loop}
                        onChange={(e) => {
                          selectedTimeline.loop = e.target.checked;
                          setSelectedTimeline({ ...selectedTimeline });
                        }}
                        className="rounded bg-dark-700 border-dark-600 text-primary-600 focus:ring-primary-500"
                      />
                      Loop
                    </label>
                  </div>
                </div>
              </div>

              {/* Timeline Tracks */}
              <div 
                className="flex-1 overflow-auto p-6 bg-dark-900"
                onDrop={handleDrop}
                onDragOver={handleDragOver}
              >
                {selectedTimeline.tracks.map((track, trackIdx) => (
                  <div key={trackIdx} className="mb-6">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-32 flex items-center gap-2">
                        <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                        <span className="text-white font-medium text-sm uppercase">{track.track_type}</span>
                      </div>
                      <div className="text-xs text-gray-500">{track.cues.length} elements</div>
                    </div>

                    {/* Cues in horizontal timeline */}
                    <div className="flex flex-wrap gap-2 min-h-[100px] bg-dark-800 rounded-lg p-4 border-2 border-dashed border-dark-700">
                      {track.cues.length === 0 ? (
                        <div className="w-full text-center py-8 text-gray-500">
                          <p className="text-sm">Drag cameras or presets here to add cues</p>
                          <p className="text-xs mt-1">Or click cameras in the sidebar</p>
                        </div>
                      ) : (
                        track.cues.map((cue, cueIdx) => (
                          <div
                            key={cueIdx}
                            className="bg-blue-600 rounded-lg p-3 text-white shadow-lg hover:bg-blue-700 transition-colors group relative"
                            style={{ minWidth: `${Math.max(150, cue.duration * 2)}px` }}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex-1">
                                <div className="font-semibold text-sm mb-1">
                                  {getCameraName(cue.action_params.camera_id!)}
                                </div>
                                {cue.action_params.preset_id && (
                                  <div className="text-xs text-blue-200 mb-1">
                                    🎯 {getPresetName(cue.action_params.preset_id)}
                                  </div>
                                )}
                                <div className="text-xs text-blue-200">
                                  {cue.duration}s
                                </div>
                              </div>
                              <button
                                onClick={() => removeCue(trackIdx, cueIdx)}
                                className="opacity-0 group-hover:opacity-100 transition-opacity bg-red-600 hover:bg-red-700 rounded p-1"
                              >
                                <TrashIcon className="h-3 w-3" />
                              </button>
                            </div>

                            {/* Duration Editor */}
                            <div className="mt-2">
                              <input
                                type="number"
                                value={cue.duration}
                                onChange={(e) => {
                                  cue.duration = parseFloat(e.target.value);
                                  setSelectedTimeline({ ...selectedTimeline });
                                }}
                                className="w-20 px-2 py-1 bg-blue-700 border border-blue-500 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                                min="1"
                                step="1"
                              />
                              <span className="text-xs text-blue-200 ml-1">seconds</span>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="text-6xl mb-4">🎬</div>
                <h3 className="text-xl font-semibold text-white mb-2">No Timeline Selected</h3>
                <p className="text-gray-400 mb-4">Select a timeline from the list or create a new one</p>
                <button
                  onClick={() => setShowNewTimelineModal(true)}
                  className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-md font-medium"
                >
                  <PlusIcon className="h-5 w-5 inline mr-2" />
                  Create New Timeline
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* New Timeline Modal */}
      {showNewTimelineModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-dark-800 rounded-lg p-6 w-full max-w-md border border-dark-700">
            <h2 className="text-xl font-bold text-white mb-4">Create New Timeline</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Timeline Name *
                </label>
                <input
                  type="text"
                  value={newTimeline.name}
                  onChange={(e) => setNewTimeline({ ...newTimeline, name: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Multi-Angle Show"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  value={newTimeline.description}
                  onChange={(e) => setNewTimeline({ ...newTimeline, description: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Automated camera switching..."
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Resolution
                  </label>
                  <select
                    value={newTimeline.resolution}
                    onChange={(e) => setNewTimeline({ ...newTimeline, resolution: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="1920x1080">1080p</option>
                    <option value="1280x720">720p</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Frame Rate
                  </label>
                  <select
                    value={newTimeline.fps}
                    onChange={(e) => setNewTimeline({ ...newTimeline, fps: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="30">30 fps</option>
                    <option value="60">60 fps</option>
                  </select>
                </div>
              </div>

              <label className="flex items-center gap-2 text-gray-300">
                <input
                  type="checkbox"
                  checked={newTimeline.loop}
                  onChange={(e) => setNewTimeline({ ...newTimeline, loop: e.target.checked })}
                  className="rounded bg-dark-700 border-dark-600 text-primary-600 focus:ring-primary-500"
                />
                Loop timeline infinitely
              </label>
            </div>

            <div className="flex items-center justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowNewTimelineModal(false)}
                className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-md"
              >
                Cancel
              </button>
              <button
                onClick={createTimeline}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-md"
              >
                Create Timeline
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelineEditor;
