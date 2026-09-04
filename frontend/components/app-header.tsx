import { StatusBadge } from "./status-badge";
export function AppHeader({ online, inference }: { online?: boolean; inference?: "ready" | "unavailable" }) {
  return <header><div className="brand"><strong>KHOLLELAB</strong><span>Maths · Réflexion · Démonstration</span></div><div className="meta"><span title="Qwen3-4B · local">IA locale {inference === "ready" ? "● prête" : "○ indisponible"}</span><span>Colle #001</span><StatusBadge online={online} /><b>Prototype</b></div></header>;
}
