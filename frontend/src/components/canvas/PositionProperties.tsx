import React, { useState, useEffect, useCallback } from 'react';
import type { FabricObject, Canvas } from 'fabric';
import { LockClosedIcon, LockOpenIcon } from '@heroicons/react/24/outline';

interface PositionPropertiesProps {
  object: FabricObject;
  canvas: Canvas;
  onModified: () => void;
}

const PositionProperties: React.FC<PositionPropertiesProps> = ({ object, canvas, onModified }) => {
  const [aspectLock, setAspectLock] = useState(false);
  const [x, setX] = useState(0);
  const [y, setY] = useState(0);
  const [w, setW] = useState(0);
  const [h, setH] = useState(0);
  const [angle, setAngle] = useState(0);

  const syncFromObject = useCallback(() => {
    setX(Math.round(object.left ?? 0));
    setY(Math.round(object.top ?? 0));
    setW(Math.round((object.width ?? 0) * (object.scaleX ?? 1)));
    setH(Math.round((object.height ?? 0) * (object.scaleY ?? 1)));
    setAngle(Math.round(object.angle ?? 0));
  }, [object]);

  useEffect(() => {
    syncFromObject();
  }, [syncFromObject]);

  const applyChange = (props: Record<string, number>) => {
    object.set(props);
    canvas.requestRenderAll();
    onModified();
    syncFromObject();
  };

  const handleWidthChange = (newW: number) => {
    const baseW = object.width ?? 1;
    const scaleX = newW / baseW;
    if (aspectLock) {
      const ratio = (object.scaleY ?? 1) / (object.scaleX ?? 1);
      applyChange({ scaleX, scaleY: scaleX * ratio });
    } else {
      applyChange({ scaleX });
    }
  };

  const handleHeightChange = (newH: number) => {
    const baseH = object.height ?? 1;
    const scaleY = newH / baseH;
    if (aspectLock) {
      const ratio = (object.scaleX ?? 1) / (object.scaleY ?? 1);
      applyChange({ scaleY, scaleX: scaleY * ratio });
    } else {
      applyChange({ scaleY });
    }
  };

  return (
    <div className="space-y-3">
      <h3 className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Position & Size</h3>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-[10px] text-gray-500 mb-0.5">X</label>
          <input
            type="number"
            value={x}
            onChange={(e) => { const v = parseInt(e.target.value) || 0; setX(v); applyChange({ left: v }); }}
            className="w-full px-2 py-1 bg-dark-700 border border-dark-600 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <div>
          <label className="block text-[10px] text-gray-500 mb-0.5">Y</label>
          <input
            type="number"
            value={y}
            onChange={(e) => { const v = parseInt(e.target.value) || 0; setY(v); applyChange({ top: v }); }}
            className="w-full px-2 py-1 bg-dark-700 border border-dark-600 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] gap-2 items-end">
        <div>
          <label className="block text-[10px] text-gray-500 mb-0.5">W</label>
          <input
            type="number"
            value={w}
            onChange={(e) => handleWidthChange(parseInt(e.target.value) || 1)}
            className="w-full px-2 py-1 bg-dark-700 border border-dark-600 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <button
          onClick={() => setAspectLock(!aspectLock)}
          className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
          title={aspectLock ? 'Unlock aspect ratio' : 'Lock aspect ratio'}
        >
          {aspectLock
            ? <LockClosedIcon className="h-3.5 w-3.5" />
            : <LockOpenIcon className="h-3.5 w-3.5" />}
        </button>
        <div>
          <label className="block text-[10px] text-gray-500 mb-0.5">H</label>
          <input
            type="number"
            value={h}
            onChange={(e) => handleHeightChange(parseInt(e.target.value) || 1)}
            className="w-full px-2 py-1 bg-dark-700 border border-dark-600 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
      </div>

      <div>
        <label className="block text-[10px] text-gray-500 mb-0.5">Rotation</label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={angle}
            onChange={(e) => { const v = parseInt(e.target.value) || 0; setAngle(v); applyChange({ angle: v }); }}
            className="w-20 px-2 py-1 bg-dark-700 border border-dark-600 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
          <span className="text-xs text-gray-500">deg</span>
        </div>
      </div>
    </div>
  );
};

export default PositionProperties;
