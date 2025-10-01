import React, { useState, useEffect } from 'react';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  PlayIcon,
  StopIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

interface Stream {
  id: number;
  name: string;
  camera_id: number;
  destination: string;
  stream_key: string;
  rtmp_url: string;
  resolution: string;
  bitrate: string;
  framerate: number;
  status: string;
  is_active: boolean;
  created_at: string;
  started_at?: string;
  stopped_at?: string;
  last_error?: string;
}

interface Camera {
  id: number;
  name: string;
  status: string;
}

const StreamManagement: React.FC = () => {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingStream, setEditingStream] = useState<Stream | null>(null);

  useEffect(() => {
    loadData();
    
    // Auto-refresh every 5 seconds to update stream status
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };
      
      const [streamsRes, camerasRes] = await Promise.all([
        fetch('http://localhost:8000/api/streams/', { headers }),
        fetch('http://localhost:8000/api/cameras/', { headers })
      ]);
      
      if (streamsRes.ok) {
        const streamsData = await streamsRes.json();
        setStreams(streamsData);
      }
      
      if (camerasRes.ok) {
        const camerasData = await camerasRes.json();
        setCameras(camerasData);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartStream = async (streamId: number) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8000/api/streams/${streamId}/start`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        loadData(); // Refresh
      } else {
        const error = await response.json();
        alert(`Failed to start stream: ${error.detail}`);
      }
    } catch (error) {
      console.error('Failed to start stream:', error);
      alert('Failed to start stream');
    }
  };

  const handleStopStream = async (streamId: number) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8000/api/streams/${streamId}/stop`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        loadData(); // Refresh
      } else {
        const error = await response.json();
        alert(`Failed to stop stream: ${error.detail}`);
      }
    } catch (error) {
      console.error('Failed to stop stream:', error);
      alert('Failed to stop stream');
    }
  };

  const handleDeleteStream = async (streamId: number) => {
    if (!window.confirm('Are you sure you want to delete this stream?')) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8000/api/streams/${streamId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        loadData(); // Refresh
      }
    } catch (error) {
      console.error('Failed to delete stream:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'stopped':
        return <XCircleIcon className="h-5 w-5 text-gray-500" />;
      case 'starting':
        return <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-500" />;
      case 'error':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />;
      default:
        return <XCircleIcon className="h-5 w-5 text-gray-500" />;
    }
  };

  const getCameraName = (cameraId: number) => {
    const camera = cameras.find(c => c.id === cameraId);
    return camera ? camera.name : `Camera ${cameraId}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Stream Management</h1>
          <p className="mt-2 text-gray-400">Manage your live streams to YouTube, Facebook, Twitch, and more</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          Add Stream
        </button>
      </div>

      {streams.length === 0 ? (
        <div className="bg-dark-800 rounded-lg p-12 border border-dark-700 text-center">
          <h3 className="text-lg font-medium text-white mb-2">No streams configured</h3>
          <p className="text-gray-400 mb-6">Create your first stream to go live on YouTube, Facebook, or Twitch</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            Create Stream
          </button>
        </div>
      ) : (
        <div className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden">
          <table className="min-w-full divide-y divide-dark-700">
            <thead className="bg-dark-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Stream Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Camera
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Destination
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Quality
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-dark-800 divide-y divide-dark-700">
              {streams.map((stream) => (
                <tr key={stream.id} className="hover:bg-dark-700">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-white">{stream.name}</div>
                    <div className="text-xs text-gray-400">{stream.rtmp_url}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {getCameraName(stream.camera_id)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-900 text-primary-300 uppercase">
                      {stream.destination}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    <div>{stream.resolution} @ {stream.framerate}fps</div>
                    <div className="text-xs text-gray-500">{stream.bitrate}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center justify-center">
                      <div className="flex items-center" title={stream.last_error || stream.status}>
                        {getStatusIcon(stream.status)}
                        <span className="ml-2 text-sm text-gray-300 capitalize">{stream.status}</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end space-x-2">
                      {stream.status === 'running' ? (
                        <button
                          onClick={() => handleStopStream(stream.id)}
                          className="text-red-600 hover:text-red-500"
                          title="Stop Stream"
                        >
                          <StopIcon className="h-5 w-5" />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleStartStream(stream.id)}
                          className="text-green-600 hover:text-green-500"
                          title="Start Stream"
                          disabled={stream.status === 'starting'}
                        >
                          <PlayIcon className="h-5 w-5" />
                        </button>
                      )}
                      <button
                        onClick={() => setEditingStream(stream)}
                        className="text-yellow-600 hover:text-yellow-500"
                        title="Edit"
                        disabled={stream.status === 'running'}
                      >
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteStream(stream.id)}
                        className="text-red-600 hover:text-red-500"
                        title="Delete"
                        disabled={stream.status === 'running'}
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Stream Modal - Simplified for now */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-dark-900 rounded-lg p-6 max-w-2xl w-full mx-4">
            <h2 className="text-xl font-bold text-white mb-4">Add New Stream</h2>
            <p className="text-gray-400 mb-4">
              Use the test script to add streams for now:
              <code className="block mt-2 bg-dark-800 p-3 rounded text-sm text-primary-400">
                python test_youtube_stream.py
              </code>
            </p>
            <p className="text-gray-400 text-sm mb-4">
              Full UI form coming soon!
            </p>
            <button
              onClick={() => setShowAddModal(false)}
              className="px-4 py-2 bg-dark-700 text-white rounded-md hover:bg-dark-600"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default StreamManagement;
