import { StatusBadge } from "./status-badge";
export function AppHeader({ online, inference }: { online?: boolean; inference?: "ready" | "starting" }) {
  return <header><div className="brand"><strong>KHOLLELAB</strong><span>Maths · Réflexion · Démonstration</span></div><div className="meta"><span title="Qwen3-4B · local">{inference === "ready" ? "IA locale ● prête" : "IA locale · téléchargement / démarrage"}</span><span>Colle #001</span><StatusBadge online={online} /><b>Prototype</b></div></header>;
}
