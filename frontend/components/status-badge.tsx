import {CircleCheck,CloudOff} from "lucide-react";
export function StatusBadge({online}:{online?:boolean}){const label=online===undefined?"Connexion…":online?"API en ligne":"API hors ligne";const Icon=online?CircleCheck:CloudOff;return <span className={`status-badge ${online?"success":"warning"}`}><Icon aria-hidden="true"/>{label}</span>}
