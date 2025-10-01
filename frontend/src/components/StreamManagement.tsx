import React, { useState, useEffect } from 'react';
import { streamService, Stream, StreamCreate, StreamStatus } from '../services/streamService';
import { cameraService, CameraWithStatus } from '../services/cameraService';
import {
  PlusIcon,
  TrashIcon,
  PlayIcon,
  StopIcon,
  SignalIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

const StreamManagement: React.FC = () => {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [cameras, setCameras] = useState<CameraWithStatus[]>([]);
  const [streamStatuses, setStreamStatuses] = useState<{[key: number]: StreamStatus}>({});
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    loadData();
    // Refresh status every 2 seconds for running streams
    const interval = setInterval(refreshStreamStatuses, 2000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [streamsData, camerasData] = await Promise.all([
        streamService.getStreams(),
        cameraService.getCameras()
      ]);
      setStreams(streamsData);
      setCameras(camerasData);
      await refreshStreamStatuses();
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const refreshStreamStatuses = async () => {
    try {
      const streamList = await streamService.getStreams();
      const statuses: {[key: number]: StreamStatus} = {};
      
      for (const stream of streamList) {
        if (stream.status !== 'stopped') {
          try {
            const status = await streamService.getStreamStatus(stream.id);
            statuses[stream.id] = status;
          } catch (error) {
            console.error(`Failed to get status for stream ${stream.id}:`, error);
          }
        }
      }
      
      setStreamStatuses(statuses);
    } catch (error) {
      console.error('Failed to refresh stream statuses:', error);
    }
  };

  const handleStartStream = async (streamId: number) => {
    try {
      await streamService.startStream(streamId);
      await loadData();
    } catch (error) {
      console.error('Failed to start stream:', error);
      alert('Failed to start stream. Check console for details.');
    }
  };

  const handleStopStream = async (streamId: number) => {
    try {
      await streamService.stopStream(streamId);
      await loadData();
    } catch (error) {
      console.error('Failed to stop stream:', error);
      alert('Failed to stop stream. Check console for details.');
    }
  };

  const handleDeleteStream = async (streamId: number) => {
    if (window.confirm('Are you sure you want to delete this stream?')) {
      try {
        await streamService.deleteStream(streamId);
        await loadData();
      } catch (error) {
        console.error('Failed to delete stream:', error);
        alert('Failed to delete stream. Check console for details.');
      }
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <SignalIcon className="h-5 w-5 text-green-500 animate-pulse" />;
      case 'starting':
        return <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-500"></div>;
      case 'stopped':
        return <StopIcon className="h-5 w-5 text-gray-500" />;
      case 'error':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />;
      default:
        return <XCircleIcon className="h-5 w-5 text-gray-500" />;
    }
  };

  const getDestinationBadgeColor = (destination: string) => {
    switch (destination) {
      case 'youtube':
        return 'bg-red-900 text-red-300';
      case 'facebook':
        return 'bg-blue-900 text-blue-300';
      case 'twitch':
        return 'bg-purple-900 text-purple-300';
      default:
        return 'bg-gray-900 text-gray-300';
    }
  };

  const getCameraName = (cameraId: number) => {
    const camera = cameras.find(c => c.id === cameraId);
    return camera ? camera.name : `Camera ${cameraId}`;
  };

  const formatBitrate = (mbps: number) => {
    return `${mbps.toFixed(2)} Mbps`;
  };

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}h ${minutes}m ${secs}s`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Stream Management</h1>
          <p className="text-gray-400 mt-1">Manage your live streams to YouTube, Facebook, and Twitch</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          Add Stream
        </button>
      </div>

      {streams.length === 0 ? (
        <div className="bg-dark-800 rounded-lg border border-dark-700 p-12 text-center">
          <SignalIcon className="h-16 w-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No streams configured</h3>
          <p className="text-gray-400 mb-6">Get started by adding your first stream destination</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            Add Stream
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {streams.map((stream) => {
            const status = streamStatuses[stream.id];
            return (
              <div key={stream.id} className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden">
                <div className="p-5">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getDestinationBadgeColor(stream.destination)}`}>
                          {stream.destination.toUpperCase()}
                        </span>
                        <div className="flex items-center">
                          {getStatusIcon(stream.status)}
                          <span className="ml-1.5 text-sm text-gray-400 capitalize">{stream.status}</span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-300 font-medium">{getCameraName(stream.camera_id)}</p>
                    </div>
                  </div>

                  {/* Metrics */}
                  {status && status.metrics && (
                    <div className="bg-dark-900 rounded p-3 mb-4 space-y-2">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-400">Bitrate:</span>
                        <span className="text-white font-mono">{formatBitrate(status.metrics.bitrate_current)}</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-400">FPS:</span>
                        <span className="text-white font-mono">{status.metrics.framerate_actual.toFixed(1)} / {status.metrics.framerate_target}</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-400">Dropped:</span>
                        <span className={`font-mono ${status.metrics.dropped_frames > 0 ? 'text-yellow-400' : 'text-green-400'}`}>
                          {status.metrics.dropped_frames}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-400">Uptime:</span>
                        <span className="text-white font-mono">{formatUptime(status.metrics.uptime_seconds)}</span>
                      </div>
                    </div>
                  )}

                  {/* Error Message */}
                  {stream.error_message && (
                    <div className="bg-red-900/20 border border-red-700 rounded p-2 mb-4">
                      <p className="text-xs text-red-300">{stream.error_message}</p>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    {stream.status === 'running' || stream.status === 'starting' ? (
                      <button
                        onClick={() => handleStopStream(stream.id)}
                        className="flex-1 inline-flex items-center justify-center px-3 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-red-600 hover:bg-red-700"
                      >
                        <StopIcon className="h-4 w-4 mr-1.5" />
                        Stop
                      </button>
                    ) : (
                      <button
                        onClick={() => handleStartStream(stream.id)}
                        className="flex-1 inline-flex items-center justify-center px-3 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-green-600 hover:bg-green-700"
                      >
                        <PlayIcon className="h-4 w-4 mr-1.5" />
                        Start
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteStream(stream.id)}
                      disabled={stream.status === 'running'}
                      className="px-3 py-2 border border-red-600 rounded-md text-sm font-medium text-red-600 hover:bg-red-600 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                      title={stream.status === 'running' ? 'Stop stream before deleting' : 'Delete stream'}
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Stream Modal */}
      {showAddModal && (
        <AddStreamModal
          cameras={cameras}
          onClose={() => setShowAddModal(false)}
          onSave={async (streamData) => {
            try {
              await streamService.createStream(streamData);
              await loadData();
              setShowAddModal(false);
            } catch (error) {
              console.error('Failed to create stream:', error);
              alert('Failed to create stream. Check console for details.');
            }
          }}
        />
      )}
    </div>
  );
};

// Add Stream Modal Component
const AddStreamModal: React.FC<{
  cameras: CameraWithStatus[];
  onClose: () => void;
  onSave: (stream: StreamCreate) => void;
}> = ({ cameras, onClose, onSave }) => {
  const [formData, setFormData] = useState<StreamCreate>({
    camera_id: cameras[0]?.id || 0,
    destination: 'youtube',
    stream_key: '',
    rtmp_url: 'rtmp://a.rtmp.youtube.com/live2'
  });

  const handleDestinationChange = (destination: 'youtube' | 'facebook' | 'twitch') => {
    const defaultUrls = {
      youtube: 'rtmp://a.rtmp.youtube.com/live2',
      facebook: 'rtmps://live-api-s.facebook.com:443/rtmp/',
      twitch: 'rtmp://live.twitch.tv/app'
    };
    setFormData({ ...formData, destination, rtmp_url: defaultUrls[destination] });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed z-10 inset-0 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 bg-black bg-opacity-75 transition-opacity"></div>

        <div className="inline-block align-bottom bg-dark-900 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <form onSubmit={handleSubmit}>
            <div className="bg-dark-900 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
              <h3 className="text-lg leading-6 font-medium text-white mb-4">
                Add New Stream
              </h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Camera
                  </label>
                  <select
                    value={formData.camera_id}
                    onChange={(e) => setFormData({ ...formData, camera_id: parseInt(e.target.value) })}
                    className="w-full bg-dark-800 border border-dark-600 rounded-md py-2 px-3 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                    required
                  >
                    {cameras.map((camera) => (
                      <option key={camera.id} value={camera.id}>
                        {camera.name} ({camera.status})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Destination
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {(['youtube', 'facebook', 'twitch'] as const).map((dest) => (
                      <button
                        key={dest}
                        type="button"
                        onClick={() => handleDestinationChange(dest)}
                        className={`px-4 py-2 rounded-md text-sm font-medium capitalize ${
                          formData.destination === dest
                            ? 'bg-primary-600 text-white'
                            : 'bg-dark-800 text-gray-300 hover:bg-dark-700'
                        }`}
                      >
                        {dest}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Stream Key
                  </label>
                  <input
                    type="text"
                    value={formData.stream_key}
                    onChange={(e) => setFormData({ ...formData, stream_key: e.target.value })}
                    className="w-full bg-dark-800 border border-dark-600 rounded-md py-2 px-3 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono text-sm"
                    placeholder="Enter your stream key"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Get this from your {formData.destination} streaming dashboard
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    RTMP URL
                  </label>
                  <input
                    type="text"
                    value={formData.rtmp_url}
                    onChange={(e) => setFormData({ ...formData, rtmp_url: e.target.value })}
                    className="w-full bg-dark-800 border border-dark-600 rounded-md py-2 px-3 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono text-sm"
                    required
                  />
                </div>
              </div>
            </div>

            <div className="bg-dark-800 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse gap-3">
              <button
                type="submit"
                className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-primary-600 text-base font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:w-auto sm:text-sm"
              >
                Add Stream
              </button>
              <button
                type="button"
                onClick={onClose}
                className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-600 shadow-sm px-4 py-2 bg-dark-700 text-base font-medium text-gray-300 hover:bg-dark-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:mt-0 sm:w-auto sm:text-sm"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default StreamManagement;
