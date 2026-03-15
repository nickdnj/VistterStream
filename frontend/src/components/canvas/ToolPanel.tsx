import React, { useRef } from 'react';
import type { ActiveTool } from './types';
import {
  CursorArrowRaysIcon,
  LanguageIcon,
  StopIcon,
  PhotoIcon,
} from '@heroicons/react/24/outline';

const TOOLS: { tool: ActiveTool; label: string; shortcut: string; icon: React.FC<{ className?: string }> }[] = [
  { tool: 'select', label: 'Select', shortcut: 'V', icon: CursorArrowRaysIcon },
  { tool: 'text', label: 'Text', shortcut: 'T', icon: LanguageIcon },
  { tool: 'rect', label: 'Rectangle', shortcut: 'R', icon: StopIcon },
  {
    tool: 'circle',
    label: 'Circle',
    shortcut: 'C',
    icon: ({ className }) => (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
        <circle cx="12" cy="12" r="9" />
      </svg>
    ),
  },
  {
    tool: 'line',
    label: 'Line',
    shortcut: 'L',
    icon: ({ className }) => (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
        <line x1="4" y1="20" x2="20" y2="4" />
      </svg>
    ),
  },
  { tool: 'image', label: 'Image', shortcut: 'I', icon: PhotoIcon },
];

interface ToolPanelProps {
  activeTool: ActiveTool;
  onToolChange: (tool: ActiveTool) => void;
  onImageSelected: (file: File) => void;
}

const ToolPanel: React.FC<ToolPanelProps> = ({ activeTool, onToolChange, onImageSelected }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleToolClick = (tool: ActiveTool) => {
    if (tool === 'image') {
      fileInputRef.current?.click();
    } else {
      onToolChange(tool);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onImageSelected(file);
      // Reset so same file can be selected again
      e.target.value = '';
    }
  };

  return (
    <div className="w-12 flex flex-col items-center py-2 gap-1 bg-dark-800 border-r border-dark-700">
      {TOOLS.map(({ tool, label, shortcut, icon: Icon }) => (
        <button
          key={tool}
          onClick={() => handleToolClick(tool)}
          title={`${label} (${shortcut})`}
          className={`w-10 h-10 flex items-center justify-center rounded-lg transition-colors ${
            activeTool === tool
              ? 'bg-primary-600 text-white'
              : 'text-gray-400 hover:bg-dark-700 hover:text-gray-200'
          }`}
        >
          <Icon className="h-5 w-5" />
        </button>
      ))}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />
    </div>
  );
};

export default ToolPanel;
