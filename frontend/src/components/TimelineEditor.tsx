import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Camera {
  id: number;
  name: string;
  type: string;
}

interface Cue {
  id?: number;
  cue_order: number;
  start_time: number;
  duration: number;
  action_type: string;
  action_params: {
    camera_id?: number;
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

const TimelineEditor: React.FC = () => {
  const [timelines, setTimelines] = useState<Timeline[]>([]);
  const [selectedTimeline, setSelectedTimeline] = useState<Timeline | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [showNewTimelineModal, setShowNewTimelineModal] = useState(false);
  const [streamKey, setStreamKey] = useState('');

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

  const addCueToTimeline = (camera: Camera) => {
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
        transition: 'cut'
      },
      transition_type: 'cut',
      transition_duration: 0
    };

    videoTrack.cues.push(newCue);
    setSelectedTimeline({ ...selectedTimeline });
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
    if (!selectedTimeline || !selectedTimeline.id || !streamKey) {
      alert('Please select a timeline and enter a stream key');
      return;
    }

    try {
      const outputUrl = `rtmp://a.rtmp.youtube.com/live2/${streamKey}`;
      await axios.post('/api/timeline-execution/start', {
        timeline_id: selectedTimeline.id,
        output_urls: [outputUrl]
      });
      setIsRunning(true);
      alert('Timeline started!');
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
              {cameras.map((camera) => (
                <div
                  key={camera.id}
                  onClick={() => addCueToTimeline(camera)}
                  className="bg-gray-700 hover:bg-gray-600 p-3 rounded cursor-pointer transition-colors"
                >
                  <div className="text-white font-medium">{camera.name}</div>
                  <div className="text-xs text-gray-400 capitalize">{camera.type}</div>
                </div>
              ))}
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
                    <input
                      type="text"
                      placeholder="YouTube Stream Key"
                      value={streamKey}
                      onChange={(e) => setStreamKey(e.target.value)}
                      className="bg-gray-700 text-white px-3 py-2 rounded w-64"
                    />
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
                                {cue.action_type === 'show_camera' &&
                                  getCameraName(cue.action_params.camera_id!)}
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

