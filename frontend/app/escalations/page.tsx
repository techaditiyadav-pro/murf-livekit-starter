'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  Headset,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react';
import { NavHeader } from '@/components/app/nav-header';
import { Button } from '@/components/ui/button';

interface EscalationRecord {
  id: number;
  reference_id: string;
  farmer_name: string;
  reason: string;
  problem_summary: string;
  what_agent_checked: string;
  urgency: string;
  language: string;
  preferred_follow_up_method: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export default function EscalationsDashboardPage() {
  const [escalations, setEscalations] = useState<EscalationRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatingRef, setUpdatingRef] = useState<string | null>(null);

  const fetchEscalations = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/escalations');
      if (!res.ok) throw new Error('Failed to fetch escalations data');
      const data = await res.json();
      setEscalations(data.escalations || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error loading escalations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEscalations();
    const interval = setInterval(fetchEscalations, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStatusUpdate = async (reference_id: string, newStatus: string) => {
    setUpdatingRef(reference_id);
    try {
      const res = await fetch('/api/escalations', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reference_id, status: newStatus }),
      });
      if (!res.ok) throw new Error('Failed to update status');
      await fetchEscalations();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update status');
    } finally {
      setUpdatingRef(null);
    }
  };

  const getUrgencyBadge = (urgency: string) => {
    switch (urgency.toLowerCase()) {
      case 'emergency':
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-red-200 bg-red-100 px-2.5 py-0.5 text-xs font-bold text-red-800">
            <ShieldAlert className="size-3" /> Emergency
          </span>
        );
      case 'high':
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-orange-200 bg-orange-100 px-2.5 py-0.5 text-xs font-bold text-orange-800">
            <AlertTriangle className="size-3" /> High
          </span>
        );
      case 'low':
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-slate-700">
            Low
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-100 px-2.5 py-0.5 text-xs font-bold text-blue-800">
            Medium
          </span>
        );
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'RESOLVED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-800">
            <CheckCircle2 className="size-3" /> RESOLVED
          </span>
        );
      case 'IN_PROGRESS':
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-100 px-2.5 py-0.5 text-xs font-bold text-amber-800">
            <Clock className="size-3" /> IN PROGRESS
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-100 px-2.5 py-0.5 text-xs font-bold text-blue-800">
            <Clock className="size-3" /> OPEN
          </span>
        );
    }
  };

  return (
    <div className="bg-background text-foreground flex min-h-svh flex-col">
      <NavHeader />

      <main className="farm-shell flex-1 px-4 py-8 sm:px-6">
        <div className="mx-auto max-w-5xl">
          <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <Link
                href="/"
                className="text-primary mb-2 inline-flex items-center gap-1.5 text-sm font-semibold hover:underline"
              >
                <ArrowLeft className="size-4" /> Back to KrishiMitra
              </Link>
              <h1 className="flex items-center gap-2 text-2xl font-bold sm:text-3xl">
                <Headset className="size-7 text-amber-600" /> Human Help Support Dashboard
              </h1>
              <p className="text-muted-foreground mt-1 text-sm">
                Review and update open human support requests from farmers.
              </p>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={fetchEscalations}
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

          {!escalations.length && !loading ? (
            <div className="farm-card text-muted-foreground p-10 text-center">
              <p className="text-4xl">🌾</p>
              <p className="text-foreground mt-3 text-lg font-bold">No Human Help Requests Yet</p>
              <p className="mt-1 text-sm">
                Requests submitted via the voice agent or /help page will appear here.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {escalations.map((rec) => (
                <div key={rec.id} className="farm-card p-5 transition hover:shadow-md sm:p-6">
                  <div className="border-border flex flex-col justify-between gap-3 border-b pb-3 sm:flex-row sm:items-center">
                    <div className="flex items-center gap-3">
                      <span className="rounded-xl bg-amber-100 px-3 py-1 font-mono text-lg font-bold text-amber-900">
                        {rec.reference_id}
                      </span>
                      {getStatusBadge(rec.status)}
                      {getUrgencyBadge(rec.urgency)}
                    </div>
                    <span className="text-muted-foreground font-mono text-xs">
                      {new Date(rec.created_at).toLocaleString()}
                    </span>
                  </div>

                  <div className="mt-4 grid grid-cols-1 gap-4 text-sm leading-6 md:grid-cols-2">
                    <div>
                      <p className="text-muted-foreground text-xs font-semibold uppercase">
                        Farmer Name
                      </p>
                      <p className="text-foreground font-bold">{rec.farmer_name}</p>
                    </div>

                    <div>
                      <p className="text-muted-foreground text-xs font-semibold uppercase">
                        Reason
                      </p>
                      <p className="text-foreground font-semibold">{rec.reason}</p>
                    </div>

                    <div className="md:col-span-2">
                      <p className="text-muted-foreground text-xs font-semibold uppercase">
                        Problem Summary
                      </p>
                      <p className="bg-secondary/40 text-foreground mt-1 rounded-xl p-3 text-sm font-medium">
                        {rec.problem_summary}
                      </p>
                    </div>

                    {rec.what_agent_checked && (
                      <div className="md:col-span-2">
                        <p className="text-muted-foreground text-xs font-semibold uppercase">
                          What Agent Checked
                        </p>
                        <p className="text-muted-foreground mt-0.5 text-xs italic">
                          {rec.what_agent_checked}
                        </p>
                      </div>
                    )}

                    <div>
                      <p className="text-muted-foreground text-xs font-semibold uppercase">
                        Preferred Follow-up
                      </p>
                      <p className="font-medium">{rec.preferred_follow_up_method}</p>
                    </div>

                    <div>
                      <p className="text-muted-foreground text-xs font-semibold uppercase">
                        Language
                      </p>
                      <p className="font-medium">{rec.language}</p>
                    </div>
                  </div>

                  <div className="border-border mt-5 flex items-center justify-end gap-2 border-t pt-3">
                    <span className="text-muted-foreground mr-2 text-xs font-semibold">
                      Update Status:
                    </span>
                    {['OPEN', 'IN_PROGRESS', 'RESOLVED'].map((st) => (
                      <button
                        key={st}
                        type="button"
                        disabled={
                          updatingRef === rec.reference_id || rec.status.toUpperCase() === st
                        }
                        onClick={() => handleStatusUpdate(rec.reference_id, st)}
                        className={`rounded-lg px-3 py-1.5 text-xs font-bold transition disabled:opacity-40 ${
                          rec.status.toUpperCase() === st
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-secondary hover:bg-accent text-foreground'
                        }`}
                      >
                        {st}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
