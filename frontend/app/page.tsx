"use client";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/app-header";
import { BlackboardPanel } from "@/components/blackboard-panel";
import { ProblemPanel } from "@/components/problem-panel";
import { ProfessorPanel } from "@/components/professor-panel";

export default function Home() {
  const [online, setOnline] = useState<boolean>();
  useEffect(() => { fetch("/api/health", { cache: "no-store" }).then((r) => setOnline(r.ok)).catch(() => setOnline(false)); }, []);
  return <main><div className="shell"><AppHeader online={online} /><div className="workspace"><ProblemPanel /><BlackboardPanel /></div><ProfessorPanel /></div><footer>Khollelab · prototype 0.1.0</footer></main>;
}
