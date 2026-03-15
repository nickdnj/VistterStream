import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FabricImage } from 'fabric';
import type { FabricObject } from 'fabric';
import { api } from '../../services/api';
import type { ActiveTool, SaveStatus, LayerInfo, CanvasProject } from './types';
import { CanvasHistoryManager } from './CanvasHistoryManager';
import FabricCanvas from './FabricCanvas';
import type { FabricCanvasHandle } from './FabricCanvas';
import EditorToolbar from './EditorToolbar';
import ToolPanel from './ToolPanel';
import PropertiesPanel from './PropertiesPanel';
import LayerPanel from './LayerPanel';
import ExportDialog from './ExportDialog';

const LOCAL_STORAGE_PREFIX = 'vistter_canvas_';
const AUTOSAVE_LOCAL_MS = 10_000;
const AUTOSAVE_SERVER_MS = 60_000;

const CanvasEditorPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Refs
  const canvasRef = useRef<FabricCanvasHandle>(null);
  const historyRef = useRef<CanvasHistoryManager | null>(null);
  const isDirtyRef = useRef(false);
  const localTimerRef = useRef<NodeJS.Timeout>(undefined);
  const serverTimerRef = useRef<NodeJS.Timeout>(undefined);
  const projectIdRef = useRef<number | null>(null);

  // State
  const [project, setProject] = useState<CanvasProject | null>(null);
  const [activeTool, setActiveTool] = useState<ActiveTool>('select');
  const [selectedObject, setSelectedObject] = useState<FabricObject | null>(null);
  const [layers, setLayers] = useState<LayerInfo[]>([]);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('saved');
  const [undoCount, setUndoCount] = useState(0);
  const [redoCount, setRedoCount] = useState(0);
  const [showExport, setShowExport] = useState(false);
  const [loading, setLoading] = useState(true);
  const [exportPngUrl, setExportPngUrl] = useState<string | null>(null);

  // ---- Helpers ----

  const syncLayers = useCallback(() => {
    const canvas = canvasRef.current?.getCanvas();
    if (!canvas) return;
    const objs = canvas.getObjects();
    const newLayers: LayerInfo[] = objs.map((obj: any) => ({
      customId: obj.customId ?? '',
      type: obj.type ?? 'unknown',
      label:
        obj.customName ??
        (obj.type === 'textbox'
          ? `Text: "${(obj.text ?? '').slice(0, 20)}"`
          : `${(obj.type ?? 'object').charAt(0).toUpperCase()}${(obj.type ?? 'object').slice(1)}`),
      visible: obj.visible !== false,
      locked: obj.selectable === false,
    }));
    setLayers(newLayers);
  }, []);

  const syncHistoryCounts = useCallback(() => {
    const h = historyRef.current;
    if (!h) return;
    setUndoCount(h.undoCount);
    setRedoCount(h.redoCount);
  }, []);

  const commitChange = useCallback(() => {
    historyRef.current?.saveState();
    syncHistoryCounts();
    syncLayers();
    isDirtyRef.current = true;
    setSaveStatus('unsaved');
  }, [syncHistoryCounts, syncLayers]);

  // ---- Save logic ----

  const saveToLocalStorage = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !projectIdRef.current) return;
    const json = JSON.stringify(canvas.toJSON());
    try {
      localStorage.setItem(`${LOCAL_STORAGE_PREFIX}${projectIdRef.current}`, json);
    } catch {
      // localStorage full — ignore
    }
  }, []);

  const saveToServer = useCallback(async () => {
    const canvas = canvasRef.current;
    const pid = projectIdRef.current;
    if (!canvas || !pid || !isDirtyRef.current) return;

    setSaveStatus('saving');
    try {
      const canvasJson = JSON.stringify(canvas.toJSON());
      const thumbnailData = canvas.toDataURL(0.25);
      await api.put(`/canvas-projects/${pid}`, {
        canvas_json: canvasJson,
        thumbnail_data: thumbnailData,
      });
      isDirtyRef.current = false;
      setSaveStatus('saved');
      // Clear localStorage crash-recovery data on successful save
      localStorage.removeItem(`${LOCAL_STORAGE_PREFIX}${pid}`);
    } catch (err) {
      console.error('Failed to save canvas:', err);
      setSaveStatus('unsaved');
    }
  }, []);

  const handleSaveToServer = useCallback(() => {
    saveToServer();
  }, [saveToServer]);

  // ---- Undo/Redo ----

  const handleUndo = useCallback(async () => {
    if (!historyRef.current) return;
    await historyRef.current.undo();
    syncHistoryCounts();
    syncLayers();
    setSelectedObject(null);
    isDirtyRef.current = true;
    setSaveStatus('unsaved');
  }, [syncHistoryCounts, syncLayers]);

  const handleRedo = useCallback(async () => {
    if (!historyRef.current) return;
    await historyRef.current.redo();
    syncHistoryCounts();
    syncLayers();
    setSelectedObject(null);
    isDirtyRef.current = true;
    setSaveStatus('unsaved');
  }, [syncHistoryCounts, syncLayers]);

  // ---- Image tool ----

  const handleImageSelected = useCallback((file: File) => {
    const canvas = canvasRef.current?.getCanvas();
    if (!canvas) return;

    const reader = new FileReader();
    reader.onload = async () => {
      const img = await FabricImage.fromURL(reader.result as string);
      (img as any).customId = crypto.randomUUID();
      // Scale to fit canvas if larger
      const maxW = 960;
      const maxH = 540;
      if ((img.width ?? 0) > maxW || (img.height ?? 0) > maxH) {
        const scale = Math.min(maxW / (img.width ?? 1), maxH / (img.height ?? 1));
        img.scale(scale);
      }
      img.set({ left: 100, top: 100 });
      canvas.add(img);
      canvas.setActiveObject(img);
      commitChange();
    };
    reader.readAsDataURL(file);
    setActiveTool('select');
  }, [commitChange]);

  // ---- Export ----

  const handleOpenExport = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const url = canvas.toDataURL(2);
    setExportPngUrl(url);
    setShowExport(true);
  }, []);

  // ---- Layer selection ----

  const handleLayerSelect = useCallback((customId: string) => {
    const canvas = canvasRef.current?.getCanvas();
    if (!canvas) return;
    const obj = canvas.getObjects().find((o: any) => o.customId === customId);
    if (obj) {
      canvas.setActiveObject(obj);
      canvas.requestRenderAll();
      setSelectedObject(obj);
    }
  }, []);

  // ---- Keyboard shortcuts ----

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      const isMeta = e.ctrlKey || e.metaKey;

      if (isMeta && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        handleUndo();
      } else if (isMeta && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        handleRedo();
      } else if (isMeta && e.key === 's') {
        e.preventDefault();
        handleSaveToServer();
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        // Don't delete if typing in an input
        if ((e.target as HTMLElement).tagName === 'INPUT' || (e.target as HTMLElement).tagName === 'TEXTAREA') return;
        // Don't delete if editing text on canvas
        const canvas = canvasRef.current?.getCanvas();
        const active = canvas?.getActiveObject();
        if (active && (active as any).isEditing) return;
        if (active && canvas) {
          canvas.remove(active);
          canvas.discardActiveObject();
          setSelectedObject(null);
          commitChange();
        }
      } else if (isMeta && e.key === 'd') {
        e.preventDefault();
        // Duplicate selected
        const canvas = canvasRef.current?.getCanvas();
        const active = canvas?.getActiveObject();
        if (active && canvas) {
          active.clone().then((cloned: FabricObject) => {
            (cloned as any).customId = crypto.randomUUID();
            cloned.set({ left: (cloned.left ?? 0) + 20, top: (cloned.top ?? 0) + 20 });
            canvas.add(cloned);
            canvas.setActiveObject(cloned);
            commitChange();
          });
        }
      } else if (!isMeta && !e.shiftKey && !e.altKey) {
        // Tool shortcuts (only when not in text editing mode)
        const canvas = canvasRef.current?.getCanvas();
        const active = canvas?.getActiveObject();
        if (active && (active as any).isEditing) return;
        if ((e.target as HTMLElement).tagName === 'INPUT' || (e.target as HTMLElement).tagName === 'TEXTAREA') return;

        switch (e.key.toLowerCase()) {
          case 'v': setActiveTool('select'); break;
          case 't': setActiveTool('text'); break;
          case 'r': setActiveTool('rect'); break;
          case 'c': setActiveTool('circle'); break;
          case 'l': setActiveTool('line'); break;
        }
      }
    };

    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [handleUndo, handleRedo, handleSaveToServer, commitChange]);

  // ---- beforeunload warning ----

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (isDirtyRef.current) {
        e.preventDefault();
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, []);

  // ---- Autosave timers ----

  useEffect(() => {
    localTimerRef.current = setInterval(saveToLocalStorage, AUTOSAVE_LOCAL_MS);
    serverTimerRef.current = setInterval(saveToServer, AUTOSAVE_SERVER_MS);
    return () => {
      clearInterval(localTimerRef.current);
      clearInterval(serverTimerRef.current);
    };
  }, [saveToLocalStorage, saveToServer]);

  // ---- Initialize history after canvas is ready ----

  const initHistory = useCallback(() => {
    const canvas = canvasRef.current?.getCanvas();
    if (canvas && !historyRef.current) {
      historyRef.current = new CanvasHistoryManager(canvas);
      syncHistoryCounts();
    }
  }, [syncHistoryCounts]);

  // ---- Load or create project ----

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      try {
        if (id === 'new') {
          // Create a new project
          const resp = await api.post('/canvas-projects', {
            name: `Canvas ${new Date().toLocaleDateString()}`,
            canvas_json: JSON.stringify({ version: '6.0.0', objects: [] }),
          });
          const newProject = resp.data;
          projectIdRef.current = newProject.id;
          setProject(newProject);
          navigate(`/assets/editor/${newProject.id}`, { replace: true });
        } else if (id) {
          const pid = parseInt(id);
          projectIdRef.current = pid;

          // Check for crash recovery
          const localData = localStorage.getItem(`${LOCAL_STORAGE_PREFIX}${pid}`);

          const resp = await api.get(`/canvas-projects/${pid}`);
          const loadedProject = resp.data;
          setProject(loadedProject);

          // Load canvas JSON
          if (localData && localData !== loadedProject.canvas_json) {
            // Ask user if they want to recover
            const recover = window.confirm(
              'Unsaved changes were found from a previous session. Recover them?'
            );
            if (recover) {
              await canvasRef.current?.loadFromJSON(localData);
            } else {
              localStorage.removeItem(`${LOCAL_STORAGE_PREFIX}${pid}`);
              await canvasRef.current?.loadFromJSON(loadedProject.canvas_json);
            }
          } else {
            await canvasRef.current?.loadFromJSON(loadedProject.canvas_json);
          }

          syncLayers();
          initHistory();
        }
      } catch (err) {
        console.error('Failed to load canvas project:', err);
        alert('Failed to load canvas project.');
        navigate('/assets');
      } finally {
        setLoading(false);
      }
    };

    // Small delay to ensure canvas ref is ready
    const t = setTimeout(init, 100);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Init history when canvas becomes available (for new projects)
  useEffect(() => {
    if (!loading && !historyRef.current) {
      initHistory();
    }
  }, [loading, initHistory]);

  // ---- Canvas event callbacks ----

  const handleSelectionChanged = useCallback((obj: FabricObject | null) => {
    setSelectedObject(obj);
  }, []);

  const handleObjectModified = useCallback(() => {
    commitChange();
  }, [commitChange]);

  const handleObjectAdded = useCallback(() => {
    syncLayers();
  }, [syncLayers]);

  const handleObjectRemoved = useCallback(() => {
    syncLayers();
  }, [syncLayers]);

  const selectedCustomId = selectedObject ? (selectedObject as any).customId ?? null : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-dark-900">
        <div className="text-gray-400 text-sm animate-pulse">Loading canvas editor...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-dark-900">
      {/* Top toolbar */}
      <EditorToolbar
        projectName={project?.name ?? ''}
        saveStatus={saveStatus}
        undoCount={undoCount}
        redoCount={redoCount}
        onUndo={handleUndo}
        onRedo={handleRedo}
        onSave={handleSaveToServer}
        onExport={handleOpenExport}
      />

      {/* Main editor area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Tool panel */}
        <ToolPanel
          activeTool={activeTool}
          onToolChange={setActiveTool}
          onImageSelected={handleImageSelected}
        />

        {/* Center: Canvas */}
        <FabricCanvas
          ref={canvasRef}
          activeTool={activeTool}
          onSelectionChanged={handleSelectionChanged}
          onObjectModified={handleObjectModified}
          onObjectAdded={handleObjectAdded}
          onObjectRemoved={handleObjectRemoved}
        />

        {/* Right: Properties + Layers */}
        <div className="w-64 flex flex-col bg-dark-800 border-l border-dark-700 overflow-hidden">
          {/* Properties */}
          <div className="flex-1 overflow-y-auto border-b border-dark-700">
            <PropertiesPanel
              selectedObject={selectedObject}
              canvas={canvasRef.current?.getCanvas() ?? null}
              onModified={commitChange}
            />
          </div>

          {/* Layers */}
          <div className="h-64 flex-shrink-0 overflow-hidden">
            <LayerPanel
              layers={layers}
              selectedCustomId={selectedCustomId}
              canvas={canvasRef.current?.getCanvas() ?? null}
              onSelect={handleLayerSelect}
              onModified={commitChange}
              onLayersChanged={syncLayers}
            />
          </div>
        </div>
      </div>

      {/* Export dialog */}
      <ExportDialog
        isOpen={showExport}
        onClose={() => setShowExport(false)}
        projectId={projectIdRef.current}
        pngDataUrl={exportPngUrl}
      />
    </div>
  );
};

export default CanvasEditorPage;
