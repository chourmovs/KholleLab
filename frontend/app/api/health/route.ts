import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export async function GET() {
  try {
    const response = await fetch(`${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    const body = await response.json();
    return NextResponse.json(body, { status: response.status });
  } catch {
    return NextResponse.json({ status: "error", database: "unknown" }, { status: 503 });
  }
}
