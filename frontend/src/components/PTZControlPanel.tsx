import React, { useState, useEffect, useCallback, useRef } from 'react';
import { cameraService, CameraWithStatus } from '../services/cameraService';
import { ptzService, Preset, PTZStatus } from '../services/ptzService';
import {
  XMarkIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  ArrowUpLeftIcon,
  ArrowUpRightIcon,
  ArrowDownLeftIcon,
  ArrowDownRightIcon,
  StopIcon,
  PlusIcon,
  MagnifyingGlassPlusIcon,
  MagnifyingGlassMinusIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';

interface PTZControlPanelProps {
  camera: CameraWithStatus;
  onClose: () => void;
}

const PTZControlPanel: React.FC<PTZControlPanelProps> = ({ camera, onClose }) => {
  const [liveSnapshot, setLiveSnapshot] = useState<string>('');
  const [presets, setPresets] = useState<Preset[]>([]);
  const [status, setStatus] = useState<PTZStatus | null>(null);
  const [speed, setSpeed] = useState(0.5);
  const [showCapture, setShowCapture] = useState(false);
  const [captureName, setCaptureName] = useState('');
  const [capturing, setCapturing] = useState(false);
  const [movingToPreset, setMovingToPreset] = useState<number | null>(null);
  const [moveFeedback, setMoveFeedback] = useState<string | null>(null);
  const captureInputRef = useRef<HTMLInputElement>(null);

  // Load presets
  const loadPresets = useCallback(async () => {
    try {
      const data = await ptzService.getPresets(camera.id);
      setPresets(data);
    } catch (err) {
      console.error('Failed to load presets:', err);
    }
  }, [camera.id]);

  useEffect(() => {
    loadPresets();
  }, [loadPresets]);

  // Live snapshot polling
  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const data = await cameraService.getCameraSnapshot(camera.id);
        if (active && data?.image_data) {
          setLiveSnapshot(`data:${data.content_type};base64,${data.image_data}`);
        }
      } catch {
        // ignore snapshot errors
      }
    };
    refresh();
    const interval = setInterval(refresh, 500);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [camera.id]);

  // PTZ status polling
  useEffect(() => {
    let active = true;
    const fetchStatus = async () => {
      try {
        const s = await ptzService.getStatus(camera.id);
        if (active) setStatus(s);
      } catch {
        // ignore
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [camera.id]);

  // Focus capture input when shown
  useEffect(() => {
    if (showCapture && captureInputRef.current) {
      captureInputRef.current.focus();
    }
  }, [showCapture]);

  // Movement handlers
  const startMove = async (panSpeed: number, tiltSpeed: number, zoomSpeed: number) => {
    try {
      await ptzService.continuousMove(camera.id, panSpeed * speed, tiltSpeed * speed, zoomSpeed * speed);
    } catch (err) {
      console.error('Move failed:', err);
    }
  };

  const stopMove = async () => {
    try {
      await ptzService.stopMovement(camera.id);
    } catch (err) {
      console.error('Stop failed:', err);
    }
  };

  // Preset handlers
  const handleCapture = async () => {
    if (!captureName.trim()) return;
    setCapturing(true);
    try {
      await ptzService.capturePreset(camera.id, captureName.trim());
      setCaptureName('');
      setShowCapture(false);
      await loadPresets();
    } catch (err) {
      console.error('Capture failed:', err);
    } finally {
      setCapturing(false);
    }
  };

  const handleGoTo = async (preset: Preset) => {
    setMovingToPreset(preset.id);
    setMoveFeedback(`Moving to ${preset.name}...`);
    try {
      await ptzService.moveToPreset(preset.id);
      setMoveFeedback(null);
    } catch (err) {
      console.error('Go To failed:', err);
      setMoveFeedback(null);
    } finally {
      setMovingToPreset(null);
    }
  };

  const handleDelete = async (preset: Preset) => {
    if (!window.confirm(`Delete preset "${preset.name}"?`)) return;
    try {
      await ptzService.deletePreset(preset.id);
      await loadPresets();
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  // D-pad button component
  const DPadButton: React.FC<{
    onStart: () => void;
    children: React.ReactNode;
    className?: string;
    title?: string;
  }> = ({ onStart, children, className = '', title }) => (
    <button
      onPointerDown={(e) => { e.preventDefault(); onStart(); }}
      onPointerUp={stopMove}
      onPointerLeave={stopMove}
      className={`flex items-center justify-center w-12 h-12 rounded-lg bg-dark-600 hover:bg-dark-500 active:bg-primary-600 text-gray-300 active:text-white transition-colors select-none touch-none ${className}`}
      title={title}
    >
      {children}
    </button>
  );

  return (
    <div className="fixed inset-0 z-50 bg-dark-900/95 flex items-center justify-center">
      <div className="w-full max-w-6xl mx-4 bg-dark-800 rounded-xl border border-dark-600 shadow-2xl overflow-hidden max-h-[95vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-dark-600 flex-shrink-0">
          <h2 className="text-xl font-bold text-white">PTZ Control: {camera.name}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {/* Body */}
        <div className="flex flex-col lg:flex-row flex-1 min-h-0 overflow-hidden">
          {/* Left: Live Preview */}
          <div className="lg:w-[65%] p-4 flex flex-col min-h-0">
            <div className="relative bg-black rounded-lg overflow-hidden flex-1 min-h-[300px]">
              {liveSnapshot ? (
                <img
                  src={liveSnapshot}
                  alt={`${camera.name} live`}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-500 mx-auto mb-3"></div>
                    <p className="text-gray-400 text-sm">Loading preview...</p>
                  </div>
                </div>
              )}
              {/* LIVE badge */}
              <div className="absolute top-3 left-3 bg-red-600 text-white text-xs font-bold px-2 py-1 rounded flex items-center">
                <span className="animate-pulse mr-1">●</span> LIVE
              </div>
              {/* Move feedback */}
              {moveFeedback && (
                <div className="absolute bottom-3 left-1/2 -translate-x-1/2 bg-primary-600/90 text-white text-sm font-medium px-4 py-2 rounded-lg">
                  {moveFeedback}
                </div>
              )}
            </div>
          </div>

          {/* Right: Controls & Presets */}
          <div className="lg:w-[35%] border-t lg:border-t-0 lg:border-l border-dark-600 p-4 flex flex-col gap-5 overflow-y-auto min-h-0">
            {/* D-Pad */}
            <div>
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Direction</h3>
              <div className="grid grid-cols-3 gap-1.5 w-fit mx-auto">
                <DPadButton onStart={() => startMove(-1, 1, 0)} title="Up-Left">
                  <ArrowUpLeftIcon className="h-5 w-5" />
                </DPadButton>
                <DPadButton onStart={() => startMove(0, 1, 0)} title="Up">
                  <ArrowUpIcon className="h-5 w-5" />
                </DPadButton>
                <DPadButton onStart={() => startMove(1, 1, 0)} title="Up-Right">
                  <ArrowUpRightIcon className="h-5 w-5" />
                </DPadButton>
                <DPadButton onStart={() => startMove(-1, 0, 0)} title="Left">
                  <ArrowLeftIcon className="h-5 w-5" />
                </DPadButton>
                <DPadButton onStart={stopMove} title="Stop" className="bg-red-900/40 hover:bg-red-800/60 active:bg-red-700">
                  <StopIcon className="h-5 w-5" />
                </DPadButton>
                <DPadButton onStart={() => startMove(1, 0, 0)} title="Right">
                  <ArrowRightIcon className="h-5 w-5" />
                </DPadButton>
                <DPadButton onStart={() => startMove(-1, -1, 0)} title="Down-Left">
                  <ArrowDownLeftIcon className="h-5 w-5" />
                </DPadButton>
                <DPadButton onStart={() => startMove(0, -1, 0)} title="Down">
                  <ArrowDownIcon className="h-5 w-5" />
                </DPadButton>
                <DPadButton onStart={() => startMove(1, -1, 0)} title="Down-Right">
                  <ArrowDownRightIcon className="h-5 w-5" />
                </DPadButton>
              </div>
            </div>

            {/* Zoom */}
            <div>
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Zoom</h3>
              <div className="flex items-center gap-2 justify-center">
                <DPadButton onStart={() => startMove(0, 0, -1)} title="Zoom Out">
                  <MagnifyingGlassMinusIcon className="h-5 w-5" />
                </DPadButton>
                <div className="text-xs text-gray-400 w-16 text-center">
                  {status?.available ? (status.zoom ?? 0).toFixed(2) : '--'}
                </div>
                <DPadButton onStart={() => startMove(0, 0, 1)} title="Zoom In">
                  <MagnifyingGlassPlusIcon className="h-5 w-5" />
                </DPadButton>
              </div>
            </div>

            {/* Speed */}
            <div>
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
                Speed: {speed.toFixed(1)}
              </h3>
              <input
                type="range"
                min={0.1}
                max={1.0}
                step={0.1}
                value={speed}
                onChange={(e) => setSpeed(parseFloat(e.target.value))}
                className="w-full accent-primary-500"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Slow</span>
                <span>Fast</span>
              </div>
            </div>

            {/* Position Readout */}
            <div>
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Position</h3>
              {status?.available ? (
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="bg-dark-700 rounded-lg p-2">
                    <div className="text-xs text-gray-500 uppercase">Pan</div>
                    <div className="text-sm text-white font-mono">{(status.pan ?? 0).toFixed(3)}</div>
                  </div>
                  <div className="bg-dark-700 rounded-lg p-2">
                    <div className="text-xs text-gray-500 uppercase">Tilt</div>
                    <div className="text-sm text-white font-mono">{(status.tilt ?? 0).toFixed(3)}</div>
                  </div>
                  <div className="bg-dark-700 rounded-lg p-2">
                    <div className="text-xs text-gray-500 uppercase">Zoom</div>
                    <div className="text-sm text-white font-mono">{(status.zoom ?? 0).toFixed(3)}</div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-500 text-center">Position unavailable</div>
              )}
            </div>

            {/* Presets */}
            <div className="flex-1 min-h-0 flex flex-col">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
                  Presets ({presets.length})
                </h3>
              </div>

              <div className="flex-1 overflow-y-auto space-y-1.5 min-h-0 max-h-[200px]">
                {presets.length === 0 ? (
                  <div className="text-sm text-gray-500 text-center py-4">No presets saved</div>
                ) : (
                  presets.map((preset) => (
                    <div
                      key={preset.id}
                      className={`flex items-center justify-between bg-dark-700 rounded-lg px-3 py-2 transition-colors ${
                        movingToPreset === preset.id ? 'ring-2 ring-primary-500' : ''
                      }`}
                    >
                      {preset.thumbnail_path ? (
                        <img src={preset.thumbnail_path} alt={preset.name}
                             className="w-10 h-7 rounded object-cover flex-shrink-0" />
                      ) : (
                        <span className="w-10 h-7 rounded bg-dark-600 flex items-center justify-center text-xs flex-shrink-0">🎯</span>
                      )}
                      <span className="text-sm text-white truncate mr-2 flex-1">{preset.name}</span>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <button
                          onClick={() => handleGoTo(preset)}
                          disabled={movingToPreset === preset.id}
                          className="px-2.5 py-1 text-xs font-medium bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 text-white rounded transition-colors"
                        >
                          {movingToPreset === preset.id ? '...' : 'Go To'}
                        </button>
                        <button
                          onClick={() => handleDelete(preset)}
                          className="p-1 text-red-400 hover:text-red-300 transition-colors"
                          title="Delete preset"
                        >
                          <TrashIcon className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Capture button / form */}
              <div className="mt-3 flex-shrink-0">
                {showCapture ? (
                  <div className="flex gap-2">
                    <input
                      ref={captureInputRef}
                      type="text"
                      value={captureName}
                      onChange={(e) => setCaptureName(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') handleCapture(); if (e.key === 'Escape') setShowCapture(false); }}
                      placeholder="Preset name..."
                      className="flex-1 px-3 py-2 bg-dark-700 border border-dark-500 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                      disabled={capturing}
                    />
                    <button
                      onClick={handleCapture}
                      disabled={capturing || !captureName.trim()}
                      className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      {capturing ? '...' : 'Save'}
                    </button>
                    <button
                      onClick={() => { setShowCapture(false); setCaptureName(''); }}
                      disabled={capturing}
                      className="px-3 py-2 bg-dark-600 hover:bg-dark-500 text-gray-300 text-sm rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowCapture(true)}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
                  >
                    <PlusIcon className="h-4 w-4" />
                    Save Current Position
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PTZControlPanel;
