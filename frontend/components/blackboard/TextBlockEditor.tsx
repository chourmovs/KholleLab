"use client";
import { useEffect, useRef } from "react";
export function TextBlockEditor({ value, onChange, onAddMath, label }: { value: string; onChange: (value: string) => void; onAddMath: () => void; label: string }) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { const node = ref.current; if (node) { node.style.height = "0"; node.style.height = `${Math.max(72, node.scrollHeight)}px`; } }, [value]);
  return <textarea ref={ref} className="text-block" aria-label={label} value={value} spellCheck placeholder="Expliquez votre raisonnement…" onChange={(event) => onChange(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) { event.preventDefault(); onAddMath(); } }} />;
}
