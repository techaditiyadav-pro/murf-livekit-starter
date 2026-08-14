'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Clock,
  Headset,
  MessageSquare,
  Phone,
  RefreshCw,
  Wrench,
  XCircle,
} from 'lucide-react';
import { NavHeader } from '@/components/app/nav-header';
import { Button } from '@/components/ui/button';

interface CallAnalyticsRecord {
  id: number;
  call_id: string;
  started_at: string;
  ended_at: string;
  duration_seconds: number;
  channel: string;
  outcome: string;
  failure_reason?: string;
  success_condition?: string;
  turns_count?: number;
  tools_used?: string;
  human_help_requested?: number;
  created_at: string;
}

interface AnalyticsSummary {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  success_rate: number;
  avg_duration_seconds: number;
  avg_turns: number;
  human_help_count: number;
  recent_calls: CallAnalyticsRecord[];
}

export default function CallAnalyticsDashboardPage() {
  const [data, setData] = useState<AnalyticsSummary>({
    total_calls: 0,
    successful_calls: 0,
    failed_calls: 0,
    success_rate: 0,
    avg_duration_seconds: 0,
    avg_turns: 0,
    human_help_count: 0,
    recent_calls: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/analytics');
      if (!res.ok) throw new Error('Failed to load call analytics data');
      const json = await res.json();
      setData({
        total_calls: json.total_calls ?? 0,
        successful_calls: json.successful_calls ?? 0,
        failed_calls: json.failed_calls ?? 0,
        success_rate: json.success_rate ?? 0,
        avg_duration_seconds: json.avg_duration_seconds ?? 0,
        avg_turns: json.avg_turns ?? 0,
        human_help_count: json.human_help_count ?? 0,
        recent_calls: json.recent_calls ?? [],
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error fetching call analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 8000);
    return () => clearInterval(interval);
  }, []);

  const formatDuration = (seconds: number) => {
    if (!seconds || seconds <= 0) return '0s';
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  return (
    <div className="bg-background text-foreground flex min-h-svh flex-col">
      <NavHeader />

      <main className="farm-shell flex-1 px-4 py-8 sm:px-6">
        <div className="mx-auto max-w-6xl">
          {/* Top Header */}
          <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <Link
                href="/"
                className="text-primary mb-2 inline-flex items-center gap-1.5 text-sm font-semibold hover:underline"
              >
                <ArrowLeft className="size-4" /> Back to KrishiMitra
              </Link>
              <h1 className="flex items-center gap-2.5 text-2xl font-bold sm:text-3xl">
                <BarChart3 className="size-7 text-emerald-600" /> KrishiMitra AI – Call Analytics
              </h1>
              <p className="text-muted-foreground mt-1 text-sm">
                Farm &amp; Field Voice Agent Performance
              </p>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={fetchAnalytics}
              disabled={loading}
              className="flex items-center gap-1.5 self-start rounded-xl sm:self-auto"
            >
              <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </Button>
          </div>

          {error && (
            <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
              {error}
            </div>
          )}

          {/* 5 KPI Metric Cards */}
          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {/* Total Calls */}
            <div className="farm-card p-5 transition hover:shadow-md">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-xs font-bold tracking-wider uppercase">
                  Total Calls
                </span>
                <div className="bg-primary/10 text-primary flex size-8 items-center justify-center rounded-xl">
                  <Phone className="size-4" />
                </div>
              </div>
              <p className="mt-2 text-3xl font-extrabold tracking-tight">{data.total_calls}</p>
              <p className="text-muted-foreground mt-1 text-xs font-medium">Completed sessions</p>
            </div>

            {/* Success Rate */}
            <div className="farm-card border-emerald-500/20 bg-emerald-50/30 p-5 transition hover:shadow-md dark:bg-emerald-950/10">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold tracking-wider text-emerald-800 uppercase dark:text-emerald-300">
                  Success Rate
                </span>
                <div className="flex size-8 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300">
                  <CheckCircle2 className="size-4" />
                </div>
              </div>
              <p className="mt-2 text-3xl font-extrabold tracking-tight text-emerald-700 dark:text-emerald-400">
                {data.success_rate}%
              </p>
              <div className="bg-secondary mt-2 h-1.5 w-full overflow-hidden rounded-full">
                <div
                  className="h-full bg-emerald-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(0, data.success_rate))}%` }}
                />
              </div>
            </div>

            {/* Avg Call Duration */}
            <div className="farm-card p-5 transition hover:shadow-md">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-xs font-bold tracking-wider uppercase">
                  Avg Duration
                </span>
                <div className="bg-primary/10 text-primary flex size-8 items-center justify-center rounded-xl">
                  <Clock className="size-4" />
                </div>
              </div>
              <p className="mt-2 text-3xl font-extrabold tracking-tight">
                {formatDuration(data.avg_duration_seconds)}
              </p>
              <p className="text-muted-foreground mt-1 text-xs font-medium">Average session time</p>
            </div>

            {/* Avg Conversation Turns */}
            <div className="farm-card p-5 transition hover:shadow-md">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-xs font-bold tracking-wider uppercase">
                  Avg Turns
                </span>
                <div className="bg-primary/10 text-primary flex size-8 items-center justify-center rounded-xl">
                  <MessageSquare className="size-4" />
                </div>
              </div>
              <p className="mt-2 text-3xl font-extrabold tracking-tight">{data.avg_turns}</p>
              <p className="text-muted-foreground mt-1 text-xs font-medium">Turns per call</p>
            </div>

            {/* Human Help Requests */}
            <div className="farm-card border-amber-500/20 bg-amber-50/30 p-5 transition hover:shadow-md dark:bg-amber-950/10">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold tracking-wider text-amber-800 uppercase dark:text-amber-300">
                  Human Help
                </span>
                <div className="flex size-8 items-center justify-center rounded-xl bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300">
                  <Headset className="size-4" />
                </div>
              </div>
              <p className="mt-2 text-3xl font-extrabold tracking-tight text-amber-800 dark:text-amber-400">
                {data.human_help_count}
              </p>
              <p className="mt-1 text-xs font-medium text-amber-800/80 dark:text-amber-400/80">
                Escalations requested
              </p>
            </div>
          </div>

          {/* Recent Call Records Table */}
          <div className="farm-card overflow-hidden">
            <div className="border-border flex items-center justify-between border-b p-5">
              <h2 className="flex items-center gap-2 text-lg font-bold">
                <Clock className="size-5 text-emerald-600" /> Recent Call Execution Logs
              </h2>
              <span className="text-muted-foreground font-mono text-xs">
                {data.recent_calls.length} call{data.recent_calls.length === 1 ? '' : 's'} recorded
              </span>
            </div>

            {!data.recent_calls.length && !loading ? (
              <div className="text-muted-foreground p-10 text-center">
                <p className="text-4xl">📞</p>
                <p className="text-foreground mt-3 text-lg font-bold">No calls recorded yet.</p>
                <p className="mt-1 text-sm">
                  Start a conversation with KrishiMitra to see analytics here.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-secondary/40 border-border text-muted-foreground border-b text-xs uppercase">
                    <tr>
                      <th className="px-4 py-3 font-bold">Date &amp; Time</th>
                      <th className="px-4 py-3 font-bold">Call ID</th>
                      <th className="px-4 py-3 font-bold">Channel</th>
                      <th className="px-4 py-3 font-bold">Status</th>
                      <th className="px-4 py-3 font-bold">Duration</th>
                      <th className="px-4 py-3 font-bold">Turns</th>
                      <th className="px-4 py-3 font-bold">Tools Used</th>
                      <th className="px-4 py-3 font-bold">Human Help</th>
                    </tr>
                  </thead>
                  <tbody className="divide-border divide-y">
                    {data.recent_calls.map((call) => {
                      const isSuccess = call.outcome.toUpperCase() === 'SUCCESS';
                      const hasHumanHelp =
                        Boolean(call.human_help_requested) ||
                        Boolean(call.success_condition?.toLowerCase().includes('human help')) ||
                        Boolean(call.failure_reason?.toLowerCase().includes('escalat'));
                      return (
                        <tr key={call.id} className="hover:bg-secondary/20 transition">
                          <td className="text-muted-foreground px-4 py-3 font-mono text-xs whitespace-nowrap">
                            {new Date(call.started_at).toLocaleString()}
                          </td>
                          <td className="text-foreground max-w-[140px] truncate px-4 py-3 font-mono text-xs font-semibold">
                            {call.call_id}
                          </td>
                          <td className="px-4 py-3">
                            <span className="bg-secondary inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold uppercase">
                              {call.channel}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            {isSuccess ? (
                              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                                <CheckCircle2 className="size-3" /> SUCCESS
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 rounded-full border border-rose-200 bg-rose-100 px-2.5 py-0.5 text-xs font-bold text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-300">
                                <XCircle className="size-3" /> FAILED
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 font-mono text-xs">
                            {formatDuration(call.duration_seconds)}
                          </td>
                          <td className="px-4 py-3 font-mono text-xs font-semibold">
                            {call.turns_count ?? 0}
                          </td>
                          <td className="px-4 py-3 text-xs">
                            {call.tools_used ? (
                              <span className="bg-secondary inline-flex items-center gap-1 rounded px-2 py-0.5 font-mono text-xs">
                                <Wrench className="text-muted-foreground size-3" />
                                {call.tools_used}
                              </span>
                            ) : (
                              <span className="text-muted-foreground font-mono text-xs">None</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {hasHumanHelp ? (
                              <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-bold text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                                <Headset className="size-3" /> Requested
                              </span>
                            ) : (
                              <span className="text-muted-foreground text-xs">No</span>
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
        </div>
      </main>
    </div>
  );
}
