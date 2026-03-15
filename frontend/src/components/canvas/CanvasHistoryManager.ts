import { Canvas, classRegistry } from 'fabric';

/**
 * Manages undo/redo history for a Fabric.js Canvas.
 *
 * Uses a canvas getter function instead of a direct reference to handle
 * React StrictMode remounts where the Canvas instance changes.
 *
 * Usage:
 *   const history = new CanvasHistoryManager(() => canvasRef.current?.getCanvas());
 *   history.saveState();          // after every meaningful change
 *   history.undo() / history.redo();
 */
export class CanvasHistoryManager {
  private getCanvas: () => Canvas | null | undefined;
  private history: string[] = [];
  private currentIndex: number = -1;
  private maxHistory: number = 50;
  private isRestoring: boolean = false;

  constructor(getCanvas: () => Canvas | null | undefined) {
    this.getCanvas = getCanvas;
    // Save the initial blank state
    this.saveState();
  }

  /**
   * Snapshot the current canvas JSON into the history stack.
   * No-op while a restore operation is in progress (prevents re-entry).
   */
  saveState(): void {
    if (this.isRestoring) return;

    const canvas = this.getCanvas();
    if (!canvas) return;

    const json = JSON.stringify(canvas.toJSON());

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

    const canvas = this.getCanvas();
    if (!canvas) return;

    this.isRestoring = true;
    try {
      // Fabric.js v6 bug workaround: canvas.loadFromJSON() internally calls
      // clear() → getContext() which can crash. Instead, manually remove all
      // objects and reconstruct them from the serialised JSON.

      // 1. Remove all existing objects (clone — getObjects() is a live array)
      const existing = [...canvas.getObjects()];
      if (existing.length > 0) {
        canvas.remove(...existing);
      }

      // 2. Parse the saved state
      const parsed = JSON.parse(json);

      // 3. Reconstruct and add objects from serialised data
      if (parsed.objects && parsed.objects.length > 0) {
        for (const objData of parsed.objects) {
          try {
            const typeName = objData.type;
            const klass = classRegistry.getClass(typeName);
            if (klass && typeof (klass as any).fromObject === 'function') {
              const obj = await (klass as any).fromObject(objData);
              canvas.add(obj);
            }
          } catch (objErr) {
            console.warn('CanvasHistoryManager: failed to restore object', objData.type, objErr);
          }
        }
      }

      // 4. Restore background colour if present
      if (parsed.background != null) {
        canvas.backgroundColor = parsed.background;
      }

      canvas.requestRenderAll();
    } finally {
      this.isRestoring = false;
    }
  }
}
