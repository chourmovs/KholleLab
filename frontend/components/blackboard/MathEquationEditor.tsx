"use client";
import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import type { MathfieldElement } from "mathlive";

export interface MathEquationEditorHandle {
  focus: () => void;
  insert: (latex: string) => void;
  getValue: () => string;
}

export const MathEquationEditor = forwardRef<MathEquationEditorHandle, {
  value: string; readOnly?: boolean; onChange: (latex: string) => void;
  onFocus?: () => void; onEnter?: () => void; onDeleteEmpty?: () => void; label?: string;
}>(function MathEquationEditor({ value, readOnly = false, onChange, onFocus, onEnter, onDeleteEmpty, label = "Équation mathématique" }, forwardedRef) {
  const host = useRef<HTMLDivElement>(null);
  const field = useRef<MathfieldElement | null>(null);
  const onChangeRef = useRef(onChange); onChangeRef.current = onChange;
  useImperativeHandle(forwardedRef, () => ({
    focus: () => field.current?.focus(),
    insert: (latex) => {
      const mf=field.current;if(!mf)return;
      if(latex==="moveToPreviousChar"||latex==="moveToNextChar"||latex==="deleteBackward") mf.executeCommand(latex);
      else mf.insert(latex,{insertionMode:"replaceSelection",selectionMode:"placeholder"});
      mf.focus();
    },
    getValue: () => field.current?.value ?? "",
  }), []);
  useEffect(() => {
    let disposed = false;
    const hostElement = host.current;
    void import("mathlive").then(() => {
      if (disposed || !host.current) return;
      const mf = document.createElement("math-field") as MathfieldElement;
      mf.value = value; mf.readOnly = readOnly; mf.mathVirtualKeyboardPolicy = "manual";
      mf.setAttribute("aria-label", label); mf.setAttribute("data-testid", "math-field");
      mf.addEventListener("input", () => onChangeRef.current(mf.value));
      mf.addEventListener("focus", () => onFocus?.());
      mf.addEventListener("keydown", (event) => {
        if (event.key === "Enter") { event.preventDefault(); onEnter?.(); }
        if (event.key === "Backspace" && !mf.value) onDeleteEmpty?.();
      });
      host.current.replaceChildren(mf); field.current = mf;
    });
    return () => { disposed = true; field.current = null; hostElement?.replaceChildren(); };
    // The element is intentionally created once; controlled updates are below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { if (field.current && field.current.value !== value) field.current.value = value; }, [value]);
  useEffect(() => { if (field.current) field.current.readOnly = readOnly; }, [readOnly]);
  return <div ref={host} className="math-field-host" />;
});
