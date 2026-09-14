import type {Account} from "@/lib/api";
import {LandingHeader} from "@/components/landing/landing-header";
export function OnboardingHeader({account,onAccount}:{account:Account|null;onAccount:()=>void}){return <LandingHeader account={account} onAccount={onAccount}/>}
