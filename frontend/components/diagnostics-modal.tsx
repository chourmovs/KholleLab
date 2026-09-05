"use client";

import { useCallback, useEffect, useState } from "react";
import { getDiagnostics, getDiagnosticLogs, testInference, type InferenceDiagnostics } from "@/lib/api";

type Tab = "diagnostic" | "application" | "inference";
const TOKEN_KEY = "khollelab.diagnostics.token";

export function DiagnosticsModal({ onClose, initialTab = "diagnostic" }: { onClose: () => void; initialTab?: Tab }) {
  const [tab, setTab] = useState<Tab>(initialTab);
  const [token, setToken] = useState(() => typeof window === "undefined" ? "" : sessionStorage.getItem(TOKEN_KEY) || "");
  const [tokenInput, setTokenInput] = useState("");
  const [diagnostic, setDiagnostic] = useState<InferenceDiagnostics>();
  const [logs, setLogs] = useState<string[]>([]);
  const [lineCount, setLineCount] = useState(200);
  const [error, setError] = useState("");
  const [completion, setCompletion] = useState("Non testé");

  const refresh = useCallback(async (currentTab: Tab, secret: string, lines = 200) => {
    setError("");
    try {
      if (currentTab === "diagnostic") setDiagnostic(await getDiagnostics(secret));
      else setLogs((await getDiagnosticLogs(currentTab, secret, lines)).lines);
    } catch (cause) {
      setError(cause instanceof Error && cause.message.includes("invalide") ? "Accès diagnostics refusé." : "Diagnostics indisponibles.");
    }
  }, []);

  useEffect(() => {
    if (token) queueMicrotask(() => void refresh(initialTab, token, 200));
  }, [initialTab, refresh, token]);

  function submitToken(event: React.FormEvent) {
    event.preventDefault();
    const secret = tokenInput.trim();
    if (!secret) return;
    sessionStorage.setItem(TOKEN_KEY, secret);
    setToken(secret);
    setTokenInput("");
    void refresh(tab, secret, lineCount);
  }

  function changeToken() {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken("");
    setError("");
  }

  async function runTest() {
    const value = await testInference(token);
    setCompletion(value.status === "pass"
      ? `PASS · ${value.latency_ms} ms · “${value.response_preview}”`
      : `FAIL · ${value.error_code || value.reason || "UNKNOWN"}`);
  }

  const checks = diagnostic?.checks;
  return <section className="diagnostics-modal" role="dialog" aria-modal="true" aria-label="Logs & diagnostics">
    <header><b>LOGS &amp; DIAGNOSTICS</b><button onClick={onClose} aria-label="Fermer">×</button></header>
    {!token ? <form onSubmit={submitToken} className="diagnostics-token">
      <label htmlFor="diagnostics-token">Token diagnostics</label>
      <input id="diagnostics-token" type="password" autoComplete="off" value={tokenInput} onChange={event => setTokenInput(event.target.value)} autoFocus />
      <button type="submit">Accéder</button>
    </form> : <>
      <p>IA locale : {diagnostic?.status === "ready" ? "● prête" : "⚠ indisponible"}</p>
      <p>Provider : {diagnostic?.provider || "—"}<br />Modèle : {diagnostic?.model || "—"} · {diagnostic?.quantization || "—"}</p>
      <nav>{(["diagnostic", "application", "inference"] as Tab[]).map(value => <button className={tab === value ? "active" : ""} onClick={() => { setTab(value); void refresh(value, token, lineCount); }} key={value}>{value === "diagnostic" ? "Diagnostic" : value === "application" ? "Application" : "Inference"}</button>)}</nav>
      {error && <p role="alert" className="diagnostics-error">{error}</p>}
      {tab === "diagnostic" ? <div className="diagnostic-grid">
        <span>Provider config</span><b>{checks?.provider_config?.toUpperCase() || "—"}</b>
        <span>DNS inference</span><b>{checks?.dns?.toUpperCase() || "—"}</b>
        <span>TCP :8080</span><b>{checks?.tcp_8080?.toUpperCase() || "—"}</b>
        <span>/health</span><b>{checks?.health?.toUpperCase() || "—"}</b>
        <span>/v1/models</span><b>{checks?.models?.toUpperCase() || "—"}</b>
        <span>Test inference</span><b>{completion}</b>
        <button onClick={() => void runTest().catch(() => setCompletion("FAIL · UNAVAILABLE"))}>Tester l&apos;inférence</button>
      </div> : <><div className="log-lines">Lignes : {[100, 200, 500].map(count => <button className={lineCount === count ? "active" : ""} key={count} onClick={() => { setLineCount(count); void refresh(tab, token, count); }}>{count}</button>)}</div><pre>{logs.length ? logs.join("\n") : "Aucun journal disponible."}</pre></>}
      <footer><button onClick={() => void refresh(tab, token, lineCount)}>Actualiser</button>{tab !== "diagnostic" && <button onClick={() => void navigator.clipboard.writeText(logs.join("\n"))}>Copier</button>}<button onClick={changeToken}>Changer le token</button></footer>
    </>}
  </section>;
}
