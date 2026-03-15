import React from 'react';
import type { FabricObject, Canvas } from 'fabric';
import PositionProperties from './PositionProperties';
import TextProperties from './TextProperties';
import ShapeProperties from './ShapeProperties';
import ImageProperties from './ImageProperties';

interface PropertiesPanelProps {
  selectedObject: FabricObject | null;
  canvas: Canvas | null;
  onModified: () => void;
}

const PropertiesPanel: React.FC<PropertiesPanelProps> = ({ selectedObject, canvas, onModified }) => {
  if (!selectedObject || !canvas) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500 text-sm">Select an object to edit its properties</p>
      </div>
    );
  }

  const objType = selectedObject.type ?? 'unknown';
  const isText = objType === 'textbox' || objType === 'i-text' || objType === 'text';
  const isShape = objType === 'rect' || objType === 'circle' || objType === 'line' || objType === 'ellipse' || objType === 'polygon';
  const isImage = objType === 'image';

  return (
    <div className="p-3 space-y-4 overflow-y-auto max-h-full">
      <PositionProperties object={selectedObject} canvas={canvas} onModified={onModified} />

      {isText && (
        <TextProperties object={selectedObject} canvas={canvas} onModified={onModified} />
      )}

      {isShape && (
        <ShapeProperties object={selectedObject} canvas={canvas} onModified={onModified} />
      )}

      {isImage && (
        <ImageProperties object={selectedObject} canvas={canvas} onModified={onModified} />
      )}
    </div>
  );
};

export default PropertiesPanel;
