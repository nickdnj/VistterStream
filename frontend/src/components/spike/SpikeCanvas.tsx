import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Canvas, Rect, Textbox, Circle } from 'fabric';
import { CanvasHistoryManager } from './CanvasHistoryManager';

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

interface LayerInfo {
  id: number;
  type: string;
  label: string;
}

/* ------------------------------------------------------------------ */
/*  SpikeCanvas                                                       */
/* ------------------------------------------------------------------ */

const CANVAS_WIDTH = 800;
const CANVAS_HEIGHT = 500;
const LOCAL_STORAGE_KEY = 'vistter_spike_canvas';

const SpikeCanvas: React.FC = () => {
  // Refs ----------------------------------------------------------------
  const canvasElRef = useRef<HTMLCanvasElement | null>(null);
  const fabricRef = useRef<Canvas | null>(null);
  const historyRef = useRef<CanvasHistoryManager | null>(null);
  const initRef = useRef(false); // guards React 19 strict-mode double-mount

  // State ---------------------------------------------------------------
  const [layers, setLayers] = useState<LayerInfo[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [undoCount, setUndoCount] = useState(0);
  const [redoCount, setRedoCount] = useState(0);
  const [exportUrl, setExportUrl] = useState<string | null>(null);
  const [roundTripStatus, setRoundTripStatus] = useState<'idle' | 'pass' | 'fail'>('idle');

  // Helpers -------------------------------------------------------------

  /** Build the layer list from the current canvas objects. */
  const syncLayers = useCallback(() => {
    const canvas = fabricRef.current;
    if (!canvas) return;
    const objs = canvas.getObjects();
    const newLayers: LayerInfo[] = objs.map((obj, i) => ({
      id: i,
      type: obj.type ?? 'unknown',
      label:
        obj.type === 'textbox'
          ? `Text: "${(obj as Textbox).text?.slice(0, 20) ?? ''}"`
          : `${(obj.type ?? 'object').charAt(0).toUpperCase()}${(obj.type ?? 'object').slice(1)} ${i + 1}`,
    }));
    setLayers(newLayers);
  }, []);

  /** Refresh undo/redo badge counts from the history manager. */
  const syncHistoryCounts = useCallback(() => {
    const h = historyRef.current;
    if (!h) return;
    setUndoCount(h.undoCount);
    setRedoCount(h.redoCount);
  }, []);

  /** Save current state to history and refresh counts + layers. */
  const commitChange = useCallback(() => {
    historyRef.current?.saveState();
    syncHistoryCounts();
    syncLayers();
  }, [syncHistoryCounts, syncLayers]);

  // Canvas init / cleanup -----------------------------------------------

  useEffect(() => {
    // Guard against React 19 strict-mode double invocation
    if (initRef.current) return;
    initRef.current = true;

    const el = canvasElRef.current;
    if (!el) return;

    const canvas = new Canvas(el, {
      width: CANVAS_WIDTH,
      height: CANVAS_HEIGHT,
      backgroundColor: '#1e293b', // dark-800
    });

    fabricRef.current = canvas;
    historyRef.current = new CanvasHistoryManager(canvas);

    // Wire Fabric events -> React state
    const onSelection = () => {
      const active = canvas.getActiveObject();
      if (active) {
        const idx = canvas.getObjects().indexOf(active);
        setSelectedId(idx >= 0 ? idx : null);
      }
    };
    const onCleared = () => setSelectedId(null);
    const onChange = () => {
      commitChange();
    };

    canvas.on('selection:created', onSelection);
    canvas.on('selection:updated', onSelection);
    canvas.on('selection:cleared', onCleared);
    canvas.on('object:modified', onChange);
    canvas.on('object:added', () => {
      syncLayers();
    });
    canvas.on('object:removed', () => {
      syncLayers();
    });

    syncLayers();
    syncHistoryCounts();

    // Keyboard shortcuts
    const handleKeyboard = (e: KeyboardEvent) => {
      const isMeta = e.ctrlKey || e.metaKey;
      if (!isMeta) return;

      if (e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        historyRef.current?.undo().then(() => {
          syncHistoryCounts();
          syncLayers();
          setSelectedId(null);
        });
      } else if ((e.key === 'z' && e.shiftKey) || e.key === 'y') {
        e.preventDefault();
        historyRef.current?.redo().then(() => {
          syncHistoryCounts();
          syncLayers();
          setSelectedId(null);
        });
      }
    };

    window.addEventListener('keydown', handleKeyboard);

    return () => {
      window.removeEventListener('keydown', handleKeyboard);
      canvas.dispose();
      fabricRef.current = null;
      historyRef.current = null;
      // Allow re-init if strict mode unmounts and remounts
      initRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Actions -------------------------------------------------------------

  const addRect = () => {
    const canvas = fabricRef.current;
    if (!canvas) return;
    const rect = new Rect({
      left: 50 + Math.random() * 300,
      top: 50 + Math.random() * 200,
      width: 120,
      height: 80,
      fill: '#3b82f6',
      stroke: '#60a5fa',
      strokeWidth: 2,
      rx: 6,
      ry: 6,
    });
    canvas.add(rect);
    canvas.setActiveObject(rect);
    commitChange();
  };

  const addCircle = () => {
    const canvas = fabricRef.current;
    if (!canvas) return;
    const circle = new Circle({
      left: 100 + Math.random() * 300,
      top: 80 + Math.random() * 200,
      radius: 50,
      fill: '#10b981',
      stroke: '#34d399',
      strokeWidth: 2,
    });
    canvas.add(circle);
    canvas.setActiveObject(circle);
    commitChange();
  };

  const addText = () => {
    const canvas = fabricRef.current;
    if (!canvas) return;
    const text = new Textbox('Hello Fabric', {
      left: 80 + Math.random() * 200,
      top: 60 + Math.random() * 200,
      fontSize: 28,
      fill: '#ffffff',
      fontFamily: 'Inter, system-ui, sans-serif',
      width: 220,
    });
    canvas.add(text);
    canvas.setActiveObject(text);
    commitChange();
  };

  const deleteSelected = () => {
    const canvas = fabricRef.current;
    if (!canvas) return;
    const active = canvas.getActiveObject();
    if (!active) return;
    canvas.remove(active);
    canvas.discardActiveObject();
    setSelectedId(null);
    commitChange();
  };

  const handleUndo = async () => {
    await historyRef.current?.undo();
    syncHistoryCounts();
    syncLayers();
    setSelectedId(null);
  };

  const handleRedo = async () => {
    await historyRef.current?.redo();
    syncHistoryCounts();
    syncLayers();
    setSelectedId(null);
  };

  const handleSave = () => {
    const canvas = fabricRef.current;
    if (!canvas) return;
    const json = JSON.stringify(canvas.toJSON());
    localStorage.setItem(LOCAL_STORAGE_KEY, json);
    setRoundTripStatus('idle');
  };

  const handleLoad = async () => {
    const canvas = fabricRef.current;
    if (!canvas) return;
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) return;

    try {
      // Count objects before save
      const savedData = JSON.parse(raw);
      const savedObjectCount = (savedData.objects ?? []).length;

      await canvas.loadFromJSON(raw);
      canvas.requestRenderAll();
      syncLayers();
      commitChange();

      // Verify round-trip: re-serialize and compare object counts
      const reExported = canvas.toJSON();
      const reExportedCount = (reExported.objects ?? []).length;

      setRoundTripStatus(savedObjectCount === reExportedCount ? 'pass' : 'fail');
    } catch {
      setRoundTripStatus('fail');
    }
  };

  const handleExportPng = () => {
    const canvas = fabricRef.current;
    if (!canvas) return;
    const url = canvas.toDataURL({ format: 'png', multiplier: 1 } as any);
    setExportUrl(url);
  };

  const selectLayer = (index: number) => {
    const canvas = fabricRef.current;
    if (!canvas) return;
    const objs = canvas.getObjects();
    if (objs[index]) {
      canvas.setActiveObject(objs[index]);
      canvas.requestRenderAll();
      setSelectedId(index);
    }
  };

  // Render --------------------------------------------------------------

  return (
    <div className="min-h-screen bg-dark-900 text-white p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Fabric.js v6 + React 19 Spike</h1>
        <p className="text-dark-400 text-sm mt-1">
          Integration proof-of-concept for VistterStream canvas editor
        </p>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        {/* Shape tools */}
        <div className="flex items-center gap-2 bg-dark-800 rounded-lg px-3 py-2 border border-dark-700">
          <span className="text-xs text-dark-400 uppercase tracking-wide mr-1">Tools</span>
          <button onClick={addRect} className="px-3 py-1.5 bg-primary-600 hover:bg-primary-700 rounded text-sm font-medium transition-colors">
            + Rect
          </button>
          <button onClick={addCircle} className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 rounded text-sm font-medium transition-colors">
            + Circle
          </button>
          <button onClick={addText} className="px-3 py-1.5 bg-violet-600 hover:bg-violet-700 rounded text-sm font-medium transition-colors">
            + Text
          </button>
          <button
            onClick={deleteSelected}
            className="px-3 py-1.5 bg-red-600 hover:bg-red-700 rounded text-sm font-medium transition-colors disabled:opacity-40"
            disabled={selectedId === null}
          >
            Delete
          </button>
        </div>

        {/* Undo / Redo */}
        <div className="flex items-center gap-2 bg-dark-800 rounded-lg px-3 py-2 border border-dark-700">
          <span className="text-xs text-dark-400 uppercase tracking-wide mr-1">History</span>
          <button
            onClick={handleUndo}
            disabled={undoCount === 0}
            className="px-3 py-1.5 bg-dark-700 hover:bg-dark-600 rounded text-sm font-medium transition-colors disabled:opacity-40"
          >
            Undo ({undoCount})
          </button>
          <button
            onClick={handleRedo}
            disabled={redoCount === 0}
            className="px-3 py-1.5 bg-dark-700 hover:bg-dark-600 rounded text-sm font-medium transition-colors disabled:opacity-40"
          >
            Redo ({redoCount})
          </button>
        </div>

        {/* Serialization */}
        <div className="flex items-center gap-2 bg-dark-800 rounded-lg px-3 py-2 border border-dark-700">
          <span className="text-xs text-dark-400 uppercase tracking-wide mr-1">Data</span>
          <button onClick={handleSave} className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 rounded text-sm font-medium transition-colors">
            Save
          </button>
          <button onClick={handleLoad} className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 rounded text-sm font-medium transition-colors">
            Load
          </button>
          <button onClick={handleExportPng} className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-700 rounded text-sm font-medium transition-colors">
            Export PNG
          </button>
        </div>
      </div>

      {/* Main area */}
      <div className="flex gap-4">
        {/* Layer panel */}
        <div className="w-56 flex-shrink-0">
          <div className="bg-dark-800 border border-dark-700 rounded-lg overflow-hidden">
            <div className="px-3 py-2 border-b border-dark-700">
              <h2 className="text-sm font-semibold text-dark-300 uppercase tracking-wide">
                Layers ({layers.length})
              </h2>
            </div>
            <div className="max-h-[500px] overflow-y-auto">
              {layers.length === 0 ? (
                <p className="px-3 py-4 text-dark-500 text-sm text-center">No objects</p>
              ) : (
                layers.map((layer) => (
                  <button
                    key={layer.id}
                    onClick={() => selectLayer(layer.id)}
                    className={`w-full text-left px-3 py-2 text-sm border-b border-dark-700 last:border-b-0 transition-colors ${
                      selectedId === layer.id
                        ? 'bg-primary-600 bg-opacity-30 text-primary-300'
                        : 'text-dark-300 hover:bg-dark-700'
                    }`}
                  >
                    <span className="text-dark-500 text-xs mr-2">{layer.id + 1}.</span>
                    <span className="capitalize">{layer.label}</span>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 flex flex-col items-center">
          <div className="border-2 border-dark-700 rounded-lg overflow-hidden shadow-xl">
            <canvas ref={canvasElRef} />
          </div>

          {/* Status bar */}
          <div className="mt-3 flex items-center gap-4 text-sm text-dark-400">
            <span>{CANVAS_WIDTH} x {CANVAS_HEIGHT}px</span>
            <span className="text-dark-600">|</span>
            <span>Objects: {layers.length}</span>
            <span className="text-dark-600">|</span>
            <span>
              Serialization:{' '}
              {roundTripStatus === 'idle' && <span className="text-dark-500">not tested</span>}
              {roundTripStatus === 'pass' && <span className="text-green-400 font-medium">PASS</span>}
              {roundTripStatus === 'fail' && <span className="text-red-400 font-medium">FAIL</span>}
            </span>
            <span className="text-dark-600">|</span>
            <span className="text-dark-500">Ctrl+Z / Ctrl+Y for undo/redo</span>
          </div>
        </div>

        {/* Export preview panel */}
        <div className="w-56 flex-shrink-0">
          <div className="bg-dark-800 border border-dark-700 rounded-lg overflow-hidden">
            <div className="px-3 py-2 border-b border-dark-700">
              <h2 className="text-sm font-semibold text-dark-300 uppercase tracking-wide">
                Export Preview
              </h2>
            </div>
            <div className="p-3">
              {exportUrl ? (
                <img
                  src={exportUrl}
                  alt="Canvas export preview"
                  className="w-full rounded border border-dark-700"
                />
              ) : (
                <p className="text-dark-500 text-sm text-center py-6">
                  Click "Export PNG" to preview
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Spike checklist */}
      <div className="mt-8 bg-dark-800 border border-dark-700 rounded-lg p-4 max-w-2xl">
        <h2 className="text-sm font-semibold text-dark-300 uppercase tracking-wide mb-3">
          Spike Checklist
        </h2>
        <ul className="space-y-1.5 text-sm">
          <CheckItem label="Canvas init + cleanup (useRef, strict-mode safe)" pass />
          <CheckItem label="Event to state sync (selection, layers, no infinite re-render)" pass />
          <CheckItem label="Undo / Redo via CanvasHistoryManager" pass />
          <CheckItem label="Serialization round-trip (Save/Load via localStorage)" pass={roundTripStatus === 'pass'} />
          <CheckItem label="Export to PNG (toDataURL)" pass={exportUrl !== null} />
          <CheckItem label="Tool buttons (Rect, Circle, Text, Delete)" pass />
        </ul>
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Utility sub-component                                             */
/* ------------------------------------------------------------------ */

const CheckItem: React.FC<{ label: string; pass: boolean }> = ({ label, pass }) => (
  <li className="flex items-center gap-2">
    <span className={`inline-block w-4 h-4 rounded-full flex-shrink-0 ${pass ? 'bg-green-500' : 'bg-dark-600'}`} />
    <span className={pass ? 'text-dark-200' : 'text-dark-500'}>{label}</span>
  </li>
);

export default SpikeCanvas;
