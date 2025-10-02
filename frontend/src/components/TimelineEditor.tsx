import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { ChevronDownIcon, ChevronRightIcon, PlusIcon, TrashIcon, PlayIcon, StopIcon, XMarkIcon } from '@heroicons/react/24/outline';

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

interface Asset {
  id: number;
  name: string;
  type: string;
  file_path: string | null;
  api_url: string | null;
  api_refresh_interval: number;
  width: number | null;
  height: number | null;
  position_x: number;
  position_y: number;
  opacity: number;
  description: string | null;
  is_active: boolean;
  created_at: string;
  last_updated: string | null;
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
    asset_id?: number;
    transition?: string;
  };
  transition_type: string;
  transition_duration: number;
}

interface Track {
  id?: number;
  track_type: string; // 'video', 'overlay', 'audio'
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

const TRACK_HEIGHT = 80; // Height of each track in pixels
const MIN_ZOOM = 10; // Minimum pixels per second
const MAX_ZOOM = 200; // Maximum pixels per second

const TimelineEditor: React.FC = () => {
  const [timelines, setTimelines] = useState<Timeline[]>([]);
  const [selectedTimeline, setSelectedTimeline] = useState<Timeline | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [selectedDestinations, setSelectedDestinations] = useState<number[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [showNewTimelineModal, setShowNewTimelineModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [starting, setStarting] = useState(false);
  const [showProgramMonitor, setShowProgramMonitor] = useState(true);

  // Drag/resize state
  const [draggingCue, setDraggingCue] = useState<{ trackIndex: number; cueIndex: number } | null>(null);
  const [resizingCue, setResizingCue] = useState<{ trackIndex: number; cueIndex: number; edge: 'left' | 'right' } | null>(null);
  const [dragStartX, setDragStartX] = useState(0);
  const [dragStartTime, setDragStartTime] = useState(0);
  const timelineRef = useRef<HTMLDivElement>(null);

  // Sidebar collapse states
  const [camerasExpanded, setCamerasExpanded] = useState(true);
  const [assetsExpanded, setAssetsExpanded] = useState(false);
  const [expandedCameras, setExpandedCameras] = useState<Set<number>>(new Set());

  // Playhead and zoom controls
  const [playheadTime, setPlayheadTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(40); // pixels per second (default 40)
  const playIntervalRef = useRef<NodeJS.Timeout | null>(null);

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
    const loadAllData = async () => {
      setLoading(true);
      await Promise.all([
        loadTimelines(),
        loadCameras(),
        loadPresets(),
        loadAssets(),
        loadDestinations()
      ]);
      setLoading(false);
    };
    loadAllData();
  }, []);

  // Playback preview
  useEffect(() => {
    if (isPlaying && selectedTimeline) {
      playIntervalRef.current = setInterval(() => {
        setPlayheadTime((prev) => {
          const next = prev + 0.1;
          if (next >= selectedTimeline.duration) {
            if (selectedTimeline.loop) {
              return 0;
            } else {
              setIsPlaying(false);
              return selectedTimeline.duration;
            }
          }
          return next;
        });
      }, 100); // Update every 100ms for smooth playback
    } else {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
        playIntervalRef.current = null;
      }
    }

    return () => {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
      }
    };
  }, [isPlaying, selectedTimeline]);

  useEffect(() => {
    // Add global mouse move and mouse up listeners for drag/resize
    const handleMouseMove = (e: MouseEvent) => {
      if (draggingCue && selectedTimeline) {
        handleCueDrag(e);
      } else if (resizingCue && selectedTimeline) {
        handleCueResize(e);
      }
    };

    const handleMouseUp = () => {
      setDraggingCue(null);
      setResizingCue(null);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [draggingCue, resizingCue, selectedTimeline]);

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

  const loadAssets = async () => {
    try {
      const response = await axios.get('/api/assets/');
      setAssets(response.data);
    } catch (error) {
      console.error('Failed to load assets:', error);
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

  const getPresetsForCamera = (cameraId: number) => {
    return presets.filter(p => p.camera_id === cameraId);
  };

  const getCameraById = (cameraId: number) => {
    return cameras.find(c => c.id === cameraId);
  };

  const getPresetById = (presetId: number) => {
    return presets.find(p => p.id === presetId);
  };

  const getAssetById = (assetId: number) => {
    return assets.find(a => a.id === assetId);
  };

  const toggleCameraExpand = (cameraId: number) => {
    const newExpanded = new Set(expandedCameras);
    if (newExpanded.has(cameraId)) {
      newExpanded.delete(cameraId);
    } else {
      newExpanded.add(cameraId);
    }
    setExpandedCameras(newExpanded);
  };

  const addCueToTimeline = (trackIndex: number, camera: Camera, preset?: Preset) => {
    if (!selectedTimeline) return;

    const track = selectedTimeline.tracks[trackIndex];
    const lastCue = track.cues[track.cues.length - 1];
    const newStartTime = lastCue ? lastCue.start_time + lastCue.duration : 0;

    const newCue: Cue = {
      cue_order: track.cues.length,
      start_time: newStartTime,
      duration: 10,
      action_type: 'camera_switch',
      action_params: {
        camera_id: camera.id,
        preset_id: preset?.id,
        transition: 'cut'
      },
      transition_type: 'cut',
      transition_duration: 0
    };

    track.cues.push(newCue);
    setSelectedTimeline({ ...selectedTimeline });
  };

  const removeCue = (trackIndex: number, cueIndex: number) => {
    if (!selectedTimeline) return;
    selectedTimeline.tracks[trackIndex].cues.splice(cueIndex, 1);
    setSelectedTimeline({ ...selectedTimeline });
  };

  const handleCueMouseDown = (e: React.MouseEvent, trackIndex: number, cueIndex: number, edge?: 'left' | 'right') => {
    e.stopPropagation();
    
    if (!selectedTimeline) return;
    const cue = selectedTimeline.tracks[trackIndex].cues[cueIndex];

    if (edge) {
      // Start resizing
      setResizingCue({ trackIndex, cueIndex, edge });
      setDragStartX(e.clientX);
      setDragStartTime(edge === 'left' ? cue.start_time : cue.start_time + cue.duration);
    } else {
      // Start dragging
      setDraggingCue({ trackIndex, cueIndex });
      setDragStartX(e.clientX);
      setDragStartTime(cue.start_time);
    }
  };

  const handleCueDrag = (e: MouseEvent) => {
    if (!draggingCue || !selectedTimeline) return;

    const deltaX = e.clientX - dragStartX;
    const deltaTime = deltaX / zoomLevel;
    let newStartTime = Math.max(0, dragStartTime + deltaTime);

    // Snap to grid (0.5 second intervals)
    newStartTime = Math.round(newStartTime * 2) / 2;

    const cue = selectedTimeline.tracks[draggingCue.trackIndex].cues[draggingCue.cueIndex];
    cue.start_time = newStartTime;
    
    setSelectedTimeline({ ...selectedTimeline });
  };

  const handleCueResize = (e: MouseEvent) => {
    if (!resizingCue || !selectedTimeline) return;

    const deltaX = e.clientX - dragStartX;
    const deltaTime = deltaX / zoomLevel;
    const cue = selectedTimeline.tracks[resizingCue.trackIndex].cues[resizingCue.cueIndex];

    if (resizingCue.edge === 'left') {
      // Resize from left (change start_time and duration)
      let newStartTime = Math.max(0, dragStartTime + deltaTime);
      newStartTime = Math.round(newStartTime * 2) / 2;
      const endTime = cue.start_time + cue.duration;
      cue.start_time = newStartTime;
      cue.duration = Math.max(1, endTime - newStartTime);
    } else {
      // Resize from right (change duration)
      let newDuration = cue.duration + deltaTime;
      newDuration = Math.round(newDuration * 2) / 2;
      cue.duration = Math.max(1, newDuration);
    }

    setSelectedTimeline({ ...selectedTimeline });
  };

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(MAX_ZOOM, prev + 10));
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(MIN_ZOOM, prev - 10));
  };

  const togglePlayback = () => {
    setIsPlaying(!isPlaying);
  };

  const stopPlayback = () => {
    setIsPlaying(false);
    setPlayheadTime(0);
  };

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (draggingCue || resizingCue) return;
    
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickTime = clickX / zoomLevel;
    
    setPlayheadTime(Math.max(0, Math.min(selectedTimeline?.duration || 0, clickTime)));
  };

  const addTrack = (trackType: 'video' | 'overlay' | 'audio') => {
    if (!selectedTimeline) return;

    const newTrack: Track = {
      track_type: trackType,
      layer: selectedTimeline.tracks.length,
      is_enabled: true,
      cues: []
    };

    selectedTimeline.tracks.push(newTrack);
    setSelectedTimeline({ ...selectedTimeline });
  };

  const removeTrack = (trackIndex: number) => {
    if (!selectedTimeline) return;
    if (selectedTimeline.tracks.length === 1) {
      alert('Cannot remove the last track!');
      return;
    }
    selectedTimeline.tracks.splice(trackIndex, 1);
    setSelectedTimeline({ ...selectedTimeline });
  };

  const saveTimeline = async () => {
    if (!selectedTimeline || !selectedTimeline.id) return;

    setSaving(true);
    try {
      await axios.put(`/api/timelines/${selectedTimeline.id}`, selectedTimeline);
      alert('✅ Timeline saved successfully!');
      loadTimelines();
    } catch (error: any) {
      console.error('Failed to save timeline:', error);
      alert(`❌ Failed to save timeline:\n${error.response?.data?.detail || error.message || 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  const startTimeline = async () => {
    if (!selectedTimeline || !selectedTimeline.id || selectedDestinations.length === 0) {
      alert('⚠️  Please select a timeline and at least one destination');
      return;
    }

    // Check if timeline has cues
    const hasCues = selectedTimeline.tracks.some(t => t.cues.length > 0);
    if (!hasCues) {
      alert('⚠️  Timeline has no cues!\n\nDrag cameras or presets from the sidebar to add cues to your timeline.');
      return;
    }

    setStarting(true);
    try {
      // First, try to stop the timeline if it's already running
      try {
        await axios.post(`/api/timeline-execution/stop/${selectedTimeline.id}`);
        console.log('🛑 Stopped existing timeline instance');
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
      const destNames = response.data.destinations.join(', ');
      const totalCues = selectedTimeline.tracks.reduce((sum, t) => sum + t.cues.length, 0);
      alert(`🎉 Timeline started!\n\n📡 Streaming to: ${destNames}\n🎬 ${totalCues} cues will execute`);
    } catch (error: any) {
      console.error('Failed to start timeline:', error);
      alert(`❌ Failed to start timeline:\n${error.response?.data?.detail || error.message || 'Unknown error'}`);
    } finally {
      setStarting(false);
    }
  };

  const stopTimeline = async () => {
    if (!selectedTimeline || !selectedTimeline.id) return;

    try {
      await axios.post(`/api/timeline-execution/stop/${selectedTimeline.id}`);
      setIsRunning(false);
      alert('Timeline stopped');
    } catch (error) {
      console.error('Failed to stop timeline:', error);
      alert('Failed to stop timeline');
    }
  };

  const createNewTimeline = async () => {
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

  const handleDrop = (e: React.DragEvent, trackIndex: number) => {
    e.preventDefault();
    const data = JSON.parse(e.dataTransfer.getData('application/json'));
    
    if (data.type === 'camera') {
      const camera = cameras.find(c => c.id === data.cameraId);
      if (camera) {
        addCueToTimeline(trackIndex, camera);
      }
    } else if (data.type === 'preset') {
      const preset = presets.find(p => p.id === data.presetId);
      const camera = cameras.find(c => c.id === data.cameraId);
      if (camera && preset) {
        addCueToTimeline(trackIndex, camera, preset);
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleTrackDrop = (e: React.DragEvent, trackIndex: number, dropTime: number) => {
    e.preventDefault();
    e.stopPropagation();
    
    const data = JSON.parse(e.dataTransfer.getData('application/json'));
    
    if (!selectedTimeline) return;

    const track = selectedTimeline.tracks[trackIndex];
    
    if (data.type === 'camera') {
      const camera = cameras.find(c => c.id === data.cameraId);
      if (camera) {
        const newCue: Cue = {
          cue_order: track.cues.length,
          start_time: Math.max(0, Math.round(dropTime * 2) / 2),
          duration: 10,
          action_type: 'camera_switch',
          action_params: {
            camera_id: camera.id,
            transition: 'cut'
          },
          transition_type: 'cut',
          transition_duration: 0
        };
        track.cues.push(newCue);
        setSelectedTimeline({ ...selectedTimeline });
      }
    } else if (data.type === 'preset') {
      const preset = presets.find(p => p.id === data.presetId);
      const camera = cameras.find(c => c.id === data.cameraId);
      if (camera && preset) {
        const newCue: Cue = {
          cue_order: track.cues.length,
          start_time: Math.max(0, Math.round(dropTime * 2) / 2),
          duration: 10,
          action_type: 'camera_switch',
          action_params: {
            camera_id: camera.id,
            preset_id: preset.id,
            transition: 'cut'
          },
          transition_type: 'cut',
          transition_duration: 0
        };
        track.cues.push(newCue);
        setSelectedTimeline({ ...selectedTimeline });
      }
    } else if (data.type === 'asset') {
      const asset = assets.find(a => a.id === data.assetId);
      if (asset) {
        const newCue: Cue = {
          cue_order: track.cues.length,
          start_time: Math.max(0, Math.round(dropTime * 2) / 2),
          duration: 10,
          action_type: 'overlay',
          action_params: {
            asset_id: asset.id,
            transition: 'fade'
          },
          transition_type: 'fade',
          transition_duration: 0.5
        };
        track.cues.push(newCue);
        setSelectedTimeline({ ...selectedTimeline });
      }
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms}`;
  };

  const getCurrentCues = () => {
    if (!selectedTimeline) return [];
    
    const currentCues: Array<{ cue: Cue; trackIndex: number; track: Track }> = [];
    
    selectedTimeline.tracks.forEach((track, trackIndex) => {
      track.cues.forEach((cue) => {
        const cueStart = cue.start_time;
        const cueEnd = cue.start_time + cue.duration;
        
        if (playheadTime >= cueStart && playheadTime <= cueEnd) {
          currentCues.push({ cue, trackIndex, track });
        }
      });
    });
    
    // Sort by track type priority: video first, then overlays, then audio
    return currentCues.sort((a, b) => {
      const priority: Record<string, number> = { video: 0, overlay: 1, audio: 2 };
      return (priority[a.track.track_type] || 99) - (priority[b.track.track_type] || 99);
    });
  };

  const getTrackColor = (trackType: string) => {
    switch (trackType) {
      case 'video': return 'bg-blue-600';
      case 'overlay': return 'bg-purple-600';
      case 'audio': return 'bg-green-600';
      default: return 'bg-gray-600';
    }
  };

  const getTrackIcon = (trackType: string) => {
    switch (trackType) {
      case 'video': return '🎥';
      case 'overlay': return '🎨';
      case 'audio': return '🔊';
      default: return '📹';
    }
  };

  const renderTimeRuler = () => {
    if (!selectedTimeline) return null;

    const marks = [];
    const duration = selectedTimeline.duration;
    const interval = zoomLevel < 20 ? 10 : zoomLevel < 40 ? 5 : 1;
    
    for (let i = 0; i <= duration; i += interval) {
      marks.push(
        <div key={i} className="absolute flex flex-col items-center" style={{ left: `${i * zoomLevel}px` }}>
          <div className="w-px h-3 bg-gray-500"></div>
          <span className="text-xs text-gray-400 mt-1">{i}s</span>
        </div>
      );
    }

    return (
      <div 
        className="relative h-8 bg-dark-800 border-b border-dark-700 cursor-pointer" 
        style={{ width: `${duration * zoomLevel}px` }}
        onClick={handleTimelineClick}
      >
        {marks}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-dark-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-500 mb-4 mx-auto"></div>
          <p className="text-gray-400">Loading timeline editor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-dark-900">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-6 py-4 bg-dark-800 border-b border-dark-700">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-white">🎬 Timeline Editor</h1>
          {selectedTimeline && (
            <span className="text-gray-400">| {selectedTimeline.name} • {selectedTimeline.resolution} • {selectedTimeline.fps}fps {selectedTimeline.loop && '• Loop'}</span>
          )}
        </div>
        
        <div className="flex items-center gap-4">
          <button
            onClick={() => setShowNewTimelineModal(true)}
            className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-md transition-colors"
          >
            + New Timeline
          </button>
          
          {selectedTimeline && (
            <>
              <button
                onClick={saveTimeline}
                disabled={saving}
                className={`px-4 py-2 rounded-md text-white font-medium transition-colors ${
                  saving
                    ? 'bg-gray-600 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {saving ? '💾 Saving...' : '💾 Save'}
              </button>
              
              <div className="flex items-center gap-2">
                <select
                  multiple
                  value={selectedDestinations.map(String)}
                  onChange={(e) => setSelectedDestinations(Array.from(e.target.selectedOptions, option => Number(option.value)))}
                  className="px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm"
                  style={{ minWidth: '200px', height: '42px' }}
                >
                  {destinations.map((dest) => (
                    <option key={dest.id} value={dest.id}>
                      {dest.platform === 'youtube' && '📺'}
                      {dest.platform === 'facebook' && '👥'}
                      {dest.platform === 'twitch' && '🟣'}
                      {dest.platform === 'custom' && '🔗'}
                      {' '}{dest.name}
                    </option>
                  ))}
                </select>
                
                {!isRunning ? (
                  <button
                    onClick={startTimeline}
                    disabled={starting || selectedDestinations.length === 0}
                    className={`px-6 py-2 rounded-md font-semibold transition-colors ${
                      starting || selectedDestinations.length === 0
                        ? 'bg-gray-600 cursor-not-allowed text-gray-400'
                        : 'bg-green-600 hover:bg-green-700 text-white'
                    }`}
                    title={selectedDestinations.length === 0 ? 'Select a destination first' : 'Start timeline playback'}
                  >
                    {starting ? '⏳ Starting...' : '▶️ Start'}
                  </button>
                ) : (
                  <button
                    onClick={stopTimeline}
                    className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md font-semibold animate-pulse"
                    title="Stop timeline playback"
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
        {/* Left Sidebar - Asset Palette */}
        <div className="w-80 bg-dark-800 border-r border-dark-700 flex flex-col">
          {/* Cameras Section */}
          <div className="border-b border-dark-700">
            <button
              onClick={() => setCamerasExpanded(!camerasExpanded)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-dark-700 transition-colors"
            >
              <div className="flex items-center gap-2 text-white font-semibold">
                {camerasExpanded ? <ChevronDownIcon className="h-5 w-5" /> : <ChevronRightIcon className="h-5 w-5" />}
                <span>📷 Cameras ({cameras.length})</span>
              </div>
            </button>
            
            {camerasExpanded && (
              <div className="px-2 pb-2 space-y-1 max-h-96 overflow-y-auto">
                {cameras.map((camera) => {
                  const isPTZ = camera.type === 'ptz';
                  const cameraPresets = isPTZ ? getPresetsForCamera(camera.id) : [];
                  const isExpanded = expandedCameras.has(camera.id);

                  return (
                    <div key={camera.id} className="space-y-1">
                      {/* Camera Card */}
                      <div className="bg-dark-700 rounded-lg overflow-hidden">
                        <div
                          draggable
                          onDragStart={(e) => {
                            e.dataTransfer.setData('application/json', JSON.stringify({ type: 'camera', cameraId: camera.id }));
                          }}
                          className="flex items-center justify-between p-3 hover:bg-dark-600 cursor-move transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-2xl">📹</span>
                            <div>
                              <div className="text-white text-sm font-medium">{camera.name}</div>
                              <div className="text-gray-400 text-xs">{isPTZ ? 'PTZ' : 'Fixed'}</div>
                            </div>
                          </div>
                          
                          {isPTZ && cameraPresets.length > 0 && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleCameraExpand(camera.id);
                              }}
                              className="text-gray-400 hover:text-white p-1"
                            >
                              {isExpanded ? <ChevronDownIcon className="h-4 w-4" /> : <ChevronRightIcon className="h-4 w-4" />}
                            </button>
                          )}
                        </div>

                        {/* Presets List */}
                        {isPTZ && isExpanded && cameraPresets.length > 0 && (
                          <div className="pl-10 pr-2 pb-2 space-y-1">
                            {cameraPresets.map((preset) => (
                              <div
                                key={preset.id}
                                draggable
                                onDragStart={(e) => {
                                  e.dataTransfer.setData('application/json', JSON.stringify({ 
                                    type: 'preset', 
                                    cameraId: camera.id, 
                                    presetId: preset.id 
                                  }));
                                }}
                                className="flex items-center gap-2 px-2 py-1.5 bg-dark-800 hover:bg-dark-600 rounded cursor-move text-sm text-gray-300"
                              >
                                <span>🎯</span>
                                <span>{preset.name}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Assets Section */}
          <div className="border-b border-dark-700">
            <button
              onClick={() => setAssetsExpanded(!assetsExpanded)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-dark-700 transition-colors"
            >
              <div className="flex items-center gap-2 text-white font-semibold">
                {assetsExpanded ? <ChevronDownIcon className="h-5 w-5" /> : <ChevronRightIcon className="h-5 w-5" />}
                <span>🎨 Assets ({assets.length})</span>
              </div>
            </button>
            
            {assetsExpanded && (
              <div className="px-2 pb-2 space-y-1 max-h-96 overflow-y-auto">
                {assets.length === 0 ? (
                  <div className="px-4 py-3 text-gray-400 text-sm">
                    No assets yet. Create assets in Settings → Assets.
                  </div>
                ) : (
                  assets.map((asset) => (
                    <div
                      key={asset.id}
                      draggable
                      onDragStart={(e) => {
                        e.dataTransfer.setData('application/json', JSON.stringify({ type: 'asset', assetId: asset.id }));
                      }}
                      className="bg-dark-700 rounded-lg overflow-hidden hover:bg-dark-600 cursor-move transition-colors"
                    >
                      <div className="flex items-center gap-2 p-3">
                        <span className="text-2xl flex-shrink-0">
                          {asset.type === 'api_image' && '🌐'}
                          {asset.type === 'static_image' && '🖼️'}
                          {asset.type === 'video' && '🎥'}
                          {asset.type === 'graphic' && '🎨'}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="text-white text-sm font-medium truncate">{asset.name}</div>
                          <div className="text-gray-400 text-xs">{asset.type.replace('_', ' ')}</div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Timeline List */}
          <div className="flex-1 overflow-y-auto">
            <div className="px-4 py-3 border-b border-dark-700">
              <h3 className="text-white font-semibold">Timelines</h3>
            </div>
            <div className="p-2 space-y-1">
              {timelines.map((timeline) => (
                <button
                  key={timeline.id}
                  onClick={() => setSelectedTimeline(timeline)}
                  className={`w-full text-left px-3 py-2 rounded transition-colors ${
                    selectedTimeline?.id === timeline.id
                      ? 'bg-primary-600 text-white'
                      : 'text-gray-300 hover:bg-dark-700'
                  }`}
                >
                  {timeline.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Timeline Tracks Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {selectedTimeline ? (
            <>
              {/* Program Monitor - Preview Window */}
              {showProgramMonitor && (
                <div className="bg-dark-800 border-b border-dark-700 pb-6">
                  <div className="flex items-center justify-between px-4 py-2 bg-dark-900 border-b border-dark-700">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-semibold">📺 Program Monitor</span>
                      <span className="text-xs text-gray-400">(Preview Before Streaming)</span>
                    </div>
                    <button
                      onClick={() => setShowProgramMonitor(false)}
                      className="text-gray-400 hover:text-white transition-colors"
                      title="Hide program monitor"
                    >
                      <XMarkIcon className="h-5 w-5" />
                    </button>
                  </div>

                  {/* Preview Frame Container */}
                  <div style={{ padding: '24px' }}>
                    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                      {/* 16:9 Video Preview */}
                      <div 
                        style={{
                          width: '100%',
                          height: '600px',
                          backgroundColor: '#000000',
                          borderRadius: '8px',
                          border: '2px solid #4B5563',
                          position: 'relative',
                          overflow: 'hidden',
                          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)'
                        }}
                      >
                        {(() => {
                          const currentCues = getCurrentCues();
                          const videoCue = currentCues.find(c => c.track.track_type === 'video');
                          const overlayCues = currentCues.filter(c => c.track.track_type === 'overlay');
                          
                          if (!videoCue) {
                            return (
                              <div style={{ position: 'absolute', inset: '0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <div style={{ textAlign: 'center' }}>
                                  <div style={{ fontSize: '96px', marginBottom: '16px' }}>📹</div>
                                  <div style={{ color: '#9CA3AF', fontSize: '20px', fontWeight: '500' }}>No Active Video Source</div>
                                  <div style={{ color: '#6B7280', fontSize: '14px', marginTop: '8px' }}>Move playhead to a video cue or press Preview</div>
                                </div>
                              </div>
                            );
                          }

                          const camera = getCameraById(videoCue.cue.action_params.camera_id || 0);
                          const preset = videoCue.cue.action_params.preset_id ? getPresetById(videoCue.cue.action_params.preset_id) : null;

                          return (
                            <>
                              {/* Base Video Layer */}
                              <div 
                                style={{
                                  position: 'absolute',
                                  inset: '0',
                                  background: 'linear-gradient(to bottom right, rgba(30, 58, 138, 0.3), rgba(37, 99, 235, 0.2))'
                                }}
                              >
                                <div style={{ position: 'absolute', inset: '0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                  <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '72px', marginBottom: '12px' }}>🎥</div>
                                    <div style={{ color: '#FFFFFF', fontSize: '28px', fontWeight: 'bold' }}>{camera?.name || 'Camera'}</div>
                                    {preset && <div style={{ color: '#60A5FA', fontSize: '18px', marginTop: '8px' }}>🎯 {preset.name}</div>}
                                    <div style={{ color: '#9CA3AF', fontSize: '14px', marginTop: '16px', padding: '0 16px' }}>
                                      Live camera feed will appear here when streaming
                                    </div>
                                  </div>
                                </div>
                              </div>

                              {/* Overlay Layers */}
                              {overlayCues.map((overlayCue, idx) => {
                                const asset = getAssetById(overlayCue.cue.action_params.asset_id || 0);
                                if (!asset) return null;

                                return (
                                  <div
                                    key={idx}
                                    style={{
                                      position: 'absolute',
                                      left: `${asset.position_x * 100}%`,
                                      top: `${asset.position_y * 100}%`,
                                      transform: 'translate(-50%, -50%)',
                                      opacity: asset.opacity,
                                      zIndex: 10 + idx,
                                      pointerEvents: 'none'
                                    }}
                                  >
                                    {asset.type === 'api_image' && asset.api_url ? (
                                      <img
                                        src={asset.api_url}
                                        alt={asset.name}
                                        style={{ maxWidth: '448px', maxHeight: '256px', borderRadius: '8px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)' }}
                                        onError={(e) => {
                                          (e.target as HTMLImageElement).style.display = 'none';
                                        }}
                                      />
                                    ) : asset.type === 'static_image' && asset.file_path ? (
                                      <img
                                        src={asset.file_path}
                                        alt={asset.name}
                                        style={{ maxWidth: '448px', maxHeight: '256px', borderRadius: '8px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)' }}
                                        onError={(e) => {
                                          (e.target as HTMLImageElement).style.display = 'none';
                                        }}
                                      />
                                    ) : (
                                      <div style={{ 
                                        backgroundColor: '#9333EA', 
                                        color: '#FFFFFF', 
                                        padding: '12px 24px', 
                                        borderRadius: '8px', 
                                        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
                                        fontSize: '18px',
                                        fontWeight: '500'
                                      }}>
                                        {asset.type === 'api_image' && '🌐 '}
                                        {asset.type === 'static_image' && '🖼️ '}
                                        {asset.type === 'video' && '🎥 '}
                                        {asset.type === 'graphic' && '🎨 '}
                                        {asset.name}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}

                              {/* Timecode Overlay */}
                              <div style={{
                                position: 'absolute',
                                top: '16px',
                                left: '16px',
                                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                color: '#FFFFFF',
                                fontSize: '14px',
                                fontFamily: 'monospace',
                                padding: '6px 12px',
                                borderRadius: '4px'
                              }}>
                                {formatTime(playheadTime)}
                              </div>
                            </>
                          );
                        })()}
                      </div>

                      {/* Warning Message */}
                      <div style={{
                        marginTop: '16px',
                        padding: '16px',
                        backgroundColor: 'rgba(113, 63, 18, 0.2)',
                        border: '1px solid rgba(234, 179, 8, 0.3)',
                        borderRadius: '8px'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                          <span style={{ fontSize: '20px', color: '#EAB308' }}>⚠️</span>
                          <div style={{ flex: '1' }}>
                            <div style={{ color: '#EAB308', fontSize: '14px', fontWeight: '600', marginBottom: '4px' }}>
                              Setup Preview Only
                            </div>
                            <div style={{ color: 'rgba(234, 179, 8, 0.8)', fontSize: '14px' }}>
                              This is a visual preview for timeline configuration. Click the <strong style={{ color: '#FFFFFF' }}>Start</strong> button in the top bar to begin actual streaming to your selected destinations.
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Show Program Monitor Button (if hidden) */}
              {!showProgramMonitor && (
                <div className="px-4 py-2 bg-dark-800 border-b border-dark-700">
                  <button
                    onClick={() => setShowProgramMonitor(true)}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded transition-colors font-medium"
                  >
                    📺 Show Program Monitor
                  </button>
                </div>
              )}

              {/* Track Controls */}
              <div className="flex items-center justify-between gap-2 px-4 py-3 bg-dark-800 border-b border-dark-700">
                <div className="flex items-center gap-2">
                  <span className="text-gray-400 text-sm font-medium">Add Track:</span>
                  <button
                    onClick={() => addTrack('video')}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
                  >
                    🎥 Video
                  </button>
                  <button
                    onClick={() => addTrack('overlay')}
                    className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded transition-colors"
                  >
                    🎨 Overlay
                  </button>
                  <button
                    onClick={() => addTrack('audio')}
                    className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition-colors"
                  >
                    🔊 Audio
                  </button>
                </div>

                {/* Playback Controls */}
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 border-r border-dark-700 pr-3">
                    <button
                      onClick={togglePlayback}
                      className={`px-3 py-1.5 rounded transition-colors ${
                        isPlaying 
                          ? 'bg-yellow-600 hover:bg-yellow-700' 
                          : 'bg-gray-600 hover:bg-gray-700'
                      } text-white text-sm font-medium`}
                      title="Preview playback (Space)"
                    >
                      {isPlaying ? '⏸️ Pause' : '▶️ Preview'}
                    </button>
                    <button
                      onClick={stopPlayback}
                      className="px-3 py-1.5 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded transition-colors"
                      title="Stop and reset"
                    >
                      ⏹️
                    </button>
                    <span className="text-gray-300 text-sm font-mono">
                      {formatTime(playheadTime)} / {formatTime(selectedTimeline.duration)}
                    </span>
                  </div>

                  {/* Zoom Controls */}
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400 text-sm font-medium">Zoom:</span>
                    <button
                      onClick={handleZoomOut}
                      disabled={zoomLevel <= MIN_ZOOM}
                      className="px-2 py-1 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Zoom out (Ctrl + -)"
                    >
                      −
                    </button>
                    <span className="text-gray-300 text-sm font-mono w-16 text-center">
                      {Math.round((zoomLevel / 40) * 100)}%
                    </span>
                    <button
                      onClick={handleZoomIn}
                      disabled={zoomLevel >= MAX_ZOOM}
                      className="px-2 py-1 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Zoom in (Ctrl + +)"
                    >
                      +
                    </button>
                  </div>
                </div>
              </div>

              {/* Timeline Container */}
              <div className="flex-1 flex overflow-hidden">
                {/* Track Labels */}
                <div className="w-40 bg-dark-800 border-r border-dark-700 flex flex-col">
                  <div className="h-8 border-b border-dark-700 flex items-center px-3 text-xs text-gray-400 font-semibold">
                    TRACKS
                  </div>
                  {selectedTimeline.tracks.map((track, trackIndex) => (
                    <div
                      key={trackIndex}
                      className="border-b border-dark-700 flex items-center justify-between px-3 py-2"
                      style={{ height: `${TRACK_HEIGHT}px` }}
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{getTrackIcon(track.track_type)}</span>
                        <span className="text-white text-sm font-medium capitalize">{track.track_type}</span>
                      </div>
                      {selectedTimeline.tracks.length > 1 && (
                        <button
                          onClick={() => removeTrack(trackIndex)}
                          className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                          title="Remove track"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>

                {/* Timeline Grid */}
                <div className="flex-1 overflow-auto" ref={timelineRef}>
                  <div className="min-w-full relative">
                    {/* Time Ruler */}
                    {renderTimeRuler()}
                    
                    {/* Playhead */}
                    <div 
                      className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-50 pointer-events-none"
                      style={{ left: `${playheadTime * zoomLevel}px` }}
                    >
                      <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-4 h-4 bg-red-500" style={{ clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }}></div>
                      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-red-500 text-white text-xs px-1 py-0.5 rounded whitespace-nowrap">
                        {formatTime(playheadTime)}
                      </div>
                    </div>
                    
                    {/* Tracks */}
                    {selectedTimeline.tracks.map((track, trackIndex) => (
                      <div
                        key={trackIndex}
                        className="relative border-b border-dark-700"
                        style={{ 
                          height: `${TRACK_HEIGHT}px`,
                          width: `${selectedTimeline.duration * zoomLevel}px`,
                          backgroundImage: `repeating-linear-gradient(to right, transparent, transparent ${zoomLevel - 1}px, rgba(75, 85, 99, 0.2) ${zoomLevel - 1}px, rgba(75, 85, 99, 0.2) ${zoomLevel}px)`,
                          backgroundSize: `${zoomLevel}px 100%`
                        }}
                        onDrop={(e) => {
                          const rect = e.currentTarget.getBoundingClientRect();
                          const dropX = e.clientX - rect.left;
                          const dropTime = dropX / zoomLevel;
                          handleTrackDrop(e, trackIndex, dropTime);
                        }}
                        onDragOver={handleDragOver}
                      >
                        {track.cues.length === 0 && (
                          <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm pointer-events-none">
                            Drag cameras or presets here
                          </div>
                        )}
                        
                        {/* Cues */}
                        {track.cues.map((cue, cueIndex) => {
                          const camera = getCameraById(cue.action_params.camera_id || 0);
                          const preset = cue.action_params.preset_id ? getPresetById(cue.action_params.preset_id) : null;
                          const asset = cue.action_params.asset_id ? getAssetById(cue.action_params.asset_id) : null;
                          const cueColor = getTrackColor(track.track_type);

                          return (
                            <div
                              key={cueIndex}
                              className={`absolute ${cueColor} text-white rounded border-2 border-white/20 hover:border-white/40 transition-all cursor-move select-none`}
                              style={{
                                left: `${cue.start_time * zoomLevel}px`,
                                width: `${cue.duration * zoomLevel}px`,
                                top: '4px',
                                bottom: '4px',
                                display: 'flex',
                                alignItems: 'center',
                                padding: '0 8px'
                              }}
                              onMouseDown={(e) => handleCueMouseDown(e, trackIndex, cueIndex)}
                            >
                              {/* Left Resize Handle */}
                              <div
                                className="absolute left-0 top-0 bottom-0 w-3 cursor-ew-resize bg-white/10 hover:bg-yellow-400/60 border-r-2 border-white/40 transition-colors z-10"
                                onMouseDown={(e) => handleCueMouseDown(e, trackIndex, cueIndex, 'left')}
                                title="◀ Drag to trim in-point"
                              >
                                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-white/50 rounded-r"></div>
                              </div>
                              
                              {/* Cue Content */}
                              <div className="flex-1 overflow-hidden">
                                <div className="text-xs font-semibold truncate">
                                  {asset ? asset.name : (camera?.name || 'Camera')}
                                </div>
                                {preset && !asset && (
                                  <div className="text-xs opacity-75 truncate">
                                    🎯 {preset.name}
                                  </div>
                                )}
                                {asset && (
                                  <div className="text-xs opacity-75 truncate">
                                    {asset.type === 'api_image' && '🌐'}
                                    {asset.type === 'static_image' && '🖼️'}
                                    {asset.type === 'video' && '🎥'}
                                    {asset.type === 'graphic' && '🎨'}
                                    {' '}{asset.type.replace('_', ' ')}
                                  </div>
                                )}
                                <div className="text-xs opacity-50">
                                  {cue.duration}s
                                </div>
                              </div>

                              {/* Delete Button */}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  removeCue(trackIndex, cueIndex);
                                }}
                                className="ml-2 p-1 hover:bg-white/20 rounded transition-colors"
                                title="Delete cue"
                              >
                                <TrashIcon className="h-3 w-3" />
                              </button>

                              {/* Right Resize Handle */}
                              <div
                                className="absolute right-0 top-0 bottom-0 w-3 cursor-ew-resize bg-white/10 hover:bg-yellow-400/60 border-l-2 border-white/40 transition-colors z-10"
                                onMouseDown={(e) => handleCueMouseDown(e, trackIndex, cueIndex, 'right')}
                                title="▶ Drag to trim out-point"
                              >
                                <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-white/50 rounded-l"></div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              <div className="text-center">
                <p className="text-xl mb-2">No timeline selected</p>
                <p className="text-sm">Select a timeline from the list or create a new one</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* New Timeline Modal */}
      {showNewTimelineModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-dark-800 rounded-lg p-6 w-full max-w-md border border-dark-700">
            <h2 className="text-xl font-bold text-white mb-4">Create New Timeline</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Name</label>
                <input
                  type="text"
                  value={newTimeline.name}
                  onChange={(e) => setNewTimeline({ ...newTimeline, name: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white"
                  placeholder="My Timeline"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Duration (seconds)</label>
                <input
                  type="number"
                  value={newTimeline.duration}
                  onChange={(e) => setNewTimeline({ ...newTimeline, duration: Number(e.target.value) })}
                  className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white"
                />
              </div>

              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-300 mb-2">Resolution</label>
                  <select
                    value={newTimeline.resolution}
                    onChange={(e) => setNewTimeline({ ...newTimeline, resolution: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white"
                  >
                    <option value="1920x1080">1920x1080</option>
                    <option value="1280x720">1280x720</option>
                    <option value="3840x2160">3840x2160</option>
                  </select>
                </div>
                
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-300 mb-2">FPS</label>
                  <select
                    value={newTimeline.fps}
                    onChange={(e) => setNewTimeline({ ...newTimeline, fps: Number(e.target.value) })}
                    className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white"
                  >
                    <option value={24}>24</option>
                    <option value={30}>30</option>
                    <option value={60}>60</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={newTimeline.loop}
                  onChange={(e) => setNewTimeline({ ...newTimeline, loop: e.target.checked })}
                  className="w-4 h-4"
                />
                <label className="text-sm text-gray-300">Loop timeline</label>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowNewTimelineModal(false)}
                className="flex-1 px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-md transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={createNewTimeline}
                disabled={!newTimeline.name}
                className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelineEditor;
