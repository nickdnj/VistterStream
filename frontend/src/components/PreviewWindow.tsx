import React, { useState, useEffect, useRef } from 'react';
// @ts-ignore - HLS.js types
import Hls from 'hls.js';
import { api } from '../services/api';
import { 
  PlayIcon, 
  StopIcon, 
  SignalIcon,
  ExclamationTriangleIcon 
} from '@heroicons/react/24/outline';

interface PreviewStatus {
  is_active: boolean;
  mode: 'idle' | 'preview' | 'live';
  timeline_id: number | null;
  timeline_name: string | null;
  hls_url: string | null;
  server_healthy: boolean;
}

interface Destination {
  id: number;
  name: string;
  platform: string;
  is_active: boolean;
}

interface PreviewWindowProps {
  timelineId: number | null;
  onPreviewStart?: () => void;
  onPreviewStop?: () => void;
  onGoLive?: () => void;
}

const PreviewWindow: React.FC<PreviewWindowProps> = ({
  timelineId,
  onPreviewStart,
  onPreviewStop,
  onGoLive
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  
  const [status, setStatus] = useState<PreviewStatus>({
    is_active: false,
    mode: 'idle',
    timeline_id: null,
    timeline_name: null,
    hls_url: null,
    server_healthy: false
  });
  
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [selectedDestinations, setSelectedDestinations] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [videoLoading, setVideoLoading] = useState(false);
  const [lastCueId, setLastCueId] = useState<number | null>(null);
  const [playbackPosition, setPlaybackPosition] = useState<any>(null);
  const [playerSession, setPlayerSession] = useState(0); // force <video> remounts on switches

  // Wait for HLS manifest to become available (HTTP 200)
  const waitForManifest = async (manifestUrl: string, maxWaitMs: number = 20000): Promise<boolean> => {
    const start = Date.now();
    while (Date.now() - start < maxWaitMs) {
      try {
        const url = `${manifestUrl}?t=${Date.now()}`;
        const res = await api.get(url, { validateStatus: () => true });
        if (res.status === 200 && typeof res.data === 'string' && res.data.includes('#EXTM3U')) {
          return true;
        }
      } catch (e) {
        // ignore and retry
      }
      await new Promise((r) => setTimeout(r, 500));
    }
    return false;
  };

  // Load status and destinations
  useEffect(() => {
    loadPreviewStatus();
    loadDestinations();
    
    // Poll status every 2 seconds
    const interval = setInterval(loadPreviewStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  // Poll playback position to detect camera switches
  useEffect(() => {
    if (status.mode !== 'preview') return;
    
    const positionInterval = setInterval(async () => {
      try {
        const response = await api.get('/preview/playback-position');
        if (response.data.is_playing && response.data.position) {
          const newCueId = response.data.position.current_cue_id;
          setPlaybackPosition(response.data.position);
          
          // Detect camera switch (cue ID changed)
          if (lastCueId !== null && newCueId !== lastCueId) {
            console.log(`Camera switch detected: Cue ${lastCueId} → ${newCueId}`);
            console.log('Reinitializing HLS player for new camera...');
            
            // Completely reinitialize the player
            setPlayerSession((s) => s + 1); // force <video> remount to avoid stale frame
            cleanupHlsPlayer();
            setVideoLoading(true);
            // Wait until preview path is actually ready before loading manifest
            (async () => {
              if (status.hls_url && videoRef.current) {
                const ok = await waitForManifest(status.hls_url as string, 20000);
                if (ok) {
                  const newUrl = `${status.hls_url}?t=${Date.now()}`;
                  initializeHlsPlayer(newUrl);
                } else {
                  console.warn('HLS manifest not ready after wait window');
                }
              } else {
                console.warn('No HLS URL or video element unavailable');
              }
            })();
          }
          
          setLastCueId(newCueId);
        }
      } catch (err) {
        console.error('Failed to poll playback position:', err);
      }
    }, 500); // Poll every 500ms
    
    return () => clearInterval(positionInterval);
  }, [status.mode, lastCueId, status.hls_url]);

  // Initialize HLS player when preview starts
  useEffect(() => {
    let cancelled = false;
    if (status.mode === 'preview' && status.hls_url && videoRef.current) {
      setVideoLoading(true);
      (async () => {
        const ok = await waitForManifest(status.hls_url as string, 20000);
        if (!cancelled) {
          if (ok) {
            const hlsUrlWithCacheBust = `${status.hls_url}?t=${Date.now()}`;
            initializeHlsPlayer(hlsUrlWithCacheBust);
          } else {
            console.warn('HLS manifest not ready after initial wait');
          }
        }
      })();
      
      return () => {
        cancelled = true;
        cleanupHlsPlayer();
      };
    } else {
      cleanupHlsPlayer();
      setVideoLoading(false);
    }
  }, [status.mode, status.hls_url]);

  const loadPreviewStatus = async () => {
    try {
      const response = await api.get('/preview/status');
      setStatus(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to load preview status:', err);
    }
  };

  const loadDestinations = async () => {
    try {
      const response = await api.get('/destinations');
      setDestinations(response.data.filter((d: Destination) => d.is_active));
    } catch (err) {
      console.error('Failed to load destinations:', err);
    }
  };

  const initializeHlsPlayer = (hlsUrl: string) => {
    if (!videoRef.current) return;

    if (Hls.isSupported()) {
      const hls = new Hls({
        maxBufferLength: 2,  // Low latency: 2 second buffer
        maxMaxBufferLength: 4,
        liveSyncDuration: 1,
        liveMaxLatencyDuration: 3,
        manifestLoadingMaxRetry: 10,        // Retry manifest load up to 10 times
        manifestLoadingRetryDelay: 1000,    // Wait 1s between retries
        manifestLoadingMaxRetryTimeout: 30000  // Give up after 30 seconds
      });
      
      hls.loadSource(hlsUrl);
      hls.attachMedia(videoRef.current);
      
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        videoRef.current?.play();
        setError(null); // Clear any errors on successful load
        setVideoLoading(false); // Video loaded successfully
      });
      
      hls.on(Hls.Events.ERROR, (event: any, data: any) => {
        console.error('HLS error:', data);
        if (data.fatal) {
          if (data.type === 'mediaError') {
            // Media errors - try to recover
            console.log('Media error, attempting recovery...');
            hls.recoverMediaError();
          } else if (data.type === 'networkError' && data.details === 'manifestLoadError') {
            // Don't show error - camera switch handler will reinitialize
            console.log('Manifest load failed (likely camera switch in progress)');
          } else {
            // Only show error for unexpected issues
            setError(`Playback error: ${data.type}`);
          }
        }
      });
      
      hlsRef.current = hls;
    } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      // Native HLS support (Safari)
      videoRef.current.src = hlsUrl;
      videoRef.current.play();
    }
  };

  const cleanupHlsPlayer = () => {
    if (hlsRef.current) {
      try { hlsRef.current.detachMedia(); } catch {}
      try { hlsRef.current.destroy(); } catch {}
      hlsRef.current = null;
    }
    if (videoRef.current) {
      try { videoRef.current.pause(); } catch {}
      try { videoRef.current.removeAttribute('src'); } catch {}
      try { videoRef.current.load(); } catch {}
    }
  };

  const handleStartPreview = async () => {
    if (!timelineId) {
      setError('No timeline selected');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      await api.post('/preview/start', { timeline_id: timelineId });
      await loadPreviewStatus();
      onPreviewStart?.();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start preview');
    } finally {
      setLoading(false);
    }
  };

  const handleStopPreview = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await api.post('/preview/stop');
      await loadPreviewStatus();
      onPreviewStop?.();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to stop preview');
    } finally {
      setLoading(false);
    }
  };

  const handleGoLive = async () => {
    if (selectedDestinations.length === 0) {
      setError('Please select at least one destination');
      return;
    }

    const confirmMessage = `Go LIVE to ${selectedDestinations.length} destination(s)?\n\n` +
      `This will publish your stream to:\n` +
      destinations
        .filter(d => selectedDestinations.includes(d.id))
        .map(d => `• ${d.name} (${d.platform})`)
        .join('\n');
    
    if (!window.confirm(confirmMessage)) {
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      await api.post('/preview/go-live', {
        destination_ids: selectedDestinations
      });
      await loadPreviewStatus();
      onGoLive?.();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to go live');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = () => {
    switch (status.mode) {
      case 'preview': return 'bg-blue-500';
      case 'live': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusText = () => {
    switch (status.mode) {
      case 'preview': return 'PREVIEW';
      case 'live': return 'LIVE';
      default: return 'OFFLINE';
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg shadow-lg overflow-hidden">
      {/* Video Player */}
      <div className="relative bg-black" style={{ paddingBottom: '56.25%' }}>
        {status.mode === 'preview' || status.mode === 'live' ? (
          <>
            <video
              ref={videoRef}
              className="absolute inset-0 w-full h-full"
              controls={false}
              muted
              playsInline
              key={playerSession}
            />
            
            {/* Loading Overlay */}
            {videoLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-75 z-10">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-16 w-16 border-4 border-blue-500 border-t-transparent mx-auto mb-4"></div>
                  <p className="text-white text-lg">Starting stream...</p>
                  <p className="text-gray-400 text-sm mt-2">Please wait 3-5 seconds</p>
                </div>
              </div>
            )}
            
            {/* Status Badge */}
            <div className="absolute top-4 left-4 flex items-center space-x-2">
              <div className={`${getStatusColor()} px-3 py-1 rounded-full flex items-center space-x-2`}>
                <SignalIcon className="w-4 h-4 text-white animate-pulse" />
                <span className="text-white font-bold text-sm">{getStatusText()}</span>
              </div>
              {status.timeline_name && (
                <div className="bg-gray-800 bg-opacity-75 px-3 py-1 rounded-full">
                  <span className="text-white text-sm">{status.timeline_name}</span>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-gray-500">
              <PlayIcon className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg">Preview Offline</p>
              <p className="text-sm">Select a timeline and click "Start Preview"</p>
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="p-4 space-y-4">
        {/* Error Message */}
        {error && (
          <div className="bg-red-900 bg-opacity-50 border border-red-500 rounded-lg p-3 flex items-start space-x-2">
            <ExclamationTriangleIcon className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="text-red-200 text-sm">{error}</div>
          </div>
        )}

        {/* Preview Server Health Warning */}
        {!status.server_healthy && (
          <div className="bg-yellow-900 bg-opacity-50 border border-yellow-500 rounded-lg p-3">
            <div className="text-yellow-200 text-sm">
              ⚠️ Preview server is not running. Check system status or start MediaMTX.
            </div>
          </div>
        )}

        {/* Preview Controls */}
        <div className="flex items-center space-x-3">
          {status.mode === 'idle' ? (
            <button
              onClick={handleStartPreview}
              disabled={loading || !timelineId || !status.server_healthy}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center space-x-2 transition"
            >
              <PlayIcon className="w-5 h-5" />
              <span>{loading ? 'Starting...' : 'Start Preview'}</span>
            </button>
          ) : status.mode === 'preview' ? (
            <>
              <button
                onClick={handleStopPreview}
                disabled={loading}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center space-x-2 transition"
              >
                <StopIcon className="w-5 h-5" />
                <span>Stop Preview</span>
              </button>
              <button
                onClick={handleGoLive}
                disabled={loading || selectedDestinations.length === 0}
                className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-lg flex items-center justify-center space-x-2 transition animate-pulse"
              >
                <SignalIcon className="w-5 h-5" />
                <span>{loading ? 'Going Live...' : 'GO LIVE'}</span>
              </button>
            </>
          ) : (
            <button
              onClick={handleStopPreview}
              disabled={loading}
              className="flex-1 bg-red-700 hover:bg-red-600 text-white font-bold py-2 px-4 rounded-lg flex items-center justify-center space-x-2 transition"
            >
              <StopIcon className="w-5 h-5" />
              <span>Stop Live Stream</span>
            </button>
          )}
        </div>

        {/* Destination Selection (shown in preview mode) */}
        {status.mode === 'preview' && (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-300">
              Select Live Destinations:
            </label>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {destinations.map((dest) => (
                <label
                  key={dest.id}
                  className="flex items-center space-x-2 p-2 hover:bg-gray-800 rounded cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedDestinations.includes(dest.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedDestinations([...selectedDestinations, dest.id]);
                      } else {
                        setSelectedDestinations(selectedDestinations.filter(id => id !== dest.id));
                      }
                    }}
                    className="w-4 h-4"
                  />
                  <span className="text-sm text-gray-300">
                    {dest.name} ({dest.platform})
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Info */}
        <div className="text-xs text-gray-500 space-y-1">
          <div>• Preview latency: ~2 seconds</div>
          <div>• Timeline will restart when going live (seamless transition coming soon)</div>
        </div>
      </div>
    </div>
  );
};

export default PreviewWindow;
