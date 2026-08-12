'use client';

import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  PhoneCall,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface FarmAlert {
  id: number;
  farmer_name: string;
  sip_destination: string;
  village: string;
  crop: string;
  alert_type: string;
  alert_reason: string;
  recommended_action: string;
  verification_question: string;
  verification_answer: string;
  status: string;
  notes: string;
  created_at: string;
  updated_at: string;
  call_attempts: number;
  last_call_outcome: string;
}

export function Day6AlertDashboard() {
  const [alerts, setAlerts] = useState<FarmAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/alerts');
      if (!res.ok) throw new Error('Failed to fetch farm alerts');
      const data = await res.json();
      setAlerts(data.alerts || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error loading alerts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'confirmed':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">
            <CheckCircle2 className="size-3.5" /> Confirmed / पुष्टि हुई
          </span>
        );
      case 'needs_inspection':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">
            <AlertTriangle className="size-3.5" /> Needs Inspection / जांच आवश्यक
          </span>
        );
      case 'not_observed':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-xs font-bold text-blue-800">
            <ShieldCheck className="size-3.5" /> Not Observed / नहीं दिखा
          </span>
        );
      case 'verification_failed':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-800">
            <ShieldAlert className="size-3.5" /> Verification Failed / पहचान असफल
          </span>
        );
      case 'follow_up_required':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 px-3 py-1 text-xs font-bold text-purple-800">
            <Clock className="size-3.5" /> Follow-up Required / कॉल बाद में
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">
            <Clock className="size-3.5" /> Pending / लंबित
          </span>
        );
    }
  };

  return (
    <div className="farm-card mt-8 p-6 text-left">
      <div className="border-border flex flex-col justify-between gap-4 border-b pb-4 sm:flex-row sm:items-center">
        <div>
          <div className="text-primary flex items-center gap-2 text-sm font-bold tracking-wider uppercase">
            <PhoneCall className="size-4" /> Day 6: Outbound SIP Telephony
          </div>
          <h2 className="text-foreground mt-1 text-2xl font-bold">
            🌾 Farm Alert Telephony Dashboard
          </h2>
          <p className="text-muted-foreground mt-1 text-sm">
            Real-time status of KrishiMitra AI proactive outbound farm alert calls.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchAlerts}
          disabled={loading}
          className="rounded-xl font-bold"
        >
          <RefreshCw className={`mr-2 size-4 ${loading ? 'animate-spin' : ''}`} /> Refresh Status
        </Button>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
          ⚠️ {error}
        </div>
      )}

      {alerts.length === 0 ? (
        <div className="text-muted-foreground py-8 text-center text-sm">
          No farm alert records found in database. Run backend agent to auto-seed demo records.
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="border-border bg-card flex flex-col justify-between rounded-2xl border p-5 shadow-sm transition-all hover:shadow-md"
            >
              <div>
                <div className="border-border/50 flex items-center justify-between gap-2 border-b pb-3">
                  <div>
                    <h3 className="text-foreground text-lg font-bold">{alert.farmer_name}</h3>
                    <p className="text-muted-foreground text-xs">
                      📍 {alert.village} • 🌾 Crop:{' '}
                      <strong className="text-foreground">{alert.crop}</strong>
                    </p>
                  </div>
                  <span className="text-primary bg-primary/10 rounded-lg px-2.5 py-1 font-mono text-xs font-bold">
                    ID #{alert.id}
                  </span>
                </div>

                <div className="mt-3 space-y-2.5 text-xs">
                  <div>
                    <span className="text-muted-foreground font-semibold">Alert Type:</span>
                    <p className="font-bold text-amber-600 dark:text-amber-400">
                      {alert.alert_type}
                    </p>
                  </div>

                  <div>
                    <span className="text-muted-foreground font-semibold">
                      Verification Question:
                    </span>
                    <p className="text-foreground bg-muted/50 mt-0.5 rounded-lg p-2 italic">
                      {alert.verification_question}
                    </p>
                  </div>

                  <div>
                    <span className="text-muted-foreground font-semibold">Status / status:</span>
                    <div className="mt-1">{getStatusBadge(alert.status)}</div>
                  </div>

                  <div>
                    <span className="text-muted-foreground font-semibold">Last Call Outcome:</span>
                    <p className="text-foreground mt-0.5 font-medium">
                      {alert.last_call_outcome || 'None'}
                    </p>
                  </div>

                  {alert.notes && (
                    <div>
                      <span className="text-muted-foreground font-semibold">Notes:</span>
                      <p className="text-muted-foreground mt-0.5 text-[11px] leading-relaxed">
                        {alert.notes}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div className="border-border/50 text-muted-foreground mt-4 flex items-center justify-between border-t pt-3 text-[11px]">
                <span>Attempts: {alert.call_attempts}</span>
                <span>
                  Updated:{' '}
                  {alert.updated_at ? new Date(alert.updated_at).toLocaleTimeString() : 'N/A'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="border-primary/20 bg-primary/5 mt-6 rounded-2xl border p-4 text-xs">
        <h4 className="text-primary flex items-center gap-1.5 text-sm font-bold">
          💻 Day 6 CLI Outbound Call Commands (Linphone SIP)
        </h4>
        <p className="text-muted-foreground mt-1">
          Execute these commands in your terminal to trigger outbound calls for each demo scenario:
        </p>
        <div className="mt-3 space-y-2 font-mono text-[11px]">
          <div className="overflow-x-auto rounded-xl bg-slate-900 p-2.5 text-slate-100">
            <span className="text-emerald-400">
              # Scenario 1 — Verified + Alert Acknowledged (Ramesh / Wheat):
            </span>
            <br />
            uv run python src/telephony/outbound/dial.py --to aditiyadav12 --alert-id 1
          </div>
          <div className="overflow-x-auto rounded-xl bg-slate-900 p-2.5 text-slate-100">
            <span className="text-emerald-400">
              # Scenario 2 — Verified + Issue Not Observed (Suresh / Soybean):
            </span>
            <br />
            uv run python src/telephony/outbound/dial.py --to aditiyadav12 --alert-id 2
          </div>
          <div className="overflow-x-auto rounded-xl bg-slate-900 p-2.5 text-slate-100">
            <span className="text-emerald-400">
              # Scenario 3 — Verification Failure (Mahesh / Rice):
            </span>
            <br />
            uv run python src/telephony/outbound/dial.py --to aditiyadav12 --alert-id 3
          </div>
        </div>
      </div>
    </div>
  );
}
