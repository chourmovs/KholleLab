"use client";
import Image from "next/image";
import {UserRound} from "lucide-react";
import type {Account} from "@/lib/api";

export function LandingHeader({account,onAccount}:{account:Account|null;onAccount:()=>void}){
 const identity=account?.authenticated?(account.display_name||account.email?.split("@")[0]||"Mon compte"):"Se connecter";
 return <header className="landing-header"><a className="landing-brand" href="#contenu" aria-label="KHOLLELAB, aller au contenu"><Image src="/assets/brand/khollelab-logo-dark.svg" alt="KHOLLELAB" width={500} height={125} style={{width:"100%",height:"auto"}} priority/></a><nav aria-label="Compte"><button className="landing-account" onClick={onAccount} aria-label={account?.authenticated?`Ouvrir le compte de ${identity}`:"Se connecter"}><UserRound aria-hidden="true"/><span>{identity}</span></button></nav></header>
}
