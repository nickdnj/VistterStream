import React from 'react';
import { useOverlayDrag } from '../../hooks/useOverlayDrag';
import { getAssetImageUrl } from '../../utils/assetImageUrl';

export interface OverlayItemAsset {
  id: number;
  name: string;
  type: string;
  file_path: string | null;
  api_url: string | null;
}

interface OverlayItemProps {
  asset: OverlayItemAsset;
  positionX: number;
  positionY: number;
  width: number;
  height: number;
  opacity: number;
  containerSize: { width: number; height: number };
  streamResolution: { width: number; height: number };
  containerRef: React.RefObject<HTMLDivElement | null>;
  isSelected: boolean;
  onSelect: () => void;
  onPositionChange: (x: number, y: number) => void;
  onSizeChange: (w: number, h: number) => void;
}

const HANDLE_SIZE = 8;

const OverlayItem: React.FC<OverlayItemProps> = ({
  asset,
  positionX,
  positionY,
  width,
  height,
  opacity,
  containerSize,
  streamResolution,
  containerRef,
  isSelected,
  onSelect,
  onPositionChange,
  onSizeChange,
}) => {
  const { dragState, handleDragStart, handleResizeStart } = useOverlayDrag({
    containerRef,
    position: { x: positionX, y: positionY },
    size: { width, height },
    streamResolution,
    onPositionChange,
    onSizeChange,
  });

  const imageUrl = getAssetImageUrl(asset);

  // Convert normalized position to CSS pixels within the container
  const leftPx = positionX * containerSize.width;
  const topPx = positionY * containerSize.height;

  // Scale asset pixel dimensions to container pixel dimensions
  const scaleX = containerSize.width / streamResolution.width;
  const scaleY = containerSize.height / streamResolution.height;
  const renderW = width * scaleX;
  const renderH = height * scaleY;

  const isDraggingOrResizing = dragState.isDragging || dragState.isResizing;

  return (
    <div
      className={`absolute group ${isDraggingOrResizing ? 'z-50' : 'z-10'}`}
      style={{
        left: `${leftPx}px`,
        top: `${topPx}px`,
        width: `${renderW}px`,
        height: `${renderH}px`,
        cursor: dragState.isDragging ? 'grabbing' : 'grab',
      }}
      onMouseDown={(e) => {
        onSelect();
        handleDragStart(e);
      }}
      onClick={(e) => e.stopPropagation()}
    >
      {/* Image or placeholder */}
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={asset.name}
          className="w-full h-full object-contain pointer-events-none select-none"
          style={{ opacity }}
          draggable={false}
          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
        />
      ) : (
        <div
          className="w-full h-full bg-purple-600/30 flex items-center justify-center text-white text-xs pointer-events-none"
          style={{ opacity }}
        >
          {asset.name}
        </div>
      )}

      {/* Selection border */}
      <div
        className={`absolute inset-0 border-2 rounded transition-colors pointer-events-none ${
          isSelected ? 'border-blue-400' : 'border-transparent group-hover:border-blue-400/50'
        }`}
      />

      {/* Name label */}
      {isSelected && (
        <div className="absolute -top-6 left-0 bg-blue-600 text-white text-[10px] px-1.5 py-0.5 rounded whitespace-nowrap">
          {asset.name}
        </div>
      )}

      {/* Pixel coordinate badge while dragging */}
      {isDraggingOrResizing && (
        <div className="absolute -bottom-6 left-0 bg-dark-900 text-gray-300 text-[10px] px-1.5 py-0.5 rounded whitespace-nowrap border border-dark-600">
          {Math.round(positionX * streamResolution.width)}, {Math.round(positionY * streamResolution.height)}
          {dragState.isResizing && ` | ${width}x${height}`}
        </div>
      )}

      {/* Resize handles (visible when selected or hovered) */}
      {(isSelected || isDraggingOrResizing) && (
        <>
          {(['nw', 'ne', 'sw', 'se'] as const).map((corner) => {
            const isLeft = corner.includes('w');
            const isTop = corner.includes('n');
            return (
              <div
                key={corner}
                className="absolute bg-white border-2 border-blue-500 rounded-sm z-20"
                style={{
                  width: HANDLE_SIZE,
                  height: HANDLE_SIZE,
                  left: isLeft ? -HANDLE_SIZE / 2 : undefined,
                  right: isLeft ? undefined : -HANDLE_SIZE / 2,
                  top: isTop ? -HANDLE_SIZE / 2 : undefined,
                  bottom: isTop ? undefined : -HANDLE_SIZE / 2,
                  cursor: corner === 'nw' || corner === 'se' ? 'nwse-resize' : 'nesw-resize',
                }}
                onMouseDown={(e) => handleResizeStart(e, corner)}
              />
            );
          })}
        </>
      )}
    </div>
  );
};

export default OverlayItem;
