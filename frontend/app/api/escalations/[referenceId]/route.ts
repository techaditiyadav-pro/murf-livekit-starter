import { NextResponse } from 'next/server';

const escalationApiUrl = process.env.ESCALATION_API_URL ?? 'http://127.0.0.1:8001';

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ referenceId: string }> }
) {
  const { referenceId } = await params;
  try {
    const response = await fetch(
      `${escalationApiUrl}/api/escalations/${encodeURIComponent(referenceId)}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(await request.json()),
      }
    );
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ error: 'Human-support service is unavailable.' }, { status: 503 });
  }
}
