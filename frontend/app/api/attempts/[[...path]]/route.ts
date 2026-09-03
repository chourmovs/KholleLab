import {NextRequest,NextResponse} from "next/server";
export const dynamic="force-dynamic";
async function proxy(request:NextRequest,{params}:{params:Promise<{path?:string[]}>}){try{const {path=[]}=await params;const url=`${process.env.BACKEND_URL??"http://localhost:8000"}/api/attempts/${path.join("/")}`.replace(/\/$/,"");const response=await fetch(url,{method:request.method,body:request.method==="GET"?undefined:await request.text(),headers:{"content-type":"application/json"},cache:"no-store"});return new NextResponse(await response.text(),{status:response.status,headers:{"content-type":"application/json"}})}catch{return NextResponse.json({error:"backend_unavailable",message:"Backend unavailable"},{status:503})}}
export const GET=proxy;export const POST=proxy;export const PATCH=proxy;
