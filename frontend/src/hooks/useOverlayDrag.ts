import { useState, useCallback, useEffect, useRef } from 'react';

type Corner = 'nw' | 'ne' | 'sw' | 'se';

interface DragState {
  isDragging: boolean;
  isResizing: boolean;
  resizeCorner: Corner | null;
}

interface UseOverlayDragOptions {
  containerRef: React.RefObject<HTMLDivElement | null>;
  position: { x: number; y: number };
  size: { width: number; height: number };
  streamResolution: { width: number; height: number };
  aspectRatio: number | null; // image natural width / height — locks resize when set
  onPositionChange: (x: number, y: number) => void;
  onSizeChange: (width: number, height: number) => void;
}

export function useOverlayDrag({
  containerRef,
  position,
  size,
  streamResolution,
  aspectRatio,
  onPositionChange,
  onSizeChange,
}: UseOverlayDragOptions) {
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    isResizing: false,
    resizeCorner: null,
  });

  const startRef = useRef({ mouseX: 0, mouseY: 0, posX: 0, posY: 0, w: 0, h: 0 });

  const getContainerRect = useCallback(() => {
    return containerRef.current?.getBoundingClientRect() ?? { left: 0, top: 0, width: 1, height: 1 };
  }, [containerRef]);

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    startRef.current = { mouseX: e.clientX, mouseY: e.clientY, posX: position.x, posY: position.y, w: size.width, h: size.height };
    setDragState({ isDragging: true, isResizing: false, resizeCorner: null });
  }, [position, size]);

  const handleResizeStart = useCallback((e: React.MouseEvent, corner: Corner) => {
    e.preventDefault();
    e.stopPropagation();
    startRef.current = { mouseX: e.clientX, mouseY: e.clientY, posX: position.x, posY: position.y, w: size.width, h: size.height };
    setDragState({ isDragging: false, isResizing: true, resizeCorner: corner });
  }, [position, size]);

  useEffect(() => {
    if (!dragState.isDragging && !dragState.isResizing) return;

    const rect = getContainerRect();
    const s = startRef.current;

    const handleMouseMove = (e: MouseEvent) => {
      if (dragState.isDragging) {
        const dx = (e.clientX - s.mouseX) / rect.width;
        const dy = (e.clientY - s.mouseY) / rect.height;
        const newX = Math.max(0, Math.min(1, s.posX + dx));
        const newY = Math.max(0, Math.min(1, s.posY + dy));
        onPositionChange(newX, newY);
      } else if (dragState.isResizing && dragState.resizeCorner) {
        const dxPx = e.clientX - s.mouseX;
        const dyPx = e.clientY - s.mouseY;
        const scale = streamResolution.width / rect.width;
        const corner = dragState.resizeCorner;

        let newW = s.w;
        let newH = s.h;

        if (corner === 'se' || corner === 'ne') {
          newW = Math.max(20, s.w + dxPx * scale);
        } else {
          newW = Math.max(20, s.w - dxPx * scale);
        }

        if (aspectRatio && aspectRatio > 0) {
          // Lock aspect ratio: derive height from width
          newH = Math.max(20, newW / aspectRatio);
        } else {
          if (corner === 'se' || corner === 'sw') {
            newH = Math.max(20, s.h + dyPx * scale);
          } else {
            newH = Math.max(20, s.h - dyPx * scale);
          }
        }

        onSizeChange(Math.round(newW), Math.round(newH));
      }
    };

    const handleMouseUp = () => {
      setDragState({ isDragging: false, isResizing: false, resizeCorner: null });
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [dragState, getContainerRect, streamResolution, aspectRatio, onPositionChange, onSizeChange]);

  return { dragState, handleDragStart, handleResizeStart };
}
