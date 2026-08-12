import { NextResponse } from 'next/server';
import fs from 'fs';
import { DatabaseSync } from 'node:sqlite';
import path from 'path';

export async function GET() {
  try {
    const dbPath = path.resolve(process.cwd(), '../backend/data/krishimitra.db');
    if (!fs.existsSync(dbPath)) {
      return NextResponse.json({ alerts: [] });
    }

    const database = new DatabaseSync(dbPath);
    const rows = database.prepare('SELECT * FROM farm_alerts ORDER BY id ASC').all();
    database.close();

    return NextResponse.json({ alerts: rows });
  } catch (error) {
    console.error('Failed to query farm_alerts database:', error);
    return NextResponse.json(
      { error: 'Failed to read farm alerts database', alerts: [] },
      { status: 500 }
    );
  }
}
