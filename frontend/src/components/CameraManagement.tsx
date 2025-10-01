import React, { useState, useEffect } from 'react';
import { cameraService, CameraWithStatus, CameraCreate } from '../services/cameraService';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  PlayIcon,
  CameraIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

const CameraManagement: React.FC = () => {
  const [cameras, setCameras] = useState<CameraWithStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingCamera, setEditingCamera] = useState<CameraWithStatus | null>(null);
  const [testingCamera, setTestingCamera] = useState<number | null>(null);
  const [showStreamModal, setShowStreamModal] = useState(false);
  const [streamingCamera, setStreamingCamera] = useState<CameraWithStatus | null>(null);
  const [snapshots, setSnapshots] = useState<{[key: number]: string}>({});

  useEffect(() => {
    loadCameras();
  }, []);

  const loadCameras = async () => {
    try {
      const data = await cameraService.getCameras();
      setCameras(data);
      // Load snapshots for online cameras
      loadSnapshots(data);
    } catch (error) {
      console.error('Failed to load cameras:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSnapshots = async (cameraList: CameraWithStatus[]) => {
    const newSnapshots: {[key: number]: string} = {};
    for (const camera of cameraList) {
      if (camera.status === 'online') {
        try {
          const response = await fetch(`http://localhost:8000/api/cameras/${camera.id}/snapshot`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`,
            },
          });
          if (response.ok) {
            const data = await response.json();
            if (data.image_data) {
              newSnapshots[camera.id] = `data:${data.content_type};base64,${data.image_data}`;
            }
          } else {
            console.log(`Snapshot response for camera ${camera.id}:`, response.status, response.statusText);
          }
        } catch (error) {
          console.error(`Failed to load snapshot for camera ${camera.id}:`, error);
        }
      }
    }
    setSnapshots(newSnapshots);
  };

  const handleViewStream = (camera: CameraWithStatus) => {
    setStreamingCamera(camera);
    setShowStreamModal(true);
  };

  const handleAddCamera = async (cameraData: CameraCreate) => {
    try {
      await cameraService.createCamera(cameraData);
      await loadCameras();
      setShowAddModal(false);
    } catch (error) {
      console.error('Failed to add camera:', error);
    }
  };

  const handleUpdateCamera = async (id: number, cameraData: Partial<CameraCreate>) => {
    try {
      await cameraService.updateCamera(id, cameraData);
      await loadCameras();
      setEditingCamera(null);
    } catch (error) {
      console.error('Failed to update camera:', error);
    }
  };

  const handleDeleteCamera = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this camera?')) {
      try {
        await cameraService.deleteCamera(id);
        await loadCameras();
      } catch (error) {
        console.error('Failed to delete camera:', error);
      }
    }
  };

  const handleTestCamera = async (id: number) => {
    setTestingCamera(id);
    try {
      const result = await cameraService.testCameraConnection(id);
      alert(`Test Result: ${result.success ? 'Success' : 'Failed'}\n${result.message}`);
    } catch (error) {
      alert('Test failed: ' + error);
    } finally {
      setTestingCamera(null);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'offline':
        return <XCircleIcon className="h-5 w-5 text-red-500" />;
      case 'error':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />;
      default:
        return <XCircleIcon className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'bg-green-500';
      case 'offline':
        return 'bg-red-500';
      case 'error':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-400">Loading cameras...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Camera Management</h1>
            <p className="mt-2 text-gray-400">Manage your IP cameras and their configurations</p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 transition-colors"
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            Add Camera
          </button>
        </div>
      </div>

      {cameras.length === 0 ? (
        <div className="bg-dark-800 rounded-lg p-8 border border-dark-700 text-center">
          <CameraIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No cameras configured</h3>
          <p className="text-gray-400 mb-4">Get started by adding your first camera</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 transition-colors"
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            Add Camera
          </button>
        </div>
      ) : (
        <div className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-dark-700">
              <thead className="bg-dark-700">
                <tr>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Preview
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Camera
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Address
                  </th>
                  <th className="px-3 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-3 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-dark-800 divide-y divide-dark-700">
                {cameras.map((camera) => (
                  <tr key={camera.id} className="hover:bg-dark-700">
                    <td className="px-3 py-3 whitespace-nowrap">
                      <div className="flex items-center justify-center">
                        {snapshots[camera.id] ? (
                          <img
                            src={snapshots[camera.id]}
                            alt={`${camera.name} snapshot`}
                            className="h-14 w-20 object-cover rounded border cursor-pointer hover:opacity-80 transition-opacity"
                            onClick={() => handleViewStream(camera)}
                            title="Click to view live stream"
                          />
                        ) : camera.status === 'online' ? (
                          <div className="h-14 w-20 bg-dark-600 rounded border flex items-center justify-center cursor-pointer hover:bg-dark-500"
                               onClick={() => handleViewStream(camera)}
                               title="Click to view live stream">
                            <CameraIcon className="h-7 w-7 text-gray-400" />
                          </div>
                        ) : (
                          <div className="h-14 w-20 bg-dark-700 rounded border flex items-center justify-center">
                            <XCircleIcon className="h-7 w-7 text-red-400" />
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex items-start">
                        <CameraIcon className="h-5 w-5 text-gray-400 mr-2 mt-0.5 flex-shrink-0" />
                        <div className="min-w-0">
                          <button
                            onClick={() => handleViewStream(camera)}
                            className="text-sm font-medium text-white hover:text-primary-400 transition-colors cursor-pointer block truncate"
                            disabled={camera.status !== 'online'}
                            title={camera.status === 'online' ? 'Click to view live stream' : 'Camera offline'}
                          >
                            {camera.name}
                          </button>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-gray-400">{camera.protocol.toUpperCase()}</span>
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary-900 text-primary-300">
                              {camera.type === 'ptz' ? 'PTZ' : 'STATIONARY'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3 text-sm text-gray-300">
                      <div className="truncate max-w-[180px]" title={`${camera.address}:${camera.port}`}>
                        {camera.address}:{camera.port}
                      </div>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <div className="flex items-center justify-center" title={camera.last_seen ? `Last seen: ${new Date(camera.last_seen).toLocaleString()}` : 'Never seen'}>
                        {getStatusIcon(camera.status)}
                      </div>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end space-x-2">
                        <button
                          onClick={() => handleTestCamera(camera.id)}
                          disabled={testingCamera === camera.id}
                          className="text-primary-600 hover:text-primary-500 disabled:opacity-50"
                          title="Test Connection"
                        >
                          {testingCamera === camera.id ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
                          ) : (
                            <PlayIcon className="h-4 w-4" />
                          )}
                        </button>
                        <button
                          onClick={() => setEditingCamera(camera)}
                          className="text-yellow-600 hover:text-yellow-500"
                          title="Edit"
                        >
                          <PencilIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteCamera(camera.id)}
                          className="text-red-600 hover:text-red-500"
                          title="Delete"
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
        </div>
      )}

      {/* Add Camera Modal */}
      {showAddModal && (
        <AddCameraModal
          onClose={() => setShowAddModal(false)}
          onSave={handleAddCamera}
        />
      )}

      {/* Edit Camera Modal */}
      {editingCamera && (
        <EditCameraModal
          camera={editingCamera}
          onClose={() => setEditingCamera(null)}
          onSave={(data) => handleUpdateCamera(editingCamera.id, data)}
        />
      )}

      {/* Stream Viewing Modal */}
      {showStreamModal && streamingCamera && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" onClick={() => setShowStreamModal(false)} />
            
            <div className="inline-block align-bottom bg-dark-900 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
              <div className="bg-dark-900 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg leading-6 font-medium text-white">
                    Live Stream: {streamingCamera.name}
                  </h3>
                  <button
                    onClick={() => setShowStreamModal(false)}
                    className="text-gray-400 hover:text-white"
                  >
                    <XCircleIcon className="h-6 w-6" />
                  </button>
                </div>
                
                <div className="bg-black rounded-lg p-4">
                  {streamingCamera.status === 'online' ? (
                    <div className="text-center">
                      <div className="bg-dark-800 rounded-lg p-8 mb-4">
                        <CameraIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                        <h4 className="text-white text-lg mb-2">RTSP Stream Available</h4>
                        <p className="text-gray-400 mb-4">
                          Use VLC or another RTSP player to view the live stream:
                        </p>
                        <div className="bg-dark-700 rounded p-3 text-sm font-mono text-primary-400 break-all">
                          rtsp://{streamingCamera.username}:***@{streamingCamera.address}:{streamingCamera.port}{streamingCamera.stream_path}
                        </div>
                        <p className="text-gray-500 text-xs mt-2">
                          * Password hidden for security
                        </p>
                      </div>
                      {snapshots[streamingCamera.id] && (
                        <div>
                          <h5 className="text-white text-sm mb-2">Latest Snapshot:</h5>
                          <img
                            src={snapshots[streamingCamera.id]}
                            alt={`${streamingCamera.name} snapshot`}
                            className="max-w-full h-auto rounded border mx-auto"
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <XCircleIcon className="h-16 w-16 text-red-400 mx-auto mb-4" />
                      <h4 className="text-white text-lg mb-2">Camera Offline</h4>
                      <p className="text-gray-400">
                        This camera is currently offline and cannot stream.
                      </p>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="bg-dark-800 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  onClick={() => setShowStreamModal(false)}
                  className="w-full inline-flex justify-center rounded-md border border-gray-600 shadow-sm px-4 py-2 bg-dark-700 text-base font-medium text-gray-300 hover:bg-dark-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:w-auto sm:text-sm"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Add Camera Modal Component
const AddCameraModal: React.FC<{
  onClose: () => void;
  onSave: (camera: CameraCreate) => void;
}> = ({ onClose, onSave }) => {
  const [formData, setFormData] = useState<CameraCreate>({
    name: '',
    type: 'stationary',
    protocol: 'rtsp',
    address: '',
    username: '',
    password: '',
    port: 554,
    stream_path: '/stream1',
    snapshot_url: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 bg-dark-900 bg-opacity-75 transition-opacity" onClick={onClose}></div>
        
        <div className="inline-block align-bottom bg-dark-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <form onSubmit={handleSubmit}>
            <div className="bg-dark-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
              <h3 className="text-lg font-medium text-white mb-4">Add New Camera</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Name</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Camera Name"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Type</label>
                    <select
                      value={formData.type}
                      onChange={(e) => setFormData({ ...formData, type: e.target.value as 'stationary' | 'ptz' })}
                      className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    >
                      <option value="stationary">Stationary</option>
                      <option value="ptz">PTZ</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Protocol</label>
                    <select
                      value={formData.protocol}
                      onChange={(e) => setFormData({ ...formData, protocol: e.target.value as 'rtsp' | 'rtmp' })}
                      className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    >
                      <option value="rtsp">RTSP</option>
                      <option value="rtmp">RTMP</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Address</label>
                  <input
                    type="text"
                    required
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="192.168.1.100"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Username</label>
                    <input
                      type="text"
                      value={formData.username || ''}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      placeholder="admin"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Password</label>
                    <input
                      type="password"
                      value={formData.password || ''}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      placeholder="password"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Port</label>
                    <input
                      type="number"
                      value={formData.port}
                      onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Stream Path</label>
                    <input
                      type="text"
                      value={formData.stream_path}
                      onChange={(e) => setFormData({ ...formData, stream_path: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Snapshot URL (Optional)</label>
                  <input
                    type="text"
                    value={formData.snapshot_url || ''}
                    onChange={(e) => setFormData({ ...formData, snapshot_url: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="http://192.168.1.100/snapshot.jpg"
                  />
                </div>
              </div>
            </div>

            <div className="bg-dark-700 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
              <button
                type="submit"
                className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-primary-600 text-base font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:ml-3 sm:w-auto sm:text-sm"
              >
                Add Camera
              </button>
              <button
                type="button"
                onClick={onClose}
                className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-600 shadow-sm px-4 py-2 bg-dark-800 text-base font-medium text-gray-300 hover:bg-dark-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
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

// Edit Camera Modal Component
const EditCameraModal: React.FC<{
  camera: CameraWithStatus;
  onClose: () => void;
  onSave: (camera: Partial<CameraCreate>) => void;
}> = ({ camera, onClose, onSave }) => {
  const [formData, setFormData] = useState<Partial<CameraCreate>>({
    name: camera.name,
    type: camera.type,
    protocol: camera.protocol,
    address: camera.address,
    username: camera.username,
    port: camera.port,
    stream_path: camera.stream_path,
    snapshot_url: camera.snapshot_url,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 bg-dark-900 bg-opacity-75 transition-opacity" onClick={onClose}></div>
        
        <div className="inline-block align-bottom bg-dark-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <form onSubmit={handleSubmit}>
            <div className="bg-dark-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
              <h3 className="text-lg font-medium text-white mb-4">Edit Camera</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Name</label>
                  <input
                    type="text"
                    required
                    value={formData.name || ''}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Type</label>
                    <select
                      value={formData.type || 'stationary'}
                      onChange={(e) => setFormData({ ...formData, type: e.target.value as 'stationary' | 'ptz' })}
                      className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    >
                      <option value="stationary">Stationary</option>
                      <option value="ptz">PTZ</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Protocol</label>
                    <select
                      value={formData.protocol || 'rtsp'}
                      onChange={(e) => setFormData({ ...formData, protocol: e.target.value as 'rtsp' | 'rtmp' })}
                      className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    >
                      <option value="rtsp">RTSP</option>
                      <option value="rtmp">RTMP</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Address</label>
                  <input
                    type="text"
                    required
                    value={formData.address || ''}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Username</label>
                    <input
                      type="text"
                      value={formData.username || ''}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Password</label>
                    <input
                      type="password"
                      value={formData.password || ''}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      placeholder="Leave blank to keep current"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Port</label>
                    <input
                      type="number"
                      value={formData.port || 554}
                      onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Stream Path</label>
                    <input
                      type="text"
                      value={formData.stream_path || ''}
                      onChange={(e) => setFormData({ ...formData, stream_path: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Snapshot URL (Optional)</label>
                  <input
                    type="text"
                    value={formData.snapshot_url || ''}
                    onChange={(e) => setFormData({ ...formData, snapshot_url: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-600 rounded-md bg-dark-700 text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              </div>
            </div>

            <div className="bg-dark-700 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
              <button
                type="submit"
                className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-primary-600 text-base font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:ml-3 sm:w-auto sm:text-sm"
              >
                Save Changes
              </button>
              <button
                type="button"
                onClick={onClose}
                className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-600 shadow-sm px-4 py-2 bg-dark-800 text-base font-medium text-gray-300 hover:bg-dark-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
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

export default CameraManagement;
