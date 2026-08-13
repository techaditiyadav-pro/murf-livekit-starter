'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Clock,
  Phone,
  PhoneOff,
  RefreshCw,
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
  created_at: string;
}

interface AnalyticsSummary {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  success_rate: number;
  recent_calls: CallAnalyticsRecord[];
}

export default function CallAnalyticsDashboardPage() {
  const [data, setData] = useState<AnalyticsSummary>({
    total_calls: 0,
    successful_calls: 0,
    failed_calls: 0,
    success_rate: 0,
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
    const interval = setInterval(fetchAnalytics, 10000);
    return () => clearInterval(interval);
  }, []);

  const formatDuration = (seconds: number) => {
    if (!seconds || seconds <= 0) return '0s';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
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
                <BarChart3 className="size-7 text-emerald-600" /> Call Analytics Dashboard
              </h1>
              <p className="text-muted-foreground mt-1 text-sm">
                KrishiMitra AI — Real-time performance &amp; outcome metrics for Farm &amp; Field voice calls.
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
            <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">
              {error}
            </div>
          )}

          {/* 3 Core Metric Cards + Success Rate */}
          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* Total Calls */}
            <div className="farm-card p-6 transition hover:shadow-md">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-xs font-bold uppercase tracking-wider">
                  Total Calls
                </span>
                <div className="bg-primary/10 text-primary flex size-9 items-center justify-center rounded-xl">
                  <Phone className="size-5" />
                </div>
              </div>
              <p className="mt-3 text-4xl font-extrabold tracking-tight">{data.total_calls}</p>
              <p className="text-muted-foreground mt-1 text-xs font-medium">
                Total completed agent sessions
              </p>
            </div>

            {/* Successful Calls */}
            <div className="farm-card border-emerald-500/20 bg-emerald-50/30 dark:bg-emerald-950/10 p-6 transition hover:shadow-md">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-300">
                  Successful Calls
                </span>
                <div className="flex size-9 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300">
                  <CheckCircle2 className="size-5" />
                </div>
              </div>
              <p className="mt-3 text-4xl font-extrabold tracking-tight text-emerald-700 dark:text-emerald-400">
                {data.successful_calls}
              </p>
              <p className="mt-1 text-xs font-medium text-emerald-800/80 dark:text-emerald-400/80">
                Info provided or escalation created
              </p>
            </div>

            {/* Failed Calls */}
            <div className="farm-card border-rose-500/20 bg-rose-50/30 dark:bg-rose-950/10 p-6 transition hover:shadow-md">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-rose-800 dark:text-rose-300">
                  Failed Calls
                </span>
                <div className="flex size-9 items-center justify-center rounded-xl bg-rose-100 text-rose-700 dark:bg-rose-900/50 dark:text-rose-300">
                  <PhoneOff className="size-5" />
                </div>
              </div>
              <p className="mt-3 text-4xl font-extrabold tracking-tight text-rose-700 dark:text-rose-400">
                {data.failed_calls}
              </p>
              <p className="mt-1 text-xs font-medium text-rose-800/80 dark:text-rose-400/80">
                Disconnected before completion
              </p>
            </div>

            {/* Success Rate */}
            <div className="farm-card p-6 transition hover:shadow-md">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-xs font-bold uppercase tracking-wider">
                  Success Rate
                </span>
                <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 font-mono text-xs font-bold text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300">
                  {data.success_rate}%
                </span>
              </div>
              <p className="mt-3 text-4xl font-extrabold tracking-tight">{data.success_rate}%</p>
              <div className="bg-secondary mt-3 h-2 w-full overflow-hidden rounded-full">
                <div
                  className="bg-emerald-500 h-full transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(0, data.success_rate))}%` }}
                />
              </div>
            </div>
          </div>

          {/* Recent Call Records Table */}
          <div className="farm-card overflow-hidden">
            <div className="border-border flex items-center justify-between border-b p-5">
              <h2 className="flex items-center gap-2 text-lg font-bold">
                <Clock className="size-5 text-emerald-600" /> Call Execution History
              </h2>
              <span className="text-muted-foreground font-mono text-xs">
                {data.recent_calls.length} record{data.recent_calls.length === 1 ? '' : 's'}
              </span>
            </div>

            {!data.recent_calls.length && !loading ? (
              <div className="p-10 text-center text-muted-foreground">
                <p className="text-4xl">📞</p>
                <p className="mt-3 text-lg font-bold text-foreground">No Calls Recorded Yet</p>
                <p className="mt-1 text-sm">
                  Start a browser or SIP voice call with KrishiMitra AI to record call metrics.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-secondary/40 border-border text-muted-foreground border-b text-xs uppercase">
                    <tr>
                      <th className="px-4 py-3 font-bold">Call ID</th>
                      <th className="px-4 py-3 font-bold">Channel</th>
                      <th className="px-4 py-3 font-bold">Outcome</th>
                      <th className="px-4 py-3 font-bold">Duration</th>
                      <th className="px-4 py-3 font-bold">Details / Condition</th>
                      <th className="px-4 py-3 font-bold">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-border divide-y">
                    {data.recent_calls.map((call) => {
                      const isSuccess = call.outcome.toUpperCase() === 'SUCCESS';
                      return (
                        <tr key={call.id} className="hover:bg-secondary/20 transition">
                          <td className="px-4 py-3 font-mono text-xs font-semibold text-foreground">
                            {call.call_id}
                          </td>
                          <td className="px-4 py-3">
                            <span className="inline-flex items-center rounded-md bg-secondary px-2 py-0.5 text-xs font-semibold uppercase">
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
                          <td className="px-4 py-3 text-xs max-w-xs truncate">
                            {isSuccess ? (
                              <span className="text-emerald-700 dark:text-emerald-400 font-medium">
                                {call.success_condition || 'Requested information delivered'}
                              </span>
                            ) : (
                              <span className="text-rose-700 dark:text-rose-400">
                                {call.failure_reason || 'Call ended early'}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 font-mono text-xs text-muted-foreground whitespace-nowrap">
                            {new Date(call.started_at).toLocaleString()}
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
