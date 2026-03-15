import { Canvas } from 'fabric';

/**
 * Manages undo/redo history for a Fabric.js Canvas.
 *
 * Usage:
 *   const history = new CanvasHistoryManager(canvas);
 *   history.saveState();          // after every meaningful change
 *   history.undo() / history.redo();
 *
 * Internally prevents re-entrant saves when restoring state.
 */
export class CanvasHistoryManager {
  private canvas: Canvas;
  private history: string[] = [];
  private currentIndex: number = -1;
  private maxHistory: number = 50;
  private isRestoring: boolean = false;

  constructor(canvas: Canvas) {
    this.canvas = canvas;
    // Save the initial blank state
    this.saveState();
  }

  /**
   * Snapshot the current canvas JSON into the history stack.
   * No-op while a restore operation is in progress (prevents re-entry).
   */
  saveState(): void {
    if (this.isRestoring) return;

    const json = JSON.stringify(this.canvas.toJSON());

    // If we are not at the end of the stack, discard any redo states
    if (this.currentIndex < this.history.length - 1) {
      this.history = this.history.slice(0, this.currentIndex + 1);
    }

    this.history.push(json);

    // Enforce maximum history depth
    if (this.history.length > this.maxHistory) {
      this.history.shift();
    }

    this.currentIndex = this.history.length - 1;
  }

  /** Restore the previous state. Returns true if undo was performed. */
  async undo(): Promise<boolean> {
    if (!this.canUndo()) return false;

    this.currentIndex--;
    await this.restore();
    return true;
  }

  /** Restore the next state. Returns true if redo was performed. */
  async redo(): Promise<boolean> {
    if (!this.canRedo()) return false;

    this.currentIndex++;
    await this.restore();
    return true;
  }

  canUndo(): boolean {
    return this.currentIndex > 0;
  }

  canRedo(): boolean {
    return this.currentIndex < this.history.length - 1;
  }

  /** Number of undo steps available */
  get undoCount(): number {
    return this.currentIndex;
  }

  /** Number of redo steps available */
  get redoCount(): number {
    return this.history.length - 1 - this.currentIndex;
  }

  // ---- private ----

  private async restore(): Promise<void> {
    const json = this.history[this.currentIndex];
    if (!json) return;

    this.isRestoring = true;
    try {
      await this.canvas.loadFromJSON(json);
      this.canvas.requestRenderAll();
    } finally {
      this.isRestoring = false;
    }
  }
}
