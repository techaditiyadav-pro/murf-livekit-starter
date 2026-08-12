'use client';

import { useCallback, useEffect, useState } from 'react';

type Escalation = {
  reference_id: string;
  farmer_name: string | null;
  reason: string;
  problem_summary: string;
  what_agent_checked: string;
  urgency: string;
  language: string;
  preferred_follow_up_method: string;
  status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED';
  created_at: string;
};

export function EscalationDashboard() {
  const [requests, setRequests] = useState<Escalation[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const response = await fetch('/api/escalations', { cache: 'no-store' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      setRequests(data.escalations);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load requests.');
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const changeStatus = async (referenceId: string, status: Escalation['status']) => {
    const response = await fetch(`/api/escalations/${referenceId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (response.ok) void load();
    else setError('Could not update request status.');
  };

  return (
    <main className="min-h-svh bg-stone-50 p-6 text-stone-900">
      <div className="mx-auto max-w-7xl">
        <h1 className="text-3xl font-semibold text-green-800">KrishiMitra Human Support</h1>
        <p className="mt-2 text-stone-600">
          Open and recent farmer escalation requests. No conversation transcripts are shown.
        </p>
        {error && <p className="mt-4 rounded bg-red-50 p-3 text-red-800">{error}</p>}
        <div className="mt-6 overflow-x-auto rounded-lg border bg-white">
          <table className="w-full min-w-[1100px] text-left text-sm">
            <thead className="bg-green-50 text-green-900">
              <tr>
                {[
                  'Reference',
                  'Farmer',
                  'Reason',
                  'Summary',
                  'Checked',
                  'Urgency',
                  'Language',
                  'Follow-up',
                  'Status',
                  'Created',
                ].map((label) => (
                  <th className="p-3" key={label}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {requests.map((item) => (
                <tr className="border-t align-top" key={item.reference_id}>
                  <td className="p-3 font-medium">{item.reference_id}</td>
                  <td className="p-3">{item.farmer_name ?? 'Not provided'}</td>
                  <td className="p-3">{item.reason}</td>
                  <td className="p-3">{item.problem_summary}</td>
                  <td className="p-3">{item.what_agent_checked}</td>
                  <td className="p-3 uppercase">{item.urgency}</td>
                  <td className="p-3">{item.language}</td>
                  <td className="p-3">{item.preferred_follow_up_method}</td>
                  <td className="p-3">
                    <select
                      aria-label={`Status for ${item.reference_id}`}
                      className="rounded border p-1"
                      value={item.status}
                      onChange={(event) =>
                        void changeStatus(
                          item.reference_id,
                          event.target.value as Escalation['status']
                        )
                      }
                    >
                      {['OPEN', 'IN_PROGRESS', 'RESOLVED'].map((status) => (
                        <option key={status}>{status}</option>
                      ))}
                    </select>
                  </td>
                  <td className="p-3">{new Date(item.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!error && requests.length === 0 && (
            <p className="p-6 text-stone-600">No escalation requests yet.</p>
          )}
        </div>
      </div>
    </main>
  );
}
