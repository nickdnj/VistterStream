import React, { useState, useRef, useEffect } from 'react';
import OverlayItem, { OverlayItemAsset } from './OverlayItem';
import { ArrowPathIcon } from '@heroicons/react/24/outline';

export interface CueKey {
  trackIndex: number;
  cueIndex: number;
}

export interface OverlayPositionUpdate {
  position_x?: number;
  position_y?: number;
  width?: number;
  height?: number;
  opacity?: number;
}

export interface OverlayInfo {
  cueKey: CueKey;
  asset: OverlayItemAsset;
  position_x: number;
  position_y: number;
  width: number;
  height: number;
  opacity: number;
}

interface OverlayPreviewPanelProps {
  snapshotUrl: string | null;
  overlays: OverlayInfo[];
  resolution: string;
  onOverlayUpdate: (cueKey: CueKey, updates: OverlayPositionUpdate) => void;
  onRefreshSnapshot?: () => void;
  onResetOverlay?: (cueKey: CueKey) => void;
}

const DEFAULT_OVERLAY_SIZE = 200;

const OverlayPreviewPanel: React.FC<OverlayPreviewPanelProps> = ({
  snapshotUrl,
  overlays,
  resolution,
  onOverlayUpdate,
  onRefreshSnapshot,
  onResetOverlay,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerSize, setContainerSize] = useState({ width: 1, height: 1 });
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  // Parse stream resolution
  const [resW, resH] = resolution.split('x').map(Number);
  const streamRes = { width: resW || 1920, height: resH || 1080 };
  const aspectRatio = streamRes.height / streamRes.width;

  // Track container size
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const update = () => {
      const rect = el.getBoundingClientRect();
      setContainerSize({ width: rect.width, height: rect.height });
    };
    update();

    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const cueKeyStr = (k: CueKey) => `${k.trackIndex}-${k.cueIndex}`;

  const selectedOverlay = overlays.find(o => cueKeyStr(o.cueKey) === selectedKey);

  // Deselect if selected overlay disappears
  useEffect(() => {
    if (selectedKey && !overlays.find(o => cueKeyStr(o.cueKey) === selectedKey)) {
      setSelectedKey(null);
    }
  }, [overlays, selectedKey]);

  return (
    <div className="bg-dark-800 border-b border-dark-700">
      <div className="max-w-4xl mx-auto p-4">
        {/* Preview container with aspect ratio */}
        <div
          className="relative w-full bg-dark-900 rounded-lg overflow-hidden border border-dark-600"
          style={{ paddingBottom: `${aspectRatio * 100}%` }}
        >
          <div
            ref={containerRef}
            className="absolute inset-0"
            onClick={() => setSelectedKey(null)}
          >
            {/* Camera snapshot background */}
            {snapshotUrl ? (
              <img
                src={snapshotUrl}
                alt="Camera preview"
                className="absolute inset-0 w-full h-full object-cover"
                draggable={false}
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <div className="text-3xl mb-2">📷</div>
                  <p className="text-sm">No camera at current playhead</p>
                </div>
              </div>
            )}

            {/* Overlay items */}
            {overlays.map((overlay) => {
              const key = cueKeyStr(overlay.cueKey);
              const effectiveW = overlay.width || DEFAULT_OVERLAY_SIZE;
              const effectiveH = overlay.height || DEFAULT_OVERLAY_SIZE;

              return (
                <OverlayItem
                  key={key}
                  asset={overlay.asset}
                  positionX={overlay.position_x}
                  positionY={overlay.position_y}
                  width={effectiveW}
                  height={effectiveH}
                  opacity={overlay.opacity}
                  containerSize={containerSize}
                  streamResolution={streamRes}
                  containerRef={containerRef}
                  isSelected={selectedKey === key}
                  onSelect={() => setSelectedKey(key)}
                  onPositionChange={(x, y) =>
                    onOverlayUpdate(overlay.cueKey, { position_x: x, position_y: y })
                  }
                  onSizeChange={(w, h) =>
                    onOverlayUpdate(overlay.cueKey, { width: w, height: h })
                  }
                />
              );
            })}

            {/* Overlay count badge */}
            <div className="absolute top-2 left-2 bg-dark-900/80 text-gray-300 text-[10px] px-2 py-1 rounded">
              {streamRes.width}x{streamRes.height}
              {overlays.length > 0 && ` | ${overlays.length} overlay${overlays.length !== 1 ? 's' : ''}`}
            </div>

            {/* Refresh snapshot button */}
            {onRefreshSnapshot && (
              <button
                onClick={(e) => { e.stopPropagation(); onRefreshSnapshot(); }}
                className="absolute top-2 right-2 p-1.5 bg-dark-900/80 hover:bg-dark-700 text-gray-300 rounded transition-colors"
                title="Refresh snapshot"
              >
                <ArrowPathIcon className="w-4 h-4" />
              </button>
            )}

            {/* Empty overlay hint */}
            {snapshotUrl && overlays.length === 0 && (
              <div className="absolute bottom-2 left-1/2 -translate-x-1/2 bg-dark-900/80 text-gray-400 text-xs px-3 py-1.5 rounded">
                Move playhead over overlay cues to position them
              </div>
            )}
          </div>
        </div>

        {/* Selected overlay controls */}
        {selectedOverlay && (
          <div className="mt-3 flex items-center gap-4 bg-dark-900 rounded-lg px-4 py-2.5 border border-dark-700">
            <span className="text-xs text-gray-400 font-medium whitespace-nowrap">
              {selectedOverlay.asset.name}
            </span>

            {/* Opacity slider */}
            <div className="flex items-center gap-2 flex-1">
              <span className="text-[10px] text-gray-500">Opacity</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={selectedOverlay.opacity}
                onChange={(e) =>
                  onOverlayUpdate(selectedOverlay.cueKey, { opacity: parseFloat(e.target.value) })
                }
                className="flex-1 h-1.5 accent-blue-500"
              />
              <span className="text-[10px] text-gray-400 w-8 text-right">
                {Math.round(selectedOverlay.opacity * 100)}%
              </span>
            </div>

            {/* Position readout */}
            <span className="text-[10px] text-gray-500 font-mono whitespace-nowrap">
              {Math.round(selectedOverlay.position_x * streamRes.width)}, {Math.round(selectedOverlay.position_y * streamRes.height)}
              {' | '}
              {selectedOverlay.width || DEFAULT_OVERLAY_SIZE}x{selectedOverlay.height || DEFAULT_OVERLAY_SIZE}
            </span>

            {/* Reset button */}
            {onResetOverlay && (
              <button
                onClick={() => onResetOverlay(selectedOverlay.cueKey)}
                className="text-[10px] text-gray-500 hover:text-white transition-colors whitespace-nowrap"
              >
                Reset
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default OverlayPreviewPanel;
