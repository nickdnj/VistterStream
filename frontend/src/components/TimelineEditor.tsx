import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { api } from '../services/api';
import { ChevronDownIcon, ChevronRightIcon, PlusIcon, TrashIcon, PlayIcon, StopIcon, XMarkIcon } from '@heroicons/react/24/outline';

// UI Version for debugging deployment
const UI_VERSION = 'v1.0.3-constraints';

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
  channel_id?: string;
  youtube_stream_id?: string;
  youtube_broadcast_id?: string;
}

/**
 * TIMELINE ZOOM CONFIGURATION & VERTICAL SIZING
 * 
 * These constants control the timeline zoom behavior:
 * - MIN_ZOOM: Minimum zoom level (pixels per second) - allows viewing ~10 minutes (600s) in standard viewport
 * - MAX_ZOOM: Maximum zoom level (pixels per second) - for detailed frame-by-frame editing
 * - TRACK_HEIGHT: Visual height of each track in the timeline (optimized at 60px for compact vertical fit)
 * 
 * Zoom Level Examples at 1200px viewport width:
 * - 2 px/s: 600 seconds (10 minutes) visible
 * - 10 px/s: 120 seconds (2 minutes) visible
 * - 40 px/s: 30 seconds visible (default)
 * - 200 px/s: 6 seconds visible (maximum zoom-in)
 * 
 * Vertical Layout Optimization (v4):
 * - TRACK_HEIGHT: 60px (reduced from original 80px)
 * - Top bar: py-2 (reduced from py-2.5)
 * - YouTube Quick Links: py-1.5 (reduced from py-2.5)
 * - Track Controls: py-1.5 (reduced from py-2)
 * - Track Labels: No extra padding, fixed height only
 * - Supports 2-6 visible tracks without vertical scrolling at 1080p+ resolutions
 * - Horizontal scrollbar always visible at bottom without requiring extra scroll
 */
const TRACK_HEIGHT = 60; // Height of each track in pixels (optimized for compact vertical fit)
const MIN_ZOOM = 2; // Minimum pixels per second (extended range for 10-minute view)
const MAX_ZOOM = 200; // Maximum pixels per second

const TimelineEditor: React.FC = () => {
  const location = useLocation();
  const [timelines, setTimelines] = useState<Timeline[]>([]);
  const [selectedTimeline, setSelectedTimeline] = useState<Timeline | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [selectedDestinations, setSelectedDestinations] = useState<number[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [showNewTimelineModal, setShowNewTimelineModal] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [starting, setStarting] = useState(false);
  
  /**
   * YouTube Button Logic:
   * - Find the first SELECTED YouTube destination from selectedDestinations
   * - Extract youtube_stream_id (or youtube_broadcast_id) for Studio URL
   * - Extract channel_id for public Channel URL and as Studio fallback
   * - Buttons are always active; link to specific stream/channel if available, otherwise generic YouTube pages
   * 
   * URL Formats:
   * - Studio (with stream ID): https://studio.youtube.com/video/{stream_id}/livestreaming
   * - Studio (fallback with channel ID): https://studio.youtube.com/channel/{channel_id}/livestreaming
   * - Studio (generic): https://studio.youtube.com/livestreaming
   * - Channel (with channel ID): https://www.youtube.com/channel/{channel_id}/live
   * - Channel (generic): https://www.youtube.com/live
   */
  const selectedYoutubeDestination = destinations.find((dest) => 
    selectedDestinations.includes(dest.id) && 
    (dest.platform === 'youtube' || dest.platform === 'youtube_oauth')
  );
  // For YouTube live streams, broadcast_id = video_id (use broadcast_id for Studio URL)
  // Fallback to stream_id if broadcast_id not available
  const youtubeVideoId = selectedYoutubeDestination?.youtube_broadcast_id || 
                         selectedYoutubeDestination?.youtube_stream_id || 
                         null;
  const youtubeChannelId = selectedYoutubeDestination?.channel_id || null;
  const hasYoutubeDestination = !!selectedYoutubeDestination;
  
  // Studio URL with fallback: video ID (from broadcast) > channel ID > generic studio
  // Includes ?c={channel_id} parameter to help YouTube switch to correct account context
  const youtubeStudioUrl = youtubeVideoId
    ? `https://studio.youtube.com/video/${youtubeVideoId}/livestreaming${youtubeChannelId ? `?c=${youtubeChannelId}` : ''}`
    : youtubeChannelId
    ? `https://studio.youtube.com/channel/${youtubeChannelId}/livestreaming?c=${youtubeChannelId}`
    : 'https://studio.youtube.com/livestreaming';

  // Watch URL for sharing (direct link to the live stream)
  const youtubeWatchUrl = youtubeVideoId 
    ? `https://www.youtube.com/watch?v=${youtubeVideoId}` 
    : null;

  // Copy share URL to clipboard
  const handleCopyShareUrl = async () => {
    if (youtubeWatchUrl) {
      await navigator.clipboard.writeText(youtubeWatchUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const [cameraSnapshots, setCameraSnapshots] = useState<Record<number, string>>({});

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

  // Context menu for reordering sidebar items
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    type: 'camera' | 'asset' | 'timeline';
    itemId: number;
  } | null>(null);

  // Custom order state (persisted to localStorage)
  const [cameraOrder, setCameraOrder] = useState<number[]>([]);
  const [assetOrder, setAssetOrder] = useState<number[]>([]);
  const [timelineOrder, setTimelineOrder] = useState<number[]>([]);

  // "Show more" collapse state for sidebar lists
  const [showAllCameras, setShowAllCameras] = useState(false);
  const [showAllAssets, setShowAllAssets] = useState(false);
  const [showAllTimelines, setShowAllTimelines] = useState(false);

  const COLLAPSED_LIMIT = 5;

  // Playhead and zoom controls (local-only, no live preview)
  const [playheadTime, setPlayheadTime] = useState(0);
  // Initialize zoom level from sessionStorage or default to 40
  const [zoomLevel, setZoomLevel] = useState(() => {
    const savedZoom = sessionStorage.getItem('timeline-zoom-level');
    if (savedZoom) {
      const zoom = parseFloat(savedZoom);
      if (zoom >= MIN_ZOOM && zoom <= MAX_ZOOM) {
        return zoom;
      }
    }
    return 40; // pixels per second (default 40)
  });

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

  // Save zoom level to sessionStorage whenever it changes
  useEffect(() => {
    sessionStorage.setItem('timeline-zoom-level', zoomLevel.toString());
  }, [zoomLevel]);

  // Reload destinations when navigating to timelines page (e.g., returning from Settings)
  useEffect(() => {
    if (location.pathname === '/timelines') {
      loadDestinations();
    }
  }, [location.pathname]);

  // Load custom order from localStorage on mount
  useEffect(() => {
    const savedCameraOrder = localStorage.getItem('timeline-camera-order');
    const savedAssetOrder = localStorage.getItem('timeline-asset-order');
    const savedTimelineOrder = localStorage.getItem('timeline-timeline-order');
    
    if (savedCameraOrder) setCameraOrder(JSON.parse(savedCameraOrder));
    if (savedAssetOrder) setAssetOrder(JSON.parse(savedAssetOrder));
    if (savedTimelineOrder) setTimelineOrder(JSON.parse(savedTimelineOrder));
  }, []);

  // Save custom order to localStorage when it changes
  useEffect(() => {
    if (cameraOrder.length) localStorage.setItem('timeline-camera-order', JSON.stringify(cameraOrder));
  }, [cameraOrder]);

  useEffect(() => {
    if (assetOrder.length) localStorage.setItem('timeline-asset-order', JSON.stringify(assetOrder));
  }, [assetOrder]);

  useEffect(() => {
    if (timelineOrder.length) localStorage.setItem('timeline-timeline-order', JSON.stringify(timelineOrder));
  }, [timelineOrder]);

  // Close context menu when clicking elsewhere
  useEffect(() => {
    const handleClick = () => setContextMenu(null);
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  // Sync Start/Stop button with backend status on refresh and selection changes
  useEffect(() => {
    let statusInterval: any;

    const refreshExecutionStatus = async () => {
      try {
        if (!selectedTimeline?.id) return;
        const resp = await api.get(`/timeline-execution/status/${selectedTimeline.id}`);
        setIsRunning(Boolean(resp.data?.is_running));
        
        // Auto-select destinations if stream is running and we have destination IDs
        if (resp.data?.is_running && resp.data?.destination_ids?.length > 0) {
          setSelectedDestinations(resp.data.destination_ids);
        }
      } catch (err) {
        console.error('Failed to fetch timeline status:', err);
        // If status endpoint fails, assume not running to avoid false "Stop" state
        setIsRunning(false);
      }
    };

    if (selectedTimeline?.id) {
      // Check immediately on mount/selection
      refreshExecutionStatus();
      // Light polling to keep UI in sync if user refreshes or stream stops externally
      statusInterval = setInterval(refreshExecutionStatus, 5000);
    }

    return () => {
      if (statusInterval) clearInterval(statusInterval);
    };
  }, [selectedTimeline?.id]);

  // Playback preview (local-only)

  // Validate and fix cues that extend beyond timeline duration
  useEffect(() => {
    if (!selectedTimeline) return;
    
    let hasInvalidCues = false;
    const validatedTimeline = {
      ...selectedTimeline,
      tracks: selectedTimeline.tracks.map(track => ({
        ...track,
        cues: track.cues.map(cue => {
          const cueEnd = cue.start_time + cue.duration;
          
          // Check if cue extends beyond timeline
          if (cueEnd > selectedTimeline.duration) {
            hasInvalidCues = true;
            
            // Fix: constrain the cue to fit within timeline
            let fixedStartTime = cue.start_time;
            let fixedDuration = cue.duration;
            
            // If start is beyond duration, move it to the end
            if (fixedStartTime >= selectedTimeline.duration) {
              fixedStartTime = Math.max(0, selectedTimeline.duration - 1);
              fixedDuration = 1;
            } else {
              // Trim duration to fit
              fixedDuration = selectedTimeline.duration - fixedStartTime;
            }
            
            console.log(`🔧 Fixed invalid cue: ${cue.start_time}s + ${cue.duration}s → ${fixedStartTime}s + ${fixedDuration}s`);
            
            return {
              ...cue,
              start_time: fixedStartTime,
              duration: fixedDuration
            };
          }
          
          return cue;
        })
      }))
    };
    
    // Only update if we found and fixed invalid cues
    if (hasInvalidCues) {
      console.log('⚠️ Found and auto-fixed cues extending beyond timeline duration');
      setSelectedTimeline(validatedTimeline);
    }
  }, [selectedTimeline?.id]); // Only run when timeline changes, not on every render

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
      const response = await api.get('/timelines');
      const timelinesData = Array.isArray(response.data) ? response.data : [];
      setTimelines(timelinesData);
      if (timelinesData.length > 0 && !selectedTimeline) {
        // Check for active/running timeline first
        try {
          const activeResp = await api.get('/timeline-execution/active');
          const activeIds = Array.isArray(activeResp.data?.active_timeline_ids) ? activeResp.data.active_timeline_ids : [];
          
          if (activeIds.length > 0) {
            // Find and select the active timeline
            const activeTimeline = timelinesData.find(
              (t: Timeline) => activeIds.includes(t.id)
            );
            if (activeTimeline) {
              setSelectedTimeline(activeTimeline);
              return;
            }
          }
        } catch (err) {
          console.log('No active timeline found');
        }
        
        // Fall back to first timeline
        setSelectedTimeline(response.data[0]);
      }
    } catch (error) {
      console.error('Failed to load timelines:', error);
    }
  };

  const loadCameras = async () => {
    try {
      const response = await api.get('/cameras');
      const camerasData = Array.isArray(response.data) ? response.data : [];
      setCameras(camerasData);
    } catch (error) {
      console.error('Failed to load cameras:', error);
    }
  };

  const loadPresets = async () => {
    try {
      const response = await api.get('/presets');
      const presetsData = Array.isArray(response.data) ? response.data : [];
      setPresets(presetsData);
    } catch (error) {
      console.error('Failed to load presets:', error);
    }
  };

  const loadAssets = async () => {
    try {
      const response = await api.get('/assets');
      const assetsData = Array.isArray(response.data) ? response.data : [];
      setAssets(assetsData);
    } catch (error) {
      console.error('Failed to load assets:', error);
    }
  };

  const loadDestinations = async () => {
    try {
      const response = await api.get('/destinations');
      const destinationsData = Array.isArray(response.data) ? response.data : [];
      setDestinations(destinationsData.filter((d: Destination) => d.is_active));
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

  // Sort items by custom order (for sidebar reordering)
  const sortByCustomOrder = <T extends { id?: number }>(
    items: T[],
    customOrder: number[]
  ): T[] => {
    // Ensure items is always an array
    if (!Array.isArray(items)) return [];
    if (!Array.isArray(customOrder) || customOrder.length === 0) return items;
    
    return [...items].sort((a, b) => {
      const indexA = customOrder.indexOf(a.id || 0);
      const indexB = customOrder.indexOf(b.id || 0);
      // Items not in custom order go to the end
      if (indexA === -1 && indexB === -1) return 0;
      if (indexA === -1) return 1;
      if (indexB === -1) return -1;
      return indexA - indexB;
    });
  };

  // Context menu handlers for sidebar reordering
  const handleContextMenu = (
    e: React.MouseEvent,
    type: 'camera' | 'asset' | 'timeline',
    itemId: number
  ) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, type, itemId });
  };

  const handleMoveItem = (direction: 'top' | 'up' | 'down') => {
    if (!contextMenu) return;
    
    const { type, itemId } = contextMenu;
    const items = type === 'camera' ? cameras : type === 'asset' ? assets : timelines;
    const currentOrder = type === 'camera' ? cameraOrder : type === 'asset' ? assetOrder : timelineOrder;
    const setOrder = type === 'camera' ? setCameraOrder : type === 'asset' ? setAssetOrder : setTimelineOrder;
    
    // Build order array if empty (use current item order)
    let order = currentOrder.length ? [...currentOrder] : items.map(i => i.id!);
    const currentIndex = order.indexOf(itemId);
    
    if (currentIndex === -1) {
      // Item not in order array, add it
      order.push(itemId);
    }
    
    const idx = order.indexOf(itemId);
    
    // Remove from current position
    order.splice(idx, 1);
    
    // Insert at new position
    if (direction === 'top') {
      order.unshift(itemId);
    } else if (direction === 'up' && idx > 0) {
      order.splice(idx - 1, 0, itemId);
    } else if (direction === 'down') {
      order.splice(idx + 1, 0, itemId);
    } else {
      order.splice(idx, 0, itemId); // Put back if can't move
    }
    
    setOrder(order);
    setContextMenu(null);
  };

  const addCueToTimeline = (trackIndex: number, camera: Camera, preset?: Preset) => {
    if (!selectedTimeline) return;

    const track = selectedTimeline.tracks[trackIndex];
    const lastCue = track.cues[track.cues.length - 1];
    const newStartTime = lastCue ? lastCue.start_time + lastCue.duration : 0;
    
    // Constrain to timeline bounds
    const defaultDuration = 10;
    
    // Check if there's any room left in the timeline
    if (newStartTime >= selectedTimeline.duration) {
      alert('⚠️ No room left in timeline! The timeline is full.');
      return;
    }
    
    // Calculate actual duration that fits in remaining space
    const remainingTime = selectedTimeline.duration - newStartTime;
    const actualDuration = Math.min(defaultDuration, remainingTime);
    
    // Sanity check (should not happen given above check, but defensive programming)
    if (actualDuration <= 0) {
      alert('⚠️ Cannot add cue - no space remaining.');
      return;
    }

    const newCue: Cue = {
      cue_order: track.cues.length,
      start_time: newStartTime,
      duration: actualDuration,
      action_type: 'show_camera',
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
    
    // Constrain cue to stay within timeline bounds
    // Ensure the cue doesn't start beyond the timeline duration
    const maxStartTime = Math.max(0, selectedTimeline.duration - cue.duration);
    newStartTime = Math.min(newStartTime, maxStartTime);
    
    // Create new timeline object with immutable update for proper React re-render
    const updatedTimeline = {
      ...selectedTimeline,
      tracks: selectedTimeline.tracks.map((track, idx) => 
        idx === draggingCue.trackIndex
          ? {
              ...track,
              cues: track.cues.map((c, cidx) =>
                cidx === draggingCue.cueIndex
                  ? { ...c, start_time: newStartTime }
                  : c
              )
            }
          : track
      )
    };
    
    setSelectedTimeline(updatedTimeline);
  };

  const handleCueResize = (e: MouseEvent) => {
    if (!resizingCue || !selectedTimeline) return;

    const deltaX = e.clientX - dragStartX;
    const deltaTime = deltaX / zoomLevel;
    const cue = selectedTimeline.tracks[resizingCue.trackIndex].cues[resizingCue.cueIndex];

    let newStartTime = cue.start_time;
    let newDuration = cue.duration;

    if (resizingCue.edge === 'left') {
      // Resize from left (change start_time and duration)
      newStartTime = Math.max(0, dragStartTime + deltaTime);
      newStartTime = Math.round(newStartTime * 2) / 2;
      const endTime = cue.start_time + cue.duration;
      newDuration = Math.max(1, endTime - newStartTime);
    } else {
      // Resize from right (change duration)
      newDuration = cue.duration + deltaTime;
      newDuration = Math.round(newDuration * 2) / 2;
      
      // Constrain resize to not exceed timeline duration
      const maxDuration = selectedTimeline.duration - cue.start_time;
      newDuration = Math.min(newDuration, maxDuration);
      newDuration = Math.max(1, newDuration);
    }

    // Create new timeline object with immutable update for proper React re-render
    const updatedTimeline = {
      ...selectedTimeline,
      tracks: selectedTimeline.tracks.map((track, idx) => 
        idx === resizingCue.trackIndex
          ? {
              ...track,
              cues: track.cues.map((c, cidx) =>
                cidx === resizingCue.cueIndex
                  ? { ...c, start_time: newStartTime, duration: newDuration }
                  : c
              )
            }
          : track
      )
    };

    setSelectedTimeline(updatedTimeline);
  };

  /**
   * Adaptive zoom controls with intelligent step sizing
   * - Small steps (2px) for low zoom levels (2-10 px/s) for fine control
   * - Medium steps (5px) for mid zoom levels (10-50 px/s)
   * - Large steps (10px) for high zoom levels (50+ px/s)
   */
  const handleZoomIn = () => {
    setZoomLevel((prev) => {
      let step;
      if (prev < 10) step = 2;
      else if (prev < 50) step = 5;
      else step = 10;
      return Math.min(MAX_ZOOM, prev + step);
    });
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => {
      let step;
      if (prev <= 10) step = 2;
      else if (prev <= 50) step = 5;
      else step = 10;
      return Math.max(MIN_ZOOM, prev - step);
    });
  };

  // Old playback controls removed - using Preview Window instead

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (draggingCue || resizingCue) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickTime = clickX / zoomLevel;
    setPlayheadTime(Math.max(0, Math.min(selectedTimeline?.duration || 0, clickTime)));
  };

  const resetPlayhead = () => {
    setPlayheadTime(0);
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
      await api.put(`/timelines/${selectedTimeline.id}`, selectedTimeline);
      alert('✅ Timeline saved successfully!');
      loadTimelines();
    } catch (error: any) {
      console.error('Failed to save timeline:', error);
      alert(`❌ Failed to save timeline:\n${error.response?.data?.detail || error.message || 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  const deleteTimeline = async (timelineId: number, timelineName: string) => {
    const confirmDelete = window.confirm(
      `⚠️ Delete Timeline "${timelineName}"?\n\nThis action cannot be undone. All tracks and cues will be permanently deleted.`
    );
    
    if (!confirmDelete) return;

    try {
      await api.delete(`/timelines/${timelineId}`);
      alert(`✅ Timeline "${timelineName}" deleted successfully!`);
      
      // Clear selection if deleted timeline was selected
      if (selectedTimeline?.id === timelineId) {
        setSelectedTimeline(null);
      }
      
      // Reload timeline list
      loadTimelines();
    } catch (error: any) {
      console.error('Failed to delete timeline:', error);
      alert(`❌ Failed to delete timeline:\n${error.response?.data?.detail || error.message || 'Unknown error'}`);
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

    // Check if another timeline is already running (MVP: only one stream at a time)
    try {
      const activeResp = await api.get('/timeline-execution/active');
      const activeIds = activeResp.data?.active_timeline_ids || [];
      
      if (activeIds.length > 0 && !activeIds.includes(selectedTimeline.id)) {
        // Another timeline is running - find its name
        const runningTimeline = timelines.find(t => activeIds.includes(t.id));
        const runningName = runningTimeline?.name || `Timeline #${activeIds[0]}`;
        
        alert(`⚠️ Another stream is already running!\n\n"${runningName}" is currently streaming.\n\nPlease stop that stream first before starting a new one.`);
        return;
      }
    } catch (err) {
      // Could not check active timelines, proceed anyway
      console.log('Could not check for active timelines:', err);
    }

    setStarting(true);
    try {
      // First, try to stop the timeline if it's already running (same timeline restart)
      try {
        await api.post(`/timeline-execution/stop/${selectedTimeline.id}`);
        console.log('🛑 Stopped existing timeline instance');
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
      } catch (stopError) {
        // Timeline wasn't running, that's fine
        console.log('No existing timeline to stop');
      }

      // Now start the timeline
      const response = await api.post('/timeline-execution/start', {
        timeline_id: selectedTimeline.id,
        destination_ids: selectedDestinations
      });
      setIsRunning(true);
      // Immediately refresh status from backend to avoid drift
      try { await api.get(`/timeline-execution/status/${selectedTimeline.id}`).then(r => setIsRunning(Boolean(r.data?.is_running))); } catch {}
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
      await api.post(`/timeline-execution/stop/${selectedTimeline.id}`);
      setIsRunning(false);
      // Immediately refresh status
      try { await api.get(`/timeline-execution/status/${selectedTimeline.id}`).then(r => setIsRunning(Boolean(r.data?.is_running))); } catch {}
      alert('Timeline stopped');
    } catch (error) {
      console.error('Failed to stop timeline:', error);
      alert('Failed to stop timeline');
    }
  };

  const createNewTimeline = async () => {
    try {
      const response = await api.post('/timelines', newTimeline);
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
    
    // Default duration for new cues
    const defaultDuration = 10;
    
    // Constrain drop position to timeline bounds
    // Snap to grid first
    let constrainedStartTime = Math.max(0, Math.round(dropTime * 2) / 2);
    
    // Ensure the cue fits within timeline
    // If dropping too close to the end, adjust duration or position
    if (constrainedStartTime + defaultDuration > selectedTimeline.duration) {
      // If there's room for a 1-second cue, allow it at the end
      if (constrainedStartTime < selectedTimeline.duration) {
        // Adjust start time to fit the default duration, or place at max possible position
        constrainedStartTime = Math.max(0, selectedTimeline.duration - defaultDuration);
      } else {
        // Drop is beyond timeline, place at the very end with minimal duration
        constrainedStartTime = Math.max(0, selectedTimeline.duration - 1);
      }
    }
    
    // Calculate actual duration (constrained to fit)
    const actualDuration = Math.min(defaultDuration, selectedTimeline.duration - constrainedStartTime);
    
    if (data.type === 'camera') {
      const camera = cameras.find(c => c.id === data.cameraId);
      if (camera) {
        const newCue: Cue = {
          cue_order: track.cues.length,
          start_time: constrainedStartTime,
          duration: actualDuration,
          action_type: 'show_camera',
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
          start_time: constrainedStartTime,
          duration: actualDuration,
          action_type: 'show_camera',
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
          start_time: constrainedStartTime,
          duration: actualDuration,
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

  const fetchCameraSnapshot = async (cameraId: number) => {
    if (cameraSnapshots[cameraId]) {
      return; // Already have this snapshot
    }

    try {
      const response = await api.get(`/cameras/${cameraId}/snapshot`);
      // Backend returns JSON with base64 encoded image
      if (response.data && response.data.image_data) {
        const imageUrl = `data:${response.data.content_type};base64,${response.data.image_data}`;
        setCameraSnapshots(prev => ({ ...prev, [cameraId]: imageUrl }));
      }
    } catch (error) {
      console.error('Failed to fetch camera snapshot:', error);
    }
  };

  // No live playhead polling

  // Fetch snapshots when playhead changes
  useEffect(() => {
    const currentCues = getCurrentCues();
    const videoCue = currentCues.find(c => c.track.track_type === 'video');
    
    if (videoCue && videoCue.cue.action_params.camera_id) {
      fetchCameraSnapshot(videoCue.cue.action_params.camera_id);
    }
  }, [playheadTime, selectedTimeline]);

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

  /**
   * Render time ruler with adaptive mark intervals based on zoom level
   * Ensures readable spacing at all zoom levels (2-200 px/s)
   */
  const renderTimeRuler = () => {
    if (!selectedTimeline) return null;

    const marks = [];
    const duration = selectedTimeline.duration;
    
    // Adaptive interval selection for optimal ruler readability
    // Target: ~40-80px spacing between marks for comfortable reading
    let interval: number;
    if (zoomLevel <= 4) {
      interval = 30; // Very zoomed out: show marks every 30s
    } else if (zoomLevel <= 8) {
      interval = 15; // Zoomed out: show marks every 15s
    } else if (zoomLevel <= 20) {
      interval = 10; // Mid-zoom out: show marks every 10s
    } else if (zoomLevel <= 40) {
      interval = 5; // Mid-zoom: show marks every 5s
    } else {
      interval = 1; // Zoomed in: show marks every 1s
    }
    
    for (let i = 0; i <= duration; i += interval) {
      marks.push(
        <div key={i} className="absolute flex flex-col items-start" style={{ left: `${i * zoomLevel}px` }}>
          <div className="w-px h-3 bg-gray-500"></div>
          <span className="text-xs text-gray-400 mt-1">{i}s</span>
        </div>
      );
    }

    return (
      <div 
        className="relative h-6 bg-dark-800 border-b border-dark-700 cursor-pointer" 
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
    <div className="h-full flex flex-col bg-dark-900">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-6 py-2 bg-dark-800 border-b border-dark-700">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-white">🎬 Timeline Editor</h1>
          <span className="text-xs text-gray-500 font-mono">{UI_VERSION}</span>
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
                {sortByCustomOrder(cameras, cameraOrder)
                  .slice(0, showAllCameras ? undefined : COLLAPSED_LIMIT)
                  .map((camera) => {
                  const isPTZ = camera.type === 'ptz';
                  const cameraPresets = isPTZ ? getPresetsForCamera(camera.id) : [];
                  const isExpanded = expandedCameras.has(camera.id);

                  return (
                    <div key={camera.id} className="space-y-1">
                      {/* Camera Card */}
                      <div 
                        className="bg-dark-700 rounded-lg overflow-hidden"
                        onContextMenu={(e) => handleContextMenu(e, 'camera', camera.id)}
                      >
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
                
                {/* Show more/less button for cameras */}
                {cameras.length > COLLAPSED_LIMIT && (
                  <button
                    onClick={() => setShowAllCameras(!showAllCameras)}
                    className="w-full py-2 text-sm text-gray-400 hover:text-white transition-colors"
                  >
                    {showAllCameras 
                      ? '▲ Show less' 
                      : `▼ Show ${cameras.length - COLLAPSED_LIMIT} more`}
                  </button>
                )}
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
                  <>
                    {sortByCustomOrder(assets, assetOrder)
                      .slice(0, showAllAssets ? undefined : COLLAPSED_LIMIT)
                      .map((asset) => (
                      <div
                        key={asset.id}
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer.setData('application/json', JSON.stringify({ type: 'asset', assetId: asset.id }));
                        }}
                        onContextMenu={(e) => handleContextMenu(e, 'asset', asset.id)}
                        className="bg-dark-700 rounded-lg overflow-hidden hover:bg-dark-600 cursor-move transition-colors"
                      >
                        <div className="flex items-center gap-2 p-3">
                          <span className="text-2xl flex-shrink-0">
                            {asset.type === 'api_image' && '🌐'}
                            {asset.type === 'static_image' && '🖼️'}
                            {asset.type === 'video' && '🎥'}
                            {asset.type === 'graphic' && '🎨'}
                            {asset.type === 'google_drawing' && '📊'}
                          </span>
                          <div className="flex-1 min-w-0">
                            <div className="text-white text-sm font-medium truncate">{asset.name}</div>
                            <div className="text-gray-400 text-xs">{asset.type.replace('_', ' ')}</div>
                          </div>
                        </div>
                      </div>
                    ))}
                    
                    {/* Show more/less button for assets */}
                    {assets.length > COLLAPSED_LIMIT && (
                      <button
                        onClick={() => setShowAllAssets(!showAllAssets)}
                        className="w-full py-2 text-sm text-gray-400 hover:text-white transition-colors"
                      >
                        {showAllAssets 
                          ? '▲ Show less' 
                          : `▼ Show ${assets.length - COLLAPSED_LIMIT} more`}
                      </button>
                    )}
                  </>
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
              {sortByCustomOrder(timelines, timelineOrder)
                .slice(0, showAllTimelines ? undefined : COLLAPSED_LIMIT)
                .map((timeline) => (
                <div
                  key={timeline.id}
                  className={`flex items-center gap-2 px-3 py-2 rounded transition-colors ${
                    selectedTimeline?.id === timeline.id
                      ? 'bg-primary-600'
                      : 'hover:bg-dark-700'
                  }`}
                  onContextMenu={(e) => timeline.id && handleContextMenu(e, 'timeline', timeline.id)}
                >
                  <button
                    onClick={() => setSelectedTimeline(timeline)}
                    className="flex-1 text-left text-gray-300 hover:text-white"
                  >
                    {timeline.name}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (timeline.id) {
                        deleteTimeline(timeline.id, timeline.name);
                      }
                    }}
                    className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                    title="Delete timeline"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
              ))}
              
              {/* Show more/less button for timelines */}
              {timelines.length > COLLAPSED_LIMIT && (
                <button
                  onClick={() => setShowAllTimelines(!showAllTimelines)}
                  className="w-full py-2 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  {showAllTimelines 
                    ? '▲ Show less' 
                    : `▼ Show ${timelines.length - COLLAPSED_LIMIT} more`}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Timeline Tracks Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {selectedTimeline ? (
            <>
              {/* Live Control - YouTube Quick Links */}
              <div className="bg-dark-800 border-b border-dark-700 px-4 py-1.5">
                <div className="max-w-4xl mx-auto flex flex-col sm:flex-row gap-2 sm:items-center sm:justify-between">
                  <div className="flex-1 min-w-0">
                    <h2 className="text-sm font-semibold text-white">
                      {hasYoutubeDestination ? (
                        <>
                          📺 {selectedYoutubeDestination?.name}
                          {youtubeVideoId && (
                            <span className="ml-2 font-mono text-xs text-gray-400" title="Broadcast/Video ID">
                              ({youtubeVideoId.substring(0, 12)}...)
                            </span>
                          )}
                        </>
                      ) : (
                        'YouTube Quick Links'
                      )}
                    </h2>
                    {!hasYoutubeDestination && (
                      <p className="text-gray-500 text-xs mt-0.5">
                        Select a YouTube destination above to link to specific stream
                      </p>
                    )}
                    {hasYoutubeDestination && !youtubeVideoId && !youtubeChannelId && (
                      <p className="text-yellow-500 text-xs mt-0.5">
                        💡 Add Broadcast ID or Channel ID to destination to link directly to your stream
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {/* Studio button - always active */}
                    <a
                      href={youtubeStudioUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`px-3 py-1.5 rounded text-sm font-medium whitespace-nowrap transition-colors ${
                        youtubeVideoId || youtubeChannelId
                          ? 'bg-red-600 hover:bg-red-700 text-white'
                          : 'bg-red-600 hover:bg-red-700 text-white'
                      }`}
                      title={
                        youtubeVideoId 
                          ? "Open YouTube Live Studio for this broadcast" 
                          : youtubeChannelId
                          ? "Open YouTube Live Studio for this channel"
                          : "Open YouTube Live Studio"
                      }
                    >
                      Studio ↗
                    </a>
                    
                    {/* Share button - only when broadcast ID available */}
                    {youtubeVideoId && (
                      <button
                        onClick={() => setShowShareModal(true)}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium whitespace-nowrap transition-colors"
                        title="Share stream link"
                      >
                        Share
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* YouTube Live Preview */}
              <div className="bg-dark-800 border-b border-dark-700">
                <div className="max-w-4xl mx-auto p-4">
                  {isRunning && hasYoutubeDestination && youtubeVideoId ? (
                    /* Stream running with valid YouTube broadcast ID - show embed */
                    <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
                      <iframe
                        className="absolute inset-0 w-full h-full rounded-lg"
                        src={`https://www.youtube.com/embed/${youtubeVideoId}?autoplay=1&mute=1`}
                        title="YouTube Live Preview"
                        frameBorder="0"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowFullScreen
                      />
                      <div className="absolute top-2 left-2 bg-red-600 px-2 py-1 rounded text-xs font-bold text-white flex items-center gap-1">
                        <span className="w-2 h-2 bg-white rounded-full animate-pulse"></span>
                        LIVE
                      </div>
                    </div>
                  ) : (
                    /* Placeholder states */
                    <div className="bg-dark-900 rounded-lg p-8 text-center border border-dark-700">
                      <div className="text-5xl mb-4">
                        {isRunning ? (hasYoutubeDestination ? '🔗' : '📺') : '▶️'}
                      </div>
                      <h3 className="text-lg font-semibold text-white mb-2">
                        {isRunning 
                          ? hasYoutubeDestination 
                            ? 'Broadcast ID Required'
                            : 'YouTube Preview Unavailable'
                          : 'Live Preview'}
                      </h3>
                      <p className="text-gray-400 text-sm max-w-md mx-auto">
                        {isRunning 
                          ? hasYoutubeDestination 
                            ? 'Add a Broadcast ID to your YouTube destination to enable live preview. Edit the destination in Settings to add the ID.'
                            : 'YouTube live preview is only available when streaming to a YouTube destination. Select a YouTube destination to enable preview.'
                          : 'Start the stream to view your YouTube live preview here. The embedded player will show your actual YouTube stream.'}
                      </p>
                      {!isRunning && hasYoutubeDestination && youtubeVideoId && (
                        <p className="text-green-400 text-xs mt-3">
                          Ready to preview: {selectedYoutubeDestination?.name}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Track Controls */}
              <div className="flex items-center justify-between gap-2 px-4 py-1.5 bg-dark-800 border-b border-dark-700">
                <div className="flex items-center gap-2">
                  <span className="text-gray-400 text-xs font-medium">Add Track:</span>
                  <button
                    onClick={() => addTrack('video')}
                    className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition-colors"
                  >
                    🎥 Video
                  </button>
                  <button
                    onClick={() => addTrack('overlay')}
                    className="px-2 py-1 bg-purple-600 hover:bg-purple-700 text-white text-xs rounded transition-colors"
                  >
                    🎨 Overlay
                  </button>
                  <button
                    onClick={() => addTrack('audio')}
                    className="px-2 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded transition-colors"
                  >
                    🔊 Audio
                  </button>
                </div>

                {/* Timeline Info & Playback Controls */}
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 border-r border-dark-700 pr-3">
                    <button
                      onClick={resetPlayhead}
                      className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-white text-xs rounded transition-colors"
                      title="Reset to start"
                    >
                      ⏮️
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
                <div className="w-40 bg-dark-800 border-r border-dark-700 flex flex-col flex-shrink-0">
                  <div className="h-6 border-b border-dark-700 flex items-center px-3 text-xs text-gray-400 font-semibold flex-shrink-0">
                    TRACKS
                  </div>
                  {selectedTimeline.tracks.map((track, trackIndex) => (
                    <div
                      key={trackIndex}
                      className="border-b border-dark-700 flex items-center justify-between px-3 flex-shrink-0"
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
                <div className="overflow-auto" ref={timelineRef}>
                  <div className="min-w-full relative">
                    {/* Time Ruler */}
                    {renderTimeRuler()}
                    
                    {/* Playhead (simple) */}
                    <div 
                      className="absolute top-0 bottom-0 z-50 pointer-events-none w-0.5 bg-red-500"
                      style={{ left: `${playheadTime * zoomLevel}px` }}
                    />
                    
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
                                    {asset.type === 'google_drawing' && '📊'}
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

      {/* Share Modal */}
      {showShareModal && youtubeWatchUrl && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-dark-800 rounded-lg p-6 w-full max-w-md border border-dark-700">
            <h2 className="text-xl font-bold text-white mb-4">Share Stream</h2>
            
            {/* URL Display */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">Stream Link</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  readOnly
                  value={youtubeWatchUrl}
                  className="flex-1 px-3 py-2 bg-dark-900 border border-dark-600 rounded-md text-white font-mono text-sm"
                  onClick={(e) => (e.target as HTMLInputElement).select()}
                />
                <button
                  onClick={handleCopyShareUrl}
                  className={`px-4 py-2 rounded-md font-medium transition-colors whitespace-nowrap ${
                    copied 
                      ? 'bg-green-600 text-white' 
                      : 'bg-blue-600 hover:bg-blue-700 text-white'
                  }`}
                >
                  {copied ? '✓ Copied!' : 'Copy'}
                </button>
              </div>
            </div>

            {/* Social Share Buttons */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">Share on</label>
              <div className="flex gap-2">
                {/* Twitter/X */}
                <a
                  href={`https://twitter.com/intent/tweet?url=${encodeURIComponent(youtubeWatchUrl)}&text=${encodeURIComponent('Watch live now!')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 px-3 py-2 bg-black hover:bg-gray-900 text-white rounded-md text-sm font-medium text-center transition-colors border border-gray-700"
                  title="Share on X (Twitter)"
                >
                  𝕏
                </a>
                
                {/* Facebook */}
                <a
                  href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(youtubeWatchUrl)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium text-center transition-colors"
                  title="Share on Facebook"
                >
                  Facebook
                </a>
                
                {/* LinkedIn */}
                <a
                  href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(youtubeWatchUrl)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 px-3 py-2 bg-blue-700 hover:bg-blue-800 text-white rounded-md text-sm font-medium text-center transition-colors"
                  title="Share on LinkedIn"
                >
                  LinkedIn
                </a>
                
                {/* WhatsApp */}
                <a
                  href={`https://wa.me/?text=${encodeURIComponent('Watch live now! ' + youtubeWatchUrl)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium text-center transition-colors"
                  title="Share on WhatsApp"
                >
                  WhatsApp
                </a>
              </div>
            </div>

            {/* Close Button */}
            <button
              onClick={() => setShowShareModal(false)}
              className="w-full px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-md transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Context Menu for reordering sidebar items */}
      {contextMenu && (
        <div
          className="fixed bg-dark-700 border border-dark-600 rounded-lg shadow-xl py-1 z-50 min-w-[140px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={() => handleMoveItem('top')}
            className="w-full px-4 py-2 text-left text-sm text-white hover:bg-dark-600 transition-colors flex items-center gap-2"
          >
            <span>⬆️</span> Move to top
          </button>
          <button
            onClick={() => handleMoveItem('up')}
            className="w-full px-4 py-2 text-left text-sm text-white hover:bg-dark-600 transition-colors flex items-center gap-2"
          >
            <span>🔼</span> Move up
          </button>
          <button
            onClick={() => handleMoveItem('down')}
            className="w-full px-4 py-2 text-left text-sm text-white hover:bg-dark-600 transition-colors flex items-center gap-2"
          >
            <span>🔽</span> Move down
          </button>
        </div>
      )}
    </div>
  );
};

export default TimelineEditor;
