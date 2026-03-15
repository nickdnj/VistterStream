/**
 * Shared types for the Canvas Editor.
 * Used by all canvas components as the shared contract.
 */

import type { Canvas, FabricObject } from 'fabric';

export type ActiveTool = 'select' | 'text' | 'rect' | 'circle' | 'line' | 'image';

export type SaveStatus = 'saved' | 'saving' | 'unsaved';

export interface LayerInfo {
  customId: string;
  type: string;
  label: string;
  visible: boolean;
  locked: boolean;
}

export interface FontInfo {
  id: number;
  family: string;
  weight: string;
  style: string;
  source: string;
  file_path: string | null;
}

export interface CanvasProject {
  id: number;
  name: string;
  description: string | null;
  canvas_json: string;
  thumbnail_path: string | null;
  width: number;
  height: number;
  user_id: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface EditorState {
  project: CanvasProject | null;
  activeTool: ActiveTool;
  selectedObject: FabricObject | null;
  layers: LayerInfo[];
  saveStatus: SaveStatus;
  undoCount: number;
  redoCount: number;
  loading: boolean;
  showExport: boolean;
}
