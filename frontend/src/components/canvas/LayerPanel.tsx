import React, { useRef } from 'react';
import type { Canvas, FabricObject } from 'fabric';
import type { LayerInfo } from './types';
import LayerItem from './LayerItem';

interface LayerPanelProps {
  layers: LayerInfo[];
  selectedCustomId: string | null;
  canvas: Canvas | null;
  onSelect: (customId: string) => void;
  onModified: () => void;
  onLayersChanged: () => void;
}

const LayerPanel: React.FC<LayerPanelProps> = ({
  layers,
  selectedCustomId,
  canvas,
  onSelect,
  onModified,
  onLayersChanged,
}) => {
  const dragIndexRef = useRef<number | null>(null);

  const findObject = (customId: string): FabricObject | undefined => {
    return canvas?.getObjects().find((o: any) => o.customId === customId);
  };

  const handleToggleVisibility = (customId: string) => {
    const obj = findObject(customId);
    if (!obj || !canvas) return;
    obj.set({ visible: !obj.visible });
    canvas.requestRenderAll();
    onLayersChanged();
  };

  const handleToggleLock = (customId: string) => {
    const obj = findObject(customId);
    if (!obj || !canvas) return;
    const locked = !obj.selectable;
    obj.set({
      selectable: !locked,
      evented: !locked,
    });
    canvas.requestRenderAll();
    onLayersChanged();
  };

  const handleDelete = (customId: string) => {
    const obj = findObject(customId);
    if (!obj || !canvas) return;
    canvas.remove(obj);
    canvas.discardActiveObject();
    canvas.requestRenderAll();
    onModified();
    onLayersChanged();
  };

  const handleRename = (customId: string, name: string) => {
    const obj = findObject(customId);
    if (!obj) return;
    (obj as any).customName = name;
    onLayersChanged();
  };

  // DnD reordering
  const handleDragStart = (index: number) => (e: React.DragEvent) => {
    dragIndexRef.current = index;
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (_index: number) => (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (dropIndex: number) => (e: React.DragEvent) => {
    e.preventDefault();
    const fromIndex = dragIndexRef.current;
    if (fromIndex === null || fromIndex === dropIndex || !canvas) return;

    const allObjects = canvas.getObjects();
    // layers are in reverse order (top layer = first in list, last in canvas stack)
    const canvasFromIndex = allObjects.length - 1 - fromIndex;
    const canvasToIndex = allObjects.length - 1 - dropIndex;

    const obj = allObjects[canvasFromIndex];
    if (!obj) return;

    // Fabric v6: reorder by removing and re-adding at target index
    canvas.remove(obj);
    const remaining = canvas.getObjects();
    // Insert at the target position
    const insertIdx = Math.min(canvasToIndex, remaining.length);
    canvas.insertAt(insertIdx, obj);
    canvas.requestRenderAll();
    onModified();
    onLayersChanged();
    dragIndexRef.current = null;
  };

  // Layers displayed top-to-bottom (top of stack first)
  const reversedLayers = [...layers].reverse();

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-dark-700">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Layers ({layers.length})
        </h2>
      </div>
      <div className="flex-1 overflow-y-auto">
        {reversedLayers.length === 0 ? (
          <p className="px-3 py-6 text-gray-600 text-xs text-center">No objects on canvas</p>
        ) : (
          reversedLayers.map((layer, i) => (
            <LayerItem
              key={layer.customId}
              layer={layer}
              isSelected={layer.customId === selectedCustomId}
              onSelect={() => onSelect(layer.customId)}
              onToggleVisibility={() => handleToggleVisibility(layer.customId)}
              onToggleLock={() => handleToggleLock(layer.customId)}
              onDelete={() => handleDelete(layer.customId)}
              onRename={(name) => handleRename(layer.customId, name)}
              dragHandlers={{
                draggable: true,
                onDragStart: handleDragStart(i),
                onDragOver: handleDragOver(i),
                onDrop: handleDrop(i),
              }}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default LayerPanel;
