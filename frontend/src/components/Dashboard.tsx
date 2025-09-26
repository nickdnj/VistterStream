import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { cameraService, CameraWithStatus } from '../services/cameraService';
import { api } from '../services/api';
import {
  CameraIcon,
  PlayIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';

interface SystemStatus {
  status: string;
  uptime: number;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  active_cameras: number;
  active_streams: number;
}

const Dashboard: React.FC = () => {
  const [cameras, setCameras] = useState<CameraWithStatus[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [camerasData, statusData] = await Promise.all([
        cameraService.getCameras(),
        api.get('/status/system').then(res => res.data)
      ]);
      setCameras(camerasData);
      setSystemStatus(statusData);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
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

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Dashboard</h1>
        <p className="mt-2 text-gray-400">Monitor your streaming appliance status</p>
      </div>

      {/* System Status Cards */}
      {systemStatus && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center">
                  <CameraIcon className="h-5 w-5 text-white" />
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">Active Cameras</p>
                <p className="text-2xl font-bold text-white">{systemStatus.active_cameras}</p>
              </div>
            </div>
          </div>

          <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="h-8 w-8 bg-green-600 rounded-lg flex items-center justify-center">
                  <PlayIcon className="h-5 w-5 text-white" />
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">Active Streams</p>
                <p className="text-2xl font-bold text-white">{systemStatus.active_streams}</p>
              </div>
            </div>
          </div>

          <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="h-8 w-8 bg-yellow-600 rounded-lg flex items-center justify-center">
                  <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">CPU Usage</p>
                <p className="text-2xl font-bold text-white">{systemStatus.cpu_usage.toFixed(1)}%</p>
              </div>
            </div>
          </div>

          <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="h-8 w-8 bg-purple-600 rounded-lg flex items-center justify-center">
                  <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">Uptime</p>
                <p className="text-2xl font-bold text-white">{formatUptime(systemStatus.uptime)}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Cameras Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-white">Cameras</h2>
          <Link
            to="/cameras"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 transition-colors"
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            Add Camera
          </Link>
        </div>

        {cameras.length === 0 ? (
          <div className="bg-dark-800 rounded-lg p-8 border border-dark-700 text-center">
            <CameraIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No cameras configured</h3>
            <p className="text-gray-400 mb-4">Get started by adding your first camera</p>
            <Link
              to="/cameras"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 transition-colors"
            >
              <PlusIcon className="h-4 w-4 mr-2" />
              Add Camera
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cameras.map((camera) => (
              <div key={camera.id} className="bg-dark-800 rounded-lg p-6 border border-dark-700 hover:border-dark-600 transition-colors">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center">
                    {getStatusIcon(camera.status)}
                    <h3 className="ml-2 text-lg font-medium text-white">{camera.name}</h3>
                  </div>
                  <div className={`h-3 w-3 rounded-full ${getStatusColor(camera.status)}`}></div>
                </div>
                
                <div className="space-y-2 text-sm text-gray-400">
                  <p><span className="font-medium">Type:</span> {camera.type.toUpperCase()}</p>
                  <p><span className="font-medium">Protocol:</span> {camera.protocol.toUpperCase()}</p>
                  <p><span className="font-medium">Address:</span> {camera.address}</p>
                  {camera.last_seen && (
                    <p><span className="font-medium">Last seen:</span> {new Date(camera.last_seen).toLocaleString()}</p>
                  )}
                </div>

                {camera.last_error && (
                  <div className="mt-4 p-3 bg-red-900/20 border border-red-500/30 rounded-md">
                    <p className="text-sm text-red-400">{camera.last_error}</p>
                  </div>
                )}

                <div className="mt-4 flex space-x-2">
                  <Link
                    to={`/cameras/${camera.id}`}
                    className="flex-1 text-center px-3 py-2 text-sm font-medium text-primary-600 hover:text-primary-500 transition-colors"
                  >
                    View Details
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
