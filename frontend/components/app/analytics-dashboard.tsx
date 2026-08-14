'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  BarChart3,
  CheckCircle2,
  Clock,
  Headset,
  MessageSquare,
  PhoneCall,
  RefreshCw,
  Sprout,
  Wrench,
  XCircle,
} from 'lucide-react';

type AnalyticsData = {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  human_help_calls: number;
  tool_usage_calls: number;
  avg_duration_seconds: number;
  avg_turns: number;
  success_rate: number;
  recent_calls: RecentCall[];
};

type RecentCall = {
  call_id: string;
  started_at: string;
  ended_at: string;
  duration_seconds: number;
  channel: string;
  outcome: string;
  turns_count?: number;
  user_turns?: number;
  tools_used?: string[];
  used_search?: number;
  human_help_requested?: number;
  language?: string | null;
  failure_reason?: string | null;
  success_condition?: string | null;
  created_at: string;
};

function StatCard({
  icon,
  label,
  value,
  accent,
  subtext,
}: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  accent: string;
  subtext?: string;
}) {
  return (
    <div
      className="flex flex-col items-center gap-2 rounded-2xl border bg-white p-5 shadow-sm transition-all hover:shadow-md"
      style={{ borderColor: accent + '30' }}
    >
      <div
        className="flex size-11 items-center justify-center rounded-full"
        style={{ backgroundColor: accent + '15', color: accent }}
      >
        {icon}
      </div>
      <p className="text-xs font-semibold tracking-wider text-stone-500 uppercase">{label}</p>
      <p className="text-3xl font-extrabold" style={{ color: accent }}>
        {value}
      </p>
      {subtext && <p className="text-[11px] text-stone-400">{subtext}</p>}
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return '0s';
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function formatToolName(tool: string): string {
  switch (tool) {
    case 'get_weather_by_district':
      return '🌦️ Weather';
    case 'get_market_price':
      return '💰 Mandi Price';
    case 'save_farmer_memory':
      return '🧠 Save Memory';
    case 'lookup_farmer':
      return '🔍 Farmer Lookup';
    case 'create_escalation':
      return '🆘 Human Help';
    case 'handoff_to_crop_specialist':
      return '🌿 Crop Specialist';
    case 'opt_out_of_outbound_calls':
      return '🚫 Outbound Opt-Out';
    default:
      return tool;
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
    <main className="min-h-svh bg-gradient-to-b from-green-50/70 via-stone-50 to-stone-100 p-4 text-stone-900 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-xl font-bold text-green-800 sm:text-2xl">
              <Sprout className="size-6 text-green-700" /> KrishiMitra AI – Call Analytics
            </div>
            <h1 className="mt-1 text-2xl font-bold text-stone-800 sm:text-3xl">
              Farm &amp; Field Voice Agent Performance
            </h1>
            <p className="mt-1 text-xs text-stone-500 sm:text-sm">
              Day 8 | Live voice session metrics, conversation turns, tool usage, and human-help
              tracking
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => void load()}
              className="flex items-center gap-1.5 rounded-lg border border-green-300 bg-white px-3.5 py-2 text-sm font-medium text-green-700 shadow-sm transition hover:bg-green-50 active:scale-95"
            >
              <RefreshCw className="size-4" /> Refresh
            </button>
            <Link
              href="/"
              className="rounded-lg border border-stone-300 bg-white px-3.5 py-2 text-sm font-medium text-stone-600 shadow-sm transition hover:bg-stone-50"
            >
              ← Back to Agent
            </Link>
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            <strong>⚠️ Error:</strong> {error}
          </div>
        )}

        {/* Loading state */}
        {loading && !data && (
          <div className="flex flex-col items-center justify-center py-20 text-stone-500">
            <RefreshCw className="mb-3 size-8 animate-spin text-green-600" />
            <p className="font-medium">Loading call analytics...</p>
          </div>
        )}

        {/* Analytics Content */}
        {data && (
          <>
            {/* KPI Cards Grid */}
            <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <StatCard
                icon={<PhoneCall className="size-5" />}
                label="Total Calls"
                value={data.total_calls}
                accent="#1f6a36"
                subtext="All logged sessions"
              />
              <StatCard
                icon={<BarChart3 className="size-5" />}
                label="Success Rate"
                value={`${data.success_rate}%`}
                accent="#2563eb"
                subtext={`${data.successful_calls} successful`}
              />
              <StatCard
                icon={<Clock className="size-5" />}
                label="Avg Duration"
                value={formatDuration(Math.round(data.avg_duration_seconds || 0))}
                accent="#d97706"
                subtext="Per call session"
              />
              <StatCard
                icon={<MessageSquare className="size-5" />}
                label="Avg Turns"
                value={data.avg_turns || 0}
                accent="#7c3aed"
                subtext="Turns per session"
              />
              <StatCard
                icon={<Headset className="size-5" />}
                label="Human Help"
                value={data.human_help_calls || 0}
                accent="#dc2626"
                subtext="Escalations requested"
              />
              <StatCard
                icon={<Wrench className="size-5" />}
                label="Tool Usage"
                value={data.tool_usage_calls || 0}
                accent="#0891b2"
                subtext="Weather / Search / DB"
              />
            </div>

            {/* Performance Breakdown / Success Bar */}
            {data.total_calls > 0 && (
              <div className="mb-6 rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 className="text-sm font-bold tracking-wider text-stone-700 uppercase">
                      Overall Outcome Breakdown
                    </h3>
                    <p className="text-xs text-stone-500">
                      Ratio of successful calls, human-help escalations, and failed calls
                    </p>
                  </div>
                  <div className="flex items-center gap-4 text-xs font-semibold">
                    <span className="flex items-center gap-1.5 text-green-700">
                      <span className="size-2.5 rounded-full bg-green-500" /> Successful (
                      {data.successful_calls})
                    </span>
                    <span className="flex items-center gap-1.5 text-red-600">
                      <span className="size-2.5 rounded-full bg-red-500" /> Failed (
                      {data.failed_calls})
                    </span>
                    <span className="flex items-center gap-1.5 text-amber-600">
                      <span className="size-2.5 rounded-full bg-amber-500" /> Human Help (
                      {data.human_help_calls})
                    </span>
                  </div>
                </div>

                <div className="mt-3 flex h-3.5 w-full overflow-hidden rounded-full bg-stone-100">
                  <div
                    className="h-full bg-green-500 transition-all duration-700"
                    style={{
                      width: `${data.total_calls > 0 ? (data.successful_calls / data.total_calls) * 100 : 0}%`,
                    }}
                    title={`Successful: ${data.successful_calls}`}
                  />
                  <div
                    className="h-full bg-red-400 transition-all duration-700"
                    style={{
                      width: `${data.total_calls > 0 ? (data.failed_calls / data.total_calls) * 100 : 0}%`,
                    }}
                    title={`Failed: ${data.failed_calls}`}
                  />
                </div>
              </div>
            )}

            {/* Recent Calls Table */}
            <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
              <div className="border-b border-stone-100 bg-green-50/60 px-5 py-3.5">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-bold text-green-900">Recent Call Records</h2>
                    <p className="text-xs text-stone-500">
                      Individual session logs with duration, turns, tools used, and status
                    </p>
                  </div>
                  <span className="rounded-full bg-green-200/60 px-2.5 py-0.5 text-xs font-semibold text-green-800">
                    {data.recent_calls.length} records
                  </span>
                </div>
              </div>

              {data.recent_calls.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center text-stone-400">
                  <PhoneCall className="mb-2 size-9 text-stone-300" />
                  <p className="text-base font-medium text-stone-600">No calls recorded yet.</p>
                  <p className="mt-1 text-xs text-stone-400">
                    Start a conversation with KrishiMitra to see analytics here.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[760px] text-left text-sm">
                    <thead className="border-b border-stone-100 bg-stone-50 text-xs font-semibold tracking-wider text-stone-500 uppercase">
                      <tr>
                        <th className="p-3.5">Date &amp; Time</th>
                        <th className="p-3.5">Duration</th>
                        <th className="p-3.5">Channel</th>
                        <th className="p-3.5">Status</th>
                        <th className="p-3.5">Turns</th>
                        <th className="p-3.5">Tools Used</th>
                        <th className="p-3.5">Human Help</th>
                        <th className="p-3.5">Outcome Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-100">
                      {data.recent_calls.map((call) => {
                        const isSuccess =
                          call.outcome === 'SUCCESS' ||
                          call.outcome === 'COMPLETED' ||
                          call.outcome === 'HUMAN_HELP';
                        const hasHumanHelp =
                          Boolean(call.human_help_requested) || call.outcome === 'HUMAN_HELP';
                        const toolsList = Array.isArray(call.tools_used) ? call.tools_used : [];

                        return (
                          <tr key={call.call_id} className="transition hover:bg-stone-50/70">
                            <td className="p-3.5 text-stone-700">
                              <div className="flex items-center gap-1.5 font-medium">
                                <Clock className="size-3.5 text-stone-400" />
                                {formatTime(call.started_at)}
                              </div>
                              <span className="font-mono text-[10px] text-stone-400">
                                {call.call_id.length > 18
                                  ? `${call.call_id.slice(0, 18)}…`
                                  : call.call_id}
                              </span>
                            </td>

                            <td className="p-3.5 font-mono text-sm font-semibold text-stone-700">
                              {formatDuration(call.duration_seconds)}
                            </td>

                            <td className="p-3.5">
                              <span className="inline-flex items-center rounded-md bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-700">
                                {call.channel === 'sip' ? '📞 SIP' : '🌐 Browser'}
                              </span>
                            </td>

                            <td className="p-3.5">
                              {isSuccess ? (
                                <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-bold text-green-800">
                                  <CheckCircle2 className="size-3 text-green-600" /> SUCCESS
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-bold text-red-800">
                                  <XCircle className="size-3 text-red-600" /> FAILED
                                </span>
                              )}
                            </td>

                            <td className="p-3.5 text-xs text-stone-600">
                              <span className="font-semibold text-stone-800">
                                {call.turns_count ?? call.user_turns ?? 0}
                              </span>{' '}
                              <span className="text-[11px] text-stone-400">
                                ({call.user_turns ?? 0} user)
                              </span>
                            </td>

                            <td className="p-3.5">
                              {toolsList.length > 0 ? (
                                <div className="flex flex-wrap gap-1">
                                  {toolsList.map((t) => (
                                    <span
                                      key={t}
                                      className="rounded border border-blue-200 bg-blue-50 px-1.5 py-0.5 text-[11px] font-medium text-blue-700"
                                    >
                                      {formatToolName(t)}
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <span className="text-xs text-stone-400">—</span>
                              )}
                            </td>

                            <td className="p-3.5">
                              {hasHumanHelp ? (
                                <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800">
                                  <Headset className="size-3 text-amber-600" /> Requested
                                </span>
                              ) : (
                                <span className="text-xs text-stone-400">No</span>
                              )}
                            </td>

                            <td className="max-w-[220px] p-3.5 text-xs text-stone-600">
                              <p className="truncate font-medium">
                                {isSuccess
                                  ? call.success_condition || 'Normal conversation'
                                  : call.failure_reason || 'Incomplete call'}
                              </p>
                              {call.language && (
                                <span className="text-[10px] text-stone-400">
                                  Lang: {call.language}
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Auto-refresh note */}
            {lastRefresh && (
              <p className="mt-4 text-center text-xs text-stone-400">
                Auto-refreshes every 10s · Last synced at {lastRefresh.toLocaleTimeString()}
              </p>
            )}
          </>
        )}

        {/* Empty state when 0 total calls */}
        {data && data.total_calls === 0 && !error && (
          <div className="mt-6 rounded-2xl border border-dashed border-green-300 bg-white p-10 text-center shadow-sm">
            <Sprout className="mx-auto size-12 text-green-600" />
            <h3 className="mt-3 text-lg font-bold text-stone-800">No calls recorded yet</h3>
            <p className="mx-auto mt-1 max-w-md text-sm text-stone-500">
              Start a conversation with KrishiMitra to see real-time analytics, duration metrics,
              and tool invocations here.
            </p>
            <Link
              href="/"
              className="mt-5 inline-block rounded-xl bg-green-700 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-green-800"
            >
              🎙️ Start a Call
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}
