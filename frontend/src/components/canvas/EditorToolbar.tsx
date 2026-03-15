import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeftIcon,
  ArrowUturnLeftIcon,
  ArrowUturnRightIcon,
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
} from '@heroicons/react/24/outline';
import type { SaveStatus } from './types';

const STATUS_STYLES: Record<SaveStatus, { text: string; classes: string }> = {
  saved: { text: 'Saved', classes: 'bg-green-900/50 text-green-400' },
  saving: { text: 'Saving...', classes: 'bg-yellow-900/50 text-yellow-400' },
  unsaved: { text: 'Unsaved', classes: 'bg-red-900/50 text-red-400' },
};

interface EditorToolbarProps {
  projectName: string;
  saveStatus: SaveStatus;
  undoCount: number;
  redoCount: number;
  onUndo: () => void;
  onRedo: () => void;
  onSave: () => void;
  onExport: () => void;
}

const EditorToolbar: React.FC<EditorToolbarProps> = ({
  projectName,
  saveStatus,
  undoCount,
  redoCount,
  onUndo,
  onRedo,
  onSave,
  onExport,
}) => {
  const navigate = useNavigate();
  const status = STATUS_STYLES[saveStatus];

  return (
    <div className="h-12 flex items-center px-3 gap-3 bg-dark-800 border-b border-dark-700 flex-shrink-0">
      {/* Back */}
      <button
        onClick={() => navigate('/assets')}
        className="p-1.5 text-gray-400 hover:text-white rounded transition-colors"
        title="Back to Assets"
      >
        <ArrowLeftIcon className="h-5 w-5" />
      </button>

      {/* Separator */}
      <div className="w-px h-6 bg-dark-600" />

      {/* Project name (read-only for MVP) */}
      <span className="text-sm font-medium text-white truncate max-w-[200px]">
        {projectName || 'Untitled Canvas'}
      </span>

      {/* Save status pill */}
      <span className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${status.classes}`}>
        {status.text}
      </span>

      <div className="flex-1" />

      {/* Undo / Redo */}
      <div className="flex items-center gap-1">
        <button
          onClick={onUndo}
          disabled={undoCount === 0}
          className="relative p-1.5 text-gray-400 hover:text-white rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          title="Undo (Ctrl+Z)"
        >
          <ArrowUturnLeftIcon className="h-4 w-4" />
          {undoCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 bg-primary-600 text-white text-[8px] w-3.5 h-3.5 rounded-full flex items-center justify-center">
              {undoCount > 9 ? '9+' : undoCount}
            </span>
          )}
        </button>
        <button
          onClick={onRedo}
          disabled={redoCount === 0}
          className="relative p-1.5 text-gray-400 hover:text-white rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          title="Redo (Ctrl+Y)"
        >
          <ArrowUturnRightIcon className="h-4 w-4" />
          {redoCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 bg-primary-600 text-white text-[8px] w-3.5 h-3.5 rounded-full flex items-center justify-center">
              {redoCount > 9 ? '9+' : redoCount}
            </span>
          )}
        </button>
      </div>

      {/* Separator */}
      <div className="w-px h-6 bg-dark-600" />

      {/* Save */}
      <button
        onClick={onSave}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-300 hover:text-white bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors"
        title="Save (Ctrl+S)"
      >
        <ArrowDownTrayIcon className="h-4 w-4" />
        Save
      </button>

      {/* Export */}
      <button
        onClick={onExport}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
      >
        <ArrowUpTrayIcon className="h-4 w-4" />
        Export
      </button>
    </div>
  );
};

export default EditorToolbar;
