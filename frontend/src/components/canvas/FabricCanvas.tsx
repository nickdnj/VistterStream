import React, { useEffect, useRef, useImperativeHandle, forwardRef, useCallback } from 'react';
import { Canvas, Rect, Circle, Textbox, Line } from 'fabric';
import type { FabricObject } from 'fabric';
import type { ActiveTool } from './types';

const LOGICAL_WIDTH = 1920;
const LOGICAL_HEIGHT = 1080;
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 4;

export interface FabricCanvasHandle {
  getCanvas: () => Canvas | null;
  loadFromJSON: (json: string) => Promise<void>;
  toJSON: () => any;
  toDataURL: (multiplier?: number) => string;
}

interface FabricCanvasProps {
  activeTool: ActiveTool;
  onSelectionChanged: (object: FabricObject | null) => void;
  onObjectModified: () => void;
  onObjectAdded: () => void;
  onObjectRemoved: () => void;
}

const FabricCanvas = forwardRef<FabricCanvasHandle, FabricCanvasProps>(({
  activeTool,
  onSelectionChanged,
  onObjectModified,
  onObjectAdded,
  onObjectRemoved,
}, ref) => {
  const canvasElRef = useRef<HTMLCanvasElement | null>(null);
  const fabricRef = useRef<Canvas | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const initRef = useRef(false);
  const activeToolRef = useRef(activeTool);
  activeToolRef.current = activeTool;

  // Expose canvas API to parent
  useImperativeHandle(ref, () => ({
    getCanvas: () => fabricRef.current,
    loadFromJSON: async (json: string) => {
      const canvas = fabricRef.current;
      if (!canvas) return;
      await canvas.loadFromJSON(json);
      // Assign customId to any objects that don't have one
      canvas.getObjects().forEach((obj: any) => {
        if (!obj.customId) {
          obj.customId = crypto.randomUUID();
        }
      });
      canvas.requestRenderAll();
    },
    toJSON: () => {
      const canvas = fabricRef.current;
      if (!canvas) return null;
      return (canvas as any).toJSON(['customId', 'customName']);
    },
    toDataURL: (multiplier = 2) => {
      const canvas = fabricRef.current;
      if (!canvas) return '';
      return canvas.toDataURL({ format: 'png', multiplier } as any);
    },
  }));

  // Tool cursor mapping
  const getCursor = useCallback((tool: ActiveTool): string => {
    switch (tool) {
      case 'select': return 'default';
      case 'text': return 'text';
      case 'rect':
      case 'circle':
      case 'line': return 'crosshair';
      case 'image': return 'pointer';
      default: return 'default';
    }
  }, []);

  // Canvas initialization
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    const el = canvasElRef.current;
    if (!el) return;

    const canvas = new Canvas(el, {
      width: LOGICAL_WIDTH,
      height: LOGICAL_HEIGHT,
      backgroundColor: 'transparent',
      preserveObjectStacking: true,
    });

    fabricRef.current = canvas;

    // Scale canvas to fit container
    const fitToContainer = () => {
      const container = containerRef.current;
      if (!container || !canvas) return;
      const { width: cw, height: ch } = container.getBoundingClientRect();
      const scale = Math.min(cw / LOGICAL_WIDTH, ch / LOGICAL_HEIGHT, 1);
      const wrapper = canvas.getElement().parentElement;
      if (wrapper) {
        wrapper.style.transform = `scale(${scale})`;
        wrapper.style.transformOrigin = 'top left';
        wrapper.style.width = `${LOGICAL_WIDTH}px`;
        wrapper.style.height = `${LOGICAL_HEIGHT}px`;
      }
    };

    fitToContainer();
    const resizeObserver = new ResizeObserver(fitToContainer);
    if (containerRef.current) resizeObserver.observe(containerRef.current);

    // Event wiring
    canvas.on('selection:created', (e) => {
      onSelectionChanged(e.selected?.[0] ?? null);
    });
    canvas.on('selection:updated', (e) => {
      onSelectionChanged(e.selected?.[0] ?? null);
    });
    canvas.on('selection:cleared', () => {
      onSelectionChanged(null);
    });
    canvas.on('object:modified', () => {
      onObjectModified();
    });
    canvas.on('object:added', () => {
      onObjectAdded();
    });
    canvas.on('object:removed', () => {
      onObjectRemoved();
    });

    // Tool mouse handlers for shape creation
    let isDrawing = false;
    let startX = 0;
    let startY = 0;
    let drawingObj: FabricObject | null = null;

    canvas.on('mouse:down', (opt) => {
      const tool = activeToolRef.current;
      if (tool === 'select' || tool === 'image') return;

      const pointer = canvas.getScenePoint(opt.e);
      startX = pointer.x;
      startY = pointer.y;

      if (tool === 'text') {
        const text = new Textbox('Text', {
          left: pointer.x,
          top: pointer.y,
          fontSize: 36,
          fill: '#ffffff',
          fontFamily: 'Inter, system-ui, sans-serif',
          width: 300,
        } as any);
        (text as any).customId = crypto.randomUUID();
        canvas.add(text);
        canvas.setActiveObject(text);
        text.enterEditing();
        onObjectModified();
        return;
      }

      isDrawing = true;
      canvas.selection = false;

      if (tool === 'rect') {
        drawingObj = new Rect({
          left: startX,
          top: startY,
          width: 0,
          height: 0,
          fill: '#3b82f6',
          stroke: '#60a5fa',
          strokeWidth: 2,
          rx: 4,
          ry: 4,
        });
      } else if (tool === 'circle') {
        drawingObj = new Circle({
          left: startX,
          top: startY,
          radius: 0,
          fill: '#10b981',
          stroke: '#34d399',
          strokeWidth: 2,
        });
      } else if (tool === 'line') {
        drawingObj = new Line([startX, startY, startX, startY], {
          stroke: '#ffffff',
          strokeWidth: 3,
        });
      }

      if (drawingObj) {
        (drawingObj as any).customId = crypto.randomUUID();
        canvas.add(drawingObj);
      }
    });

    canvas.on('mouse:move', (opt) => {
      if (!isDrawing || !drawingObj) return;
      const pointer = canvas.getScenePoint(opt.e);
      const tool = activeToolRef.current;

      if (tool === 'rect') {
        const rect = drawingObj as Rect;
        rect.set({
          width: Math.abs(pointer.x - startX),
          height: Math.abs(pointer.y - startY),
          left: Math.min(startX, pointer.x),
          top: Math.min(startY, pointer.y),
        });
      } else if (tool === 'circle') {
        const dx = pointer.x - startX;
        const dy = pointer.y - startY;
        const radius = Math.sqrt(dx * dx + dy * dy) / 2;
        (drawingObj as Circle).set({
          radius,
          left: Math.min(startX, pointer.x),
          top: Math.min(startY, pointer.y),
        });
      } else if (tool === 'line') {
        (drawingObj as Line).set({ x2: pointer.x, y2: pointer.y });
      }

      canvas.requestRenderAll();
    });

    canvas.on('mouse:up', () => {
      if (!isDrawing) return;
      isDrawing = false;
      canvas.selection = true;

      if (drawingObj) {
        canvas.setActiveObject(drawingObj);
        onObjectModified();
        drawingObj = null;
      }
    });

    // Ctrl+scroll zoom
    const handleWheel = (opt: any) => {
      if (!opt.e.ctrlKey && !opt.e.metaKey) return;
      opt.e.preventDefault();
      opt.e.stopPropagation();

      const delta = opt.e.deltaY;
      let zoom = canvas.getZoom();
      zoom *= 0.999 ** delta;
      zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom));

      const point = canvas.getScenePoint(opt.e);
      canvas.zoomToPoint(point, zoom);
    };
    canvas.on('mouse:wheel', handleWheel);

    return () => {
      resizeObserver.disconnect();
      canvas.dispose();
      fabricRef.current = null;
      initRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update cursor when tool changes
  useEffect(() => {
    const canvas = fabricRef.current;
    if (!canvas) return;
    canvas.defaultCursor = getCursor(activeTool);
    // Toggle object selectability based on tool
    const isSelect = activeTool === 'select';
    canvas.selection = isSelect;
    canvas.getObjects().forEach((obj) => {
      if (!(obj as any)._wasLocked) {
        obj.set({ selectable: isSelect, evented: isSelect });
      }
    });
  }, [activeTool, getCursor]);

  return (
    <div ref={containerRef} className="flex-1 overflow-hidden bg-dark-900 relative">
      {/* Checkerboard background to show transparency */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: 'linear-gradient(45deg, #1a1a2e 25%, transparent 25%), linear-gradient(-45deg, #1a1a2e 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #1a1a2e 75%), linear-gradient(-45deg, transparent 75%, #1a1a2e 75%)',
          backgroundSize: '20px 20px',
          backgroundPosition: '0 0, 0 10px, 10px -10px, -10px 0px',
        }}
      />
      <canvas ref={canvasElRef} className="relative" />
    </div>
  );
});

FabricCanvas.displayName = 'FabricCanvas';

export default FabricCanvas;
