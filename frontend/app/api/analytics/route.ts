import { NextResponse } from 'next/server';

const escalationApiUrl = process.env.ESCALATION_API_URL ?? 'http://127.0.0.1:8001';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const response = await fetch(`${escalationApiUrl}/api/analytics`, { cache: 'no-store' });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ error: 'Analytics service is unavailable.' }, { status: 503 });
  }
}
