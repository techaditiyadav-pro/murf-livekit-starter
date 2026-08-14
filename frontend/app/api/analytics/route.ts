import { NextResponse } from 'next/server';
import fs from 'fs';
import { DatabaseSync } from 'node:sqlite';
import path from 'path';

export async function GET() {
  try {
    const dbPath = path.resolve(process.cwd(), '../backend/data/krishimitra.db');
    if (!fs.existsSync(dbPath)) {
      return NextResponse.json({
        total_calls: 0,
        successful_calls: 0,
        failed_calls: 0,
        success_rate: 0.0,
        avg_duration_seconds: 0.0,
        avg_turns: 0.0,
        human_help_count: 0,
        recent_calls: [],
      });
    }

    const database = new DatabaseSync(dbPath);
    database.exec(`
      CREATE TABLE IF NOT EXISTS call_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        call_id TEXT UNIQUE NOT NULL,
        started_at TEXT NOT NULL,
        ended_at TEXT NOT NULL,
        duration_seconds INTEGER NOT NULL DEFAULT 0,
        channel TEXT NOT NULL DEFAULT 'browser',
        outcome TEXT NOT NULL,
        failure_reason TEXT DEFAULT '',
        success_condition TEXT DEFAULT '',
        turns_count INTEGER DEFAULT 0,
        tools_used TEXT DEFAULT '',
        human_help_requested INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
      )
    `);

    try {
      database.exec('ALTER TABLE call_analytics ADD COLUMN turns_count INTEGER DEFAULT 0');
    } catch {}
    try {
      database.exec("ALTER TABLE call_analytics ADD COLUMN tools_used TEXT DEFAULT ''");
    } catch {}
    try {
      database.exec('ALTER TABLE call_analytics ADD COLUMN human_help_requested INTEGER DEFAULT 0');
    } catch {}

    const totalRow = database.prepare('SELECT COUNT(*) as count FROM call_analytics').get() as
      | { count: number }
      | undefined;
    const total_calls = totalRow?.count ?? 0;

    const successRow = database
      .prepare("SELECT COUNT(*) as count FROM call_analytics WHERE outcome = 'SUCCESS'")
      .get() as { count: number } | undefined;
    const successful_calls = successRow?.count ?? 0;

    const failedRow = database
      .prepare("SELECT COUNT(*) as count FROM call_analytics WHERE outcome = 'FAILED'")
      .get() as { count: number } | undefined;
    const failed_calls = failedRow?.count ?? 0;

    const avgDurationRow = database
      .prepare('SELECT AVG(duration_seconds) as avg_duration FROM call_analytics')
      .get() as { avg_duration: number | null } | undefined;
    const avg_duration_seconds =
      total_calls > 0 ? parseFloat((avgDurationRow?.avg_duration ?? 0).toFixed(1)) : 0.0;

    const avgTurnsRow = database
      .prepare('SELECT AVG(turns_count) as avg_turns FROM call_analytics')
      .get() as { avg_turns: number | null } | undefined;
    const avg_turns = total_calls > 0 ? parseFloat((avgTurnsRow?.avg_turns ?? 0).toFixed(1)) : 0.0;

    const humanHelpRow = database
      .prepare(
        "SELECT COUNT(*) as count FROM call_analytics WHERE human_help_requested = 1 OR success_condition LIKE '%Human help%' OR failure_reason LIKE '%escalat%'"
      )
      .get() as { count: number } | undefined;
    const human_help_count = humanHelpRow?.count ?? 0;

    const recent_calls = database
      .prepare('SELECT * FROM call_analytics ORDER BY id DESC LIMIT 50')
      .all();

    database.close();

    const success_rate =
      total_calls > 0 ? parseFloat(((successful_calls / total_calls) * 100).toFixed(1)) : 0.0;

    return NextResponse.json({
      total_calls,
      successful_calls,
      failed_calls,
      success_rate,
      avg_duration_seconds,
      avg_turns,
      human_help_count,
      recent_calls,
    });
  } catch (error) {
    console.error('Failed to query call_analytics database:', error);
    return NextResponse.json(
      {
        error: 'Failed to read call analytics database',
        total_calls: 0,
        successful_calls: 0,
        failed_calls: 0,
        success_rate: 0.0,
        avg_duration_seconds: 0.0,
        avg_turns: 0.0,
        human_help_count: 0,
        recent_calls: [],
      },
      { status: 500 }
    );
  }
}
