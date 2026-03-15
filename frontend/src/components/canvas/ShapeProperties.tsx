import React, { useState, useEffect, useCallback, useRef } from 'react';
import type { FabricObject, Canvas, Rect } from 'fabric';
import ColorPicker from './ColorPicker';

interface ShapePropertiesProps {
  object: FabricObject;
  canvas: Canvas;
  onModified: () => void;
}

const ShapeProperties: React.FC<ShapePropertiesProps> = ({ object, canvas, onModified }) => {
  const [fill, setFill] = useState('#3b82f6');
  const [stroke, setStroke] = useState('#000000');
  const [strokeWidth, setStrokeWidth] = useState(0);
  const [opacity, setOpacity] = useState(1);
  const [cornerRadius, setCornerRadius] = useState(0);
  const debounceRef = useRef<NodeJS.Timeout>(undefined);

  const isRect = object.type === 'rect';

  const syncFromObject = useCallback(() => {
    setFill((object.fill as string) ?? '#3b82f6');
    setStroke((object.stroke as string) ?? '#000000');
    setStrokeWidth(object.strokeWidth ?? 0);
    setOpacity(object.opacity ?? 1);
    if (isRect) {
      setCornerRadius((object as Rect).rx ?? 0);
    }
  }, [object, isRect]);

  useEffect(() => {
    syncFromObject();
  }, [syncFromObject]);

  const apply = (props: Record<string, any>) => {
    object.set(props);
    canvas.requestRenderAll();
    onModified();
  };

  // Debounce slider changes
  const applyDebounced = (props: Record<string, any>) => {
    object.set(props);
    canvas.requestRenderAll();
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(onModified, 300);
  };

  return (
    <div className="space-y-3">
      <h3 className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Shape</h3>

      <ColorPicker label="Fill" color={fill} onChange={(v) => { setFill(v); apply({ fill: v }); }} />
      <ColorPicker label="Stroke" color={stroke} onChange={(v) => { setStroke(v); apply({ stroke: v }); }} />

      <div>
        <label className="block text-[10px] text-gray-500 mb-0.5">Stroke Width</label>
        <input
          type="number"
          value={strokeWidth}
          min={0}
          max={50}
          onChange={(e) => { const v = parseInt(e.target.value) || 0; setStrokeWidth(v); apply({ strokeWidth: v }); }}
          className="w-full px-2 py-1 bg-dark-700 border border-dark-600 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
        />
      </div>

      {isRect && (
        <div>
          <label className="block text-[10px] text-gray-500 mb-0.5">Corner Radius</label>
          <input
            type="number"
            value={cornerRadius}
            min={0}
            max={200}
            onChange={(e) => { const v = parseInt(e.target.value) || 0; setCornerRadius(v); apply({ rx: v, ry: v }); }}
            className="w-full px-2 py-1 bg-dark-700 border border-dark-600 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
      )}

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
    </div>
  );
};

export default ShapeProperties;
