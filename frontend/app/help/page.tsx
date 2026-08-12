'use client';

import { FormEvent, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, CheckCircle2, Headset, ShieldAlert, Sparkles } from 'lucide-react';
import { NavHeader } from '@/components/app/nav-header';
import { Button } from '@/components/ui/button';

export default function HumanHelpPage() {
  const [farmerName, setFarmerName] = useState('');
  const [reason, setReason] = useState('SERIOUS_CROP_PROBLEM');
  const [problemSummary, setProblemSummary] = useState('');
  const [urgency, setUrgency] = useState('medium');
  const [language, setLanguage] = useState('Hindi');
  const [followUpMethod, setFollowUpMethod] = useState('Phone Call');
  const [permission, setPermission] = useState(false);

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [sensitiveWarning, setSensitiveWarning] = useState<string | null>(null);
  const [successData, setSuccessData] = useState<{
    reference_id: string;
    farmer_name: string;
    reason: string;
  } | null>(null);

  const checkSensitiveData = (text: string): boolean => {
    const sensitivePatterns = [
      /\b(otp|pin|password|passwd|cvv|bank account|account number|credit card|debit card)\b/i,
      /\b\d{4,8}\b/,
      /\b\d{13,19}\b/,
    ];
    return sensitivePatterns.some((pattern) => pattern.test(text));
  };

  const handleDescriptionChange = (text: string) => {
    setProblemSummary(text);
    if (checkSensitiveData(text)) {
      setSensitiveWarning(
        'Please remove sensitive information such as OTPs, PINs, passwords, or bank details before submitting.'
      );
    } else {
      setSensitiveWarning(null);
    }
  };

  const isFormValid =
    farmerName.trim().length > 0 &&
    problemSummary.trim().length > 0 &&
    permission &&
    !sensitiveWarning;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);

    if (!permission) {
      setErrorMessage('Your request was not submitted because permission is required.');
      return;
    }

    if (checkSensitiveData(problemSummary)) {
      setSensitiveWarning(
        'Please remove sensitive information such as OTPs, PINs, passwords, or bank details before submitting.'
      );
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('/api/escalations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farmer_name: farmerName,
          reason,
          problem_summary: problemSummary,
          what_agent_checked: 'User requested human support directly via /help form.',
          urgency,
          language,
          preferred_follow_up_method: followUpMethod,
          permission_granted: permission,
        }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Unable to create your request right now. Please try again.');
      }

      setSuccessData({
        reference_id: data.reference_id,
        farmer_name: farmerName,
        reason,
      });
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : 'Unable to create your request right now. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-background text-foreground flex min-h-svh flex-col">
      <NavHeader />

      <main className="farm-shell flex-1 px-4 py-8 sm:px-6">
        <div className="mx-auto max-w-2xl">
          <Link
            href="/"
            className="text-primary mb-6 inline-flex items-center gap-1.5 text-sm font-semibold hover:underline"
          >
            <ArrowLeft className="size-4" /> Back to KrishiMitra
          </Link>

          {successData ? (
            <div className="farm-card animate-in fade-in zoom-in p-6 text-center duration-300 sm:p-10">
              <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                <CheckCircle2 className="size-10" />
              </div>
              <h1 className="text-foreground text-2xl font-bold sm:text-3xl">
                Human Help Request Created
              </h1>
              <p className="text-muted-foreground mt-2 text-base">
                Your request has been successfully submitted to the human support team.
              </p>

              <div className="mx-auto my-6 max-w-md rounded-2xl border border-amber-200 bg-amber-50 p-5 text-left">
                <p className="text-xs font-bold tracking-wider text-amber-800 uppercase">
                  Reference ID
                </p>
                <p className="mt-1 font-mono text-2xl font-extrabold tracking-tight text-amber-950">
                  {successData.reference_id}
                </p>
                <div className="mt-3 space-y-1 border-t border-amber-200/60 pt-3 text-xs text-amber-900">
                  <p>
                    <span className="font-semibold">Farmer:</span> {successData.farmer_name}
                  </p>
                  <p>
                    <span className="font-semibold">Status:</span> OPEN
                  </p>
                </div>
              </div>

              <div className="bg-secondary/50 mb-8 rounded-2xl p-5 text-left text-sm leading-6">
                <p className="text-foreground font-bold">What happens next?</p>
                <p className="text-muted-foreground mt-1">
                  Your request is now open and can be reviewed by the human support team. The team
                  will follow up using your selected method when available.
                </p>
              </div>

              <Link href="/">
                <Button
                  size="lg"
                  className="min-h-12 w-full rounded-2xl text-base font-bold shadow-md"
                >
                  🌾 Back to KrishiMitra
                </Button>
              </Link>
            </div>
          ) : (
            <div className="farm-card p-6 sm:p-10">
              <div className="border-border mb-6 flex items-center gap-3 border-b pb-5">
                <div className="flex size-12 items-center justify-center rounded-2xl bg-amber-100 font-bold text-amber-800 shadow-sm">
                  <Headset className="size-6" />
                </div>
                <div>
                  <h1 className="text-foreground text-2xl font-bold sm:text-3xl">Human Help</h1>
                  <p className="text-muted-foreground mt-0.5 text-sm">
                    Need help from a human? Tell us briefly what happened and our support team can
                    review your request.
                  </p>
                </div>
              </div>

              {errorMessage && (
                <div className="mb-6 flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-900">
                  <ShieldAlert className="mt-0.5 size-5 shrink-0 text-red-600" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {sensitiveWarning && (
                <div className="mb-6 flex items-start gap-2.5 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm font-medium text-amber-950">
                  <ShieldAlert className="mt-0.5 size-5 shrink-0 text-amber-700" />
                  <span>{sensitiveWarning}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Field 1: Farmer Name */}
                <div>
                  <label
                    htmlFor="farmer-name"
                    className="text-foreground mb-1.5 block text-sm font-bold"
                  >
                    Your Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="farmer-name"
                    type="text"
                    required
                    value={farmerName}
                    onChange={(e) => setFarmerName(e.target.value)}
                    placeholder="Enter your name"
                    className="border-input bg-background focus:ring-ring w-full rounded-xl border px-4 py-3 text-sm focus:ring-2 focus:outline-none"
                  />
                </div>

                {/* Field 2: Reason */}
                <div>
                  <label
                    htmlFor="reason"
                    className="text-foreground mb-1.5 block text-sm font-bold"
                  >
                    Reason for Human Help <span className="text-red-500">*</span>
                  </label>
                  <select
                    id="reason"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    className="border-input bg-background focus:ring-ring w-full rounded-xl border px-4 py-3 text-sm focus:ring-2 focus:outline-none"
                  >
                    <option value="SERIOUS_CROP_PROBLEM">Serious Crop Problem</option>
                    <option value="MARKET_DATA_UNAVAILABLE_OR_STALE">
                      Market Data Missing or Outdated
                    </option>
                    <option value="OTHER">Other Farm &amp; Field Issue</option>
                  </select>
                </div>

                {/* Field 3: Problem Description */}
                <div>
                  <div className="mb-1.5 flex items-center justify-between">
                    <label
                      htmlFor="problem-summary"
                      className="text-foreground block text-sm font-bold"
                    >
                      What happened? <span className="text-red-500">*</span>
                    </label>
                    <span className="text-muted-foreground text-xs">
                      {problemSummary.length}/500 chars
                    </span>
                  </div>
                  <textarea
                    id="problem-summary"
                    required
                    maxLength={500}
                    rows={4}
                    value={problemSummary}
                    onChange={(e) => handleDescriptionChange(e.target.value)}
                    placeholder="Briefly describe your problem..."
                    className="border-input bg-background focus:ring-ring w-full resize-y rounded-xl border px-4 py-3 text-sm focus:ring-2 focus:outline-none"
                  />
                </div>

                {/* Field 4: Urgency */}
                <div>
                  <label className="text-foreground mb-1.5 block text-sm font-bold">
                    How urgent is this?
                  </label>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {[
                      { val: 'low', label: 'Low' },
                      { val: 'medium', label: 'Medium' },
                      { val: 'high', label: 'High' },
                      { val: 'emergency', label: 'Emergency' },
                    ].map((opt) => (
                      <button
                        key={opt.val}
                        type="button"
                        onClick={() => setUrgency(opt.val)}
                        className={`rounded-xl border px-3 py-2.5 text-xs font-bold transition ${
                          urgency === opt.val
                            ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                            : 'border-input bg-background hover:bg-accent text-foreground'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Field 5 & 6: Language & Follow-up */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label
                      htmlFor="language"
                      className="text-foreground mb-1.5 block text-sm font-bold"
                    >
                      Preferred Language
                    </label>
                    <select
                      id="language"
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="border-input bg-background focus:ring-ring w-full rounded-xl border px-4 py-3 text-sm focus:ring-2 focus:outline-none"
                    >
                      <option value="Hindi">Hindi</option>
                      <option value="English">English</option>
                      <option value="Hinglish">Hinglish</option>
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="followup-method"
                      className="text-foreground mb-1.5 block text-sm font-bold"
                    >
                      Preferred Follow-up Method
                    </label>
                    <select
                      id="followup-method"
                      value={followUpMethod}
                      onChange={(e) => setFollowUpMethod(e.target.value)}
                      className="border-input bg-background focus:ring-ring w-full rounded-xl border px-4 py-3 text-sm focus:ring-2 focus:outline-none"
                    >
                      <option value="Phone Call">Phone Call</option>
                      <option value="Voice Call">Voice Call</option>
                      <option value="Chat">Chat</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                </div>

                {/* Privacy Notice */}
                <div className="border-border bg-secondary/30 text-muted-foreground space-y-1 rounded-xl border p-4 text-xs leading-5">
                  <p className="text-foreground font-semibold">🔒 Privacy Notice</p>
                  <p>
                    Please do not enter passwords, OTPs, PINs, bank details, account numbers, or
                    other sensitive information.
                  </p>
                  <p>We will share only the information needed to handle your request.</p>
                </div>

                {/* Permission Checkbox */}
                <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4">
                  <label className="flex cursor-pointer items-start gap-3">
                    <input
                      type="checkbox"
                      required
                      checked={permission}
                      onChange={(e) => setPermission(e.target.checked)}
                      className="mt-1 size-4 rounded border-amber-400 text-amber-600 focus:ring-amber-500"
                    />
                    <span className="text-xs leading-5 font-medium text-amber-950 sm:text-sm">
                      I agree to share this information with the human support team for help with my
                      request. <span className="font-bold text-red-600">*</span>
                    </span>
                  </label>
                </div>

                {/* Submit Button */}
                <Button
                  type="submit"
                  size="lg"
                  disabled={!isFormValid || loading}
                  className="min-h-14 w-full rounded-2xl bg-amber-600 text-base font-bold text-white shadow-md hover:bg-amber-700 disabled:opacity-50"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <Sparkles className="size-5 animate-spin" /> Creating Request...
                    </span>
                  ) : (
                    'Request Human Help'
                  )}
                </Button>
              </form>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
