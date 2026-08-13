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
        created_at TEXT NOT NULL
      )
    `);

    const totalRow = database
      .prepare('SELECT COUNT(*) as count FROM call_analytics')
      .get() as { count: number } | undefined;
    const total_calls = totalRow?.count ?? 0;

    const successRow = database
      .prepare("SELECT COUNT(*) as count FROM call_analytics WHERE outcome = 'SUCCESS'")
      .get() as { count: number } | undefined;
    const successful_calls = successRow?.count ?? 0;

    const failedRow = database
      .prepare("SELECT COUNT(*) as count FROM call_analytics WHERE outcome = 'FAILED'")
      .get() as { count: number } | undefined;
    const failed_calls = failedRow?.count ?? 0;

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
        recent_calls: [],
      },
      { status: 500 }
    );
  }
}
