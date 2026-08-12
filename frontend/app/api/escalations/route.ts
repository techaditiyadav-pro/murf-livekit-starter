import { NextResponse } from 'next/server';

const escalationApiUrl = process.env.ESCALATION_API_URL ?? 'http://127.0.0.1:8001';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const response = await fetch(`${escalationApiUrl}/api/escalations`, { cache: 'no-store' });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ error: 'Human-support service is unavailable.' }, { status: 503 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const response = await fetch(`${escalationApiUrl}/api/escalations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ error: 'Human-support service is unavailable.' }, { status: 503 });
  }
}
