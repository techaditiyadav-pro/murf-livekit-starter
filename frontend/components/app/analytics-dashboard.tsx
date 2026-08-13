'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  BarChart3,
  CheckCircle2,
  Clock,
  PhoneCall,
  RefreshCw,
  Sprout,
  XCircle,
} from 'lucide-react';

type AnalyticsData = {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  success_rate: number;
  recent_calls: RecentCall[];
};

type RecentCall = {
  call_id: string;
  started_at: string;
  ended_at: string;
  duration_seconds: number;
  channel: string;
  outcome: 'SUCCESS' | 'FAILED';
  failure_reason: string | null;
  success_condition: string | null;
  created_at: string;
};

function StatCard({
  icon,
  label,
  value,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  accent: string;
}) {
  return (
    <div
      className="flex flex-col items-center gap-2 rounded-2xl border bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
      style={{ borderColor: accent + '30' }}
    >
      <div
        className="flex size-12 items-center justify-center rounded-full"
        style={{ backgroundColor: accent + '15', color: accent }}
      >
        {icon}
      </div>
      <p className="text-sm font-medium text-stone-500">{label}</p>
      <p className="text-4xl font-bold" style={{ color: accent }}>
        {value}
      </p>
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function AnalyticsDashboard() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const load = useCallback(async () => {
    try {
      const response = await fetch('/api/analytics', { cache: 'no-store' });
      const json = await response.json();
      if (!response.ok) throw new Error(json.error || 'Failed to load analytics');
      setData(json);
      setError(null);
      setLastRefresh(new Date());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load analytics.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const interval = setInterval(() => void load(), 10_000);
    return () => clearInterval(interval);
  }, [load]);

  return (
    <main className="min-h-svh bg-gradient-to-b from-green-50/60 to-stone-50 p-4 text-stone-900 sm:p-6">
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-xl font-bold text-green-800 sm:text-2xl">
              <Sprout className="size-6" /> KrishiMitra AI
            </div>
            <h1 className="mt-1 text-2xl font-semibold text-stone-800 sm:text-3xl">
              📊 Call Analytics Dashboard
            </h1>
            <p className="mt-1 text-sm text-stone-500">
              Farm &amp; Field — Day 8 | Real-time call metrics from actual conversations
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => void load()}
              className="flex items-center gap-1.5 rounded-lg border border-green-300 bg-white px-3 py-2 text-sm font-medium text-green-700 shadow-sm transition-colors hover:bg-green-50"
            >
              <RefreshCw className="size-4" /> Refresh
            </button>
            <Link
              href="/"
              className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-600 shadow-sm transition-colors hover:bg-stone-50"
            >
              ← Back
            </Link>
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">
            <strong>⚠️ Error:</strong> {error}
          </div>
        )}

        {/* Loading state */}
        {loading && !data && (
          <div className="flex flex-col items-center justify-center py-20 text-stone-500">
            <RefreshCw className="mb-3 size-8 animate-spin text-green-600" />
            <p>Loading analytics...</p>
          </div>
        )}

        {/* Stats cards */}
        {data && (
          <>
            <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                icon={<PhoneCall className="size-6" />}
                label="Total Calls"
                value={data.total_calls}
                accent="#287a3d"
              />
              <StatCard
                icon={<CheckCircle2 className="size-6" />}
                label="Successful Calls"
                value={data.successful_calls}
                accent="#16a34a"
              />
              <StatCard
                icon={<XCircle className="size-6" />}
                label="Failed Calls"
                value={data.failed_calls}
                accent="#dc2626"
              />
              <StatCard
                icon={<BarChart3 className="size-6" />}
                label="Success Rate"
                value={`${data.success_rate}%`}
                accent="#2563eb"
              />
            </div>

            {/* Success bar */}
            {data.total_calls > 0 && (
              <div className="mb-6 overflow-hidden rounded-xl border bg-white p-5 shadow-sm">
                <p className="mb-2 text-sm font-medium text-stone-600">Success Rate</p>
                <div className="h-4 w-full overflow-hidden rounded-full bg-stone-100">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-green-500 to-green-400 transition-all duration-700"
                    style={{ width: `${data.success_rate}%` }}
                  />
                </div>
                <p className="mt-1 text-right text-xs text-stone-400">
                  {data.successful_calls} of {data.total_calls} calls successful
                </p>
              </div>
            )}

            {/* Recent calls table */}
            <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
              <div className="border-b bg-green-50/50 px-5 py-3">
                <h2 className="text-lg font-semibold text-green-800">Recent Calls</h2>
                <p className="text-xs text-stone-500">
                  Safe metadata only — no transcripts or personal data shown
                </p>
              </div>
              {data.recent_calls.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-stone-400">
                  <PhoneCall className="mb-2 size-8" />
                  <p>No calls recorded yet.</p>
                  <p className="mt-1 text-xs">
                    Make a voice call to see analytics here.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[700px] text-left text-sm">
                    <thead className="bg-stone-50 text-stone-600">
                      <tr>
                        <th className="p-3">Time</th>
                        <th className="p-3">Duration</th>
                        <th className="p-3">Channel</th>
                        <th className="p-3">Outcome</th>
                        <th className="p-3">Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.recent_calls.map((call) => (
                        <tr
                          key={call.call_id}
                          className="border-t transition-colors hover:bg-stone-50/50"
                        >
                          <td className="p-3 text-stone-600">
                            <div className="flex items-center gap-1.5">
                              <Clock className="size-3.5 text-stone-400" />
                              {formatTime(call.started_at)}
                            </div>
                          </td>
                          <td className="p-3 font-mono text-stone-700">
                            {formatDuration(call.duration_seconds)}
                          </td>
                          <td className="p-3">
                            <span className="inline-flex items-center rounded-full bg-stone-100 px-2.5 py-0.5 text-xs font-medium text-stone-700">
                              {call.channel === 'sip' ? '📞 SIP' : '🌐 Browser'}
                            </span>
                          </td>
                          <td className="p-3">
                            {call.outcome === 'SUCCESS' ? (
                              <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800">
                                <CheckCircle2 className="size-3" /> SUCCESS
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-800">
                                <XCircle className="size-3" /> FAILED
                              </span>
                            )}
                          </td>
                          <td className="max-w-[200px] truncate p-3 text-xs text-stone-500">
                            {call.outcome === 'SUCCESS'
                              ? call.success_condition || '—'
                              : call.failure_reason || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Auto-refresh indicator */}
            {lastRefresh && (
              <p className="mt-4 text-center text-xs text-stone-400">
                Auto-refreshes every 10 seconds · Last updated:{' '}
                {lastRefresh.toLocaleTimeString()}
              </p>
            )}
          </>
        )}

        {/* Empty state when data loaded but zero calls */}
        {data && data.total_calls === 0 && !error && (
          <div className="mt-4 rounded-xl border border-dashed border-green-300 bg-green-50/30 p-8 text-center">
            <p className="text-lg font-medium text-green-800">🌱 No calls yet</p>
            <p className="mt-1 text-sm text-stone-500">
              Start a voice conversation with KrishiMitra AI and the analytics will
              appear here automatically.
            </p>
            <Link
              href="/"
              className="mt-4 inline-block rounded-lg bg-green-700 px-5 py-2.5 text-sm font-semibold text-white shadow transition-colors hover:bg-green-800"
            >
              🎙️ Start a Call
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}
