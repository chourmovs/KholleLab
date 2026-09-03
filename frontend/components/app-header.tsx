import { StatusBadge } from "./status-badge";
export function AppHeader({ online }: { online?: boolean }) {
  return <header><div className="brand"><strong>KHOLLELAB</strong><span>Maths · Réflexion · Démonstration</span></div><div className="meta"><span>Colle #001</span><StatusBadge online={online} /><b>Prototype</b></div></header>;
}
