export function StatusBadge({ online }: { online?: boolean }) {
  const label = online === undefined ? "Connexion…" : online ? "Online" : "Offline";
  return <span className={`status ${online ? "online" : ""}`}><i /> API · {label}</span>;
}
