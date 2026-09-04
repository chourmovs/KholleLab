import type { MathEquationEditorHandle } from "./MathEquationEditor";

/** Deterministic insertion target for a blackboard containing several fields. */
export class MathFieldRegistry {
  private fields = new Map<string, MathEquationEditorHandle>();
  activeBlockId?: string;
  register(id: string, field: MathEquationEditorHandle) { this.fields.set(id, field); }
  unregister(id: string) { this.fields.delete(id); if (this.activeBlockId === id) this.activeBlockId = undefined; }
  activate(id: string) { if (this.fields.has(id)) this.activeBlockId = id; }
  getActive() { return this.activeBlockId ? this.fields.get(this.activeBlockId) : undefined; }
  insertMathTemplate(template: string) { this.getActive()?.insert(template); }
}
