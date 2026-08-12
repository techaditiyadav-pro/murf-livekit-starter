import { NextResponse } from 'next/server';
import fs from 'fs';
import { DatabaseSync } from 'node:sqlite';
import path from 'path';

function sanitizeInput(text: string): string {
  if (!text) return '';
  let sanitized = text.replace(/\b\d{4,8}\b/g, '[REDACTED_CODE]');
  sanitized = sanitized.replace(/\b\d{13,19}\b/g, '[REDACTED_CARD]');
  const keywords = ['password', 'otp', 'pin', 'cvv', 'bank account'];
  keywords.forEach((kw) => {
    const re = new RegExp(`\\b${kw}\\b\\s*[:=]?\\s*\\S+`, 'gi');
    sanitized = sanitized.replace(re, `${kw}: [REDACTED]`);
  });
  return sanitized.trim();
}

function containsSensitiveInfo(text: string): boolean {
  if (!text) return false;
  const sensitivePatterns = [
    /\b(otp|pin|password|passwd|cvv|bank account|account number|credit card|debit card)\b/i,
    /\b\d{4,8}\b/,
    /\b\d{13,19}\b/,
  ];
  return sensitivePatterns.some((pattern) => pattern.test(text));
}

function getDatabase(): DatabaseSync | null {
  const dbPath = path.resolve(process.cwd(), '../backend/data/krishimitra.db');
  if (!fs.existsSync(dbPath)) {
    return null;
  }
  const db = new DatabaseSync(dbPath);
  db.exec(`
    CREATE TABLE IF NOT EXISTS escalations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      reference_id TEXT UNIQUE NOT NULL,
      farmer_name TEXT NOT NULL,
      reason TEXT NOT NULL,
      problem_summary TEXT NOT NULL,
      what_agent_checked TEXT NOT NULL,
      urgency TEXT NOT NULL,
      language TEXT NOT NULL,
      preferred_follow_up_method TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'OPEN',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  `);
  return db;
}

export async function GET() {
  try {
    const database = getDatabase();
    if (!database) {
      return NextResponse.json({ escalations: [] });
    }

    const rows = database.prepare('SELECT * FROM escalations ORDER BY id DESC').all();
    database.close();

    return NextResponse.json({ escalations: rows });
  } catch (error) {
    console.error('Failed to query escalations database:', error);
    return NextResponse.json(
      { error: 'Failed to read escalations database', escalations: [] },
      { status: 500 }
    );
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const {
      farmer_name,
      reason,
      problem_summary,
      what_agent_checked,
      urgency,
      language,
      preferred_follow_up_method,
      permission_granted,
    } = body;

    if (!permission_granted) {
      return NextResponse.json(
        { error: 'Your request was not submitted because permission is required.' },
        { status: 400 }
      );
    }

    if (!farmer_name || !farmer_name.trim()) {
      return NextResponse.json({ error: 'Farmer name is required.' }, { status: 400 });
    }

    if (!problem_summary || !problem_summary.trim()) {
      return NextResponse.json({ error: 'Problem description is required.' }, { status: 400 });
    }

    if (containsSensitiveInfo(problem_summary)) {
      return NextResponse.json(
        {
          error:
            'Please remove sensitive information such as OTPs, PINs, passwords, or bank details before submitting.',
        },
        { status: 400 }
      );
    }

    const database = getDatabase();
    if (!database) {
      return NextResponse.json(
        { error: 'Database is unavailable right now. Please try again.' },
        { status: 500 }
      );
    }

    const cleanName = farmer_name.trim();
    const cleanReason = (reason || 'OTHER').trim();
    const cleanSummary = sanitizeInput(problem_summary);
    const cleanChecked = sanitizeInput(
      what_agent_checked || 'User requested human support directly.'
    );
    const cleanUrgency = (urgency || 'medium').toLowerCase();
    const cleanLang = language || 'Hindi';
    const cleanFollowUp = preferred_follow_up_method || 'Phone Call';

    // Duplicate check for existing OPEN request
    const existing = database
      .prepare(
        'SELECT * FROM escalations WHERE farmer_name = ? AND reason = ? AND problem_summary = ? AND status = "OPEN" LIMIT 1'
      )
      .get(cleanName, cleanReason, cleanSummary) as Record<string, unknown> | undefined;

    if (existing) {
      database.close();
      return NextResponse.json({
        success: true,
        reference_id: existing.reference_id,
        is_duplicate: true,
        escalation: existing,
      });
    }

    const now = new Date().toISOString();
    const currentYear = new Date().getFullYear();

    const countRow = database
      .prepare('SELECT COUNT(*) as cnt FROM escalations WHERE reference_id LIKE ?')
      .get(`KM-${currentYear}-%`) as { cnt: number } | undefined;

    const seq = (countRow?.cnt ?? 0) + 1;
    const referenceId = `KM-${currentYear}-${String(seq).padStart(4, '0')}`;

    database
      .prepare(
        `INSERT INTO escalations (
          reference_id, farmer_name, reason, problem_summary,
          what_agent_checked, urgency, language, preferred_follow_up_method,
          status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)`
      )
      .run(
        referenceId,
        cleanName,
        cleanReason,
        cleanSummary,
        cleanChecked,
        cleanUrgency,
        cleanLang,
        cleanFollowUp,
        now,
        now
      );

    const created = database
      .prepare('SELECT * FROM escalations WHERE reference_id = ?')
      .get(referenceId);

    database.close();

    return NextResponse.json({
      success: true,
      reference_id: referenceId,
      escalation: created,
    });
  } catch (error) {
    console.error('Failed to create escalation:', error);
    return NextResponse.json(
      { error: 'Unable to create your request right now. Please try again.' },
      { status: 500 }
    );
  }
}

export async function PATCH(req: Request) {
  try {
    const body = await req.json();
    const { reference_id, status } = body;

    if (!reference_id || !status) {
      return NextResponse.json({ error: 'Reference ID and status are required.' }, { status: 400 });
    }

    const validStatuses = ['OPEN', 'IN_PROGRESS', 'RESOLVED'];
    const cleanStatus = status.toUpperCase();
    if (!validStatuses.includes(cleanStatus)) {
      return NextResponse.json({ error: 'Invalid status value.' }, { status: 400 });
    }

    const database = getDatabase();
    if (!database) {
      return NextResponse.json({ error: 'Database unavailable' }, { status: 500 });
    }

    const now = new Date().toISOString();
    database
      .prepare('UPDATE escalations SET status = ?, updated_at = ? WHERE reference_id = ?')
      .run(cleanStatus, now, reference_id);

    const updated = database
      .prepare('SELECT * FROM escalations WHERE reference_id = ?')
      .get(reference_id);

    database.close();

    return NextResponse.json({ success: true, escalation: updated });
  } catch (error) {
    console.error('Failed to update escalation status:', error);
    return NextResponse.json({ error: 'Failed to update escalation' }, { status: 500 });
  }
}
