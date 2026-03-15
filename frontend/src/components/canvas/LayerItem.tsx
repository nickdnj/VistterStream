import React, { useState } from 'react';
import {
  EyeIcon,
  EyeSlashIcon,
  LockClosedIcon,
  LockOpenIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import type { LayerInfo } from './types';

const TYPE_ICONS: Record<string, string> = {
  textbox: 'T',
  'i-text': 'T',
  text: 'T',
  rect: 'R',
  circle: 'C',
  line: 'L',
  image: 'I',
};

interface LayerItemProps {
  layer: LayerInfo;
  isSelected: boolean;
  onSelect: () => void;
  onToggleVisibility: () => void;
  onToggleLock: () => void;
  onDelete: () => void;
  onRename: (name: string) => void;
  dragHandlers: {
    draggable: boolean;
    onDragStart: (e: React.DragEvent) => void;
    onDragOver: (e: React.DragEvent) => void;
    onDrop: (e: React.DragEvent) => void;
  };
}

const LayerItem: React.FC<LayerItemProps> = ({
  layer,
  isSelected,
  onSelect,
  onToggleVisibility,
  onToggleLock,
  onDelete,
  onRename,
  dragHandlers,
}) => {
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(layer.label);

  const icon = TYPE_ICONS[layer.type] || '?';

  const commitRename = () => {
    setEditing(false);
    if (editName.trim() && editName !== layer.label) {
      onRename(editName.trim());
    } else {
      setEditName(layer.label);
    }
  };

  return (
    <div
      className={`flex items-center gap-1.5 px-2 py-1.5 border-b border-dark-700 last:border-b-0 cursor-pointer transition-colors ${
        isSelected
          ? 'bg-primary-600/20 text-primary-300'
          : 'text-gray-300 hover:bg-dark-700'
      } ${!layer.visible ? 'opacity-40' : ''}`}
      onClick={onSelect}
      {...dragHandlers}
    >
      {/* Drag handle */}
      <span className="text-gray-600 cursor-grab text-xs select-none">&#x2630;</span>

      {/* Type icon */}
      <span className="w-5 h-5 bg-dark-600 rounded text-[10px] flex items-center justify-center font-mono text-gray-400 flex-shrink-0">
        {icon}
      </span>

      {/* Name */}
      {editing ? (
        <input
          type="text"
          value={editName}
          onChange={(e) => setEditName(e.target.value)}
          onBlur={commitRename}
          onKeyDown={(e) => { if (e.key === 'Enter') commitRename(); if (e.key === 'Escape') { setEditing(false); setEditName(layer.label); } }}
          className="flex-1 min-w-0 px-1 py-0 bg-dark-600 border border-dark-500 rounded text-xs text-white focus:outline-none"
          autoFocus
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <span
          className="flex-1 min-w-0 truncate text-xs"
          onDoubleClick={(e) => { e.stopPropagation(); setEditing(true); setEditName(layer.label); }}
        >
          {layer.label}
        </span>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-0.5 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
        <button onClick={onToggleVisibility} className="p-0.5 hover:text-white transition-colors" title={layer.visible ? 'Hide' : 'Show'}>
          {layer.visible ? <EyeIcon className="h-3 w-3" /> : <EyeSlashIcon className="h-3 w-3" />}
        </button>
        <button onClick={onToggleLock} className="p-0.5 hover:text-white transition-colors" title={layer.locked ? 'Unlock' : 'Lock'}>
          {layer.locked ? <LockClosedIcon className="h-3 w-3" /> : <LockOpenIcon className="h-3 w-3" />}
        </button>
        <button onClick={onDelete} className="p-0.5 hover:text-red-400 transition-colors" title="Delete">
          <TrashIcon className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
};

export default LayerItem;
