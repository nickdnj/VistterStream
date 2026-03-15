import React, { useState, useEffect, useCallback, useRef } from 'react';
import type { FabricObject, Canvas } from 'fabric';

interface ImagePropertiesProps {
  object: FabricObject;
  canvas: Canvas;
  onModified: () => void;
}

const ImageProperties: React.FC<ImagePropertiesProps> = ({ object, canvas, onModified }) => {
  const [opacity, setOpacity] = useState(1);
  const [flipX, setFlipX] = useState(false);
  const [flipY, setFlipY] = useState(false);
  const debounceRef = useRef<NodeJS.Timeout>(undefined);

  const syncFromObject = useCallback(() => {
    setOpacity(object.opacity ?? 1);
    setFlipX(object.flipX ?? false);
    setFlipY(object.flipY ?? false);
  }, [object]);

  useEffect(() => {
    syncFromObject();
  }, [syncFromObject]);

  const apply = (props: Record<string, any>) => {
    object.set(props);
    canvas.requestRenderAll();
    onModified();
  };

  const applyDebounced = (props: Record<string, any>) => {
    object.set(props);
    canvas.requestRenderAll();
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(onModified, 300);
  };

  return (
    <div className="space-y-3">
      <h3 className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Image</h3>

      <div>
        <label className="block text-[10px] text-gray-500 mb-0.5">
          Opacity: {Math.round(opacity * 100)}%
        </label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={opacity}
          onChange={(e) => { const v = parseFloat(e.target.value); setOpacity(v); applyDebounced({ opacity: v }); }}
          className="w-full accent-primary-500"
        />
      </div>

      <div>
        <label className="block text-[10px] text-gray-500 mb-1">Flip</label>
        <div className="flex gap-2">
          <button
            onClick={() => { const v = !flipX; setFlipX(v); apply({ flipX: v }); }}
            className={`flex-1 px-2 py-1 rounded text-xs transition-colors ${flipX ? 'bg-primary-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'}`}
          >
            Flip X
          </button>
          <button
            onClick={() => { const v = !flipY; setFlipY(v); apply({ flipY: v }); }}
            className={`flex-1 px-2 py-1 rounded text-xs transition-colors ${flipY ? 'bg-primary-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'}`}
          >
            Flip Y
          </button>
        </div>
      </div>
    </div>
  );
};

export default ImageProperties;
