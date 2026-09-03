import { NextRequest, NextResponse } from "next/server";
export const dynamic="force-dynamic";
export async function GET(_request:NextRequest,{params}:{params:Promise<{path:string[]}>}){try{const {path}=await params;const response=await fetch(`${process.env.BACKEND_URL??"http://localhost:8000"}/api/problems/${path.join("/")}`,{cache:"no-store"});return new NextResponse(await response.text(),{status:response.status,headers:{"content-type":response.headers.get("content-type")??"application/json"}})}catch{return NextResponse.json({detail:"Backend unavailable"},{status:503})}}
