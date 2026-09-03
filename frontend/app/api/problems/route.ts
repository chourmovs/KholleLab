import { NextResponse } from "next/server";
export const dynamic="force-dynamic";
export async function GET(){try{const response=await fetch(`${process.env.BACKEND_URL??"http://localhost:8000"}/api/problems`,{cache:"no-store"});return new NextResponse(await response.text(),{status:response.status,headers:{"content-type":"application/json"}})}catch{return NextResponse.json({detail:"Backend unavailable"},{status:503})}}
