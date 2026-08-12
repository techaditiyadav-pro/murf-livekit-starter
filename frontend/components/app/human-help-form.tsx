'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Headset,
  Lock,
  Send,
  ShieldAlert,
  Sprout,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

type EscalationResponse = {
  reference_id: string;
  farmer_name: string | null;
  reason: string;
  problem_summary: string;
  urgency: string;
  language: string;
  preferred_follow_up_method: string;
  status: string;
  created_at: string;
  duplicate?: boolean;
};

export function HumanHelpForm() {
  const [farmerName, setFarmerName] = useState('');
  const [reason, setReason] = useState('SERIOUS_CROP_PROBLEM');
  const [problemSummary, setProblemSummary] = useState('');
  const [urgency, setUrgency] = useState('medium');
  const [language, setLanguage] = useState('Hindi');
  const [followUpMethod, setFollowUpMethod] = useState('Phone Call');
  const [permissionGranted, setPermissionGranted] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sensitiveWarning, setSensitiveWarning] = useState<string | null>(null);
  const [createdRequest, setCreatedRequest] = useState<EscalationResponse | null>(null);

  // Client-side privacy filter to detect OTP, PIN, Passwords, Bank/Card numbers
  const checkSensitiveData = (text: str): boolean => {
    const patterns = [
      /\b(?:otp|pin|password|passcode)\b/i,
      /\b(?:account|bank|card)\s*(?:number|no\.?|details?)?\b/i,
      /\b(?:\d[ -]?){12,19}\b/,
    ];
    return patterns.some((pattern) => pattern.test(text));
  };

  const handleSummaryChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setProblemSummary(val);
    if (checkSensitiveData(val)) {
      setSensitiveWarning(
        'Please remove sensitive information such as OTPs, PINs, passwords, or bank details before submitting.'
      );
    } else {
      setSensitiveWarning(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!permissionGranted) {
      setError('Your request was not submitted because permission is required.');
      return;
    }

    if (checkSensitiveData(problemSummary)) {
      setSensitiveWarning(
        'Please remove sensitive information such as OTPs, PINs, passwords, or bank details before submitting.'
      );
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch('/api/escalations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farmer_name: farmerName.trim() || null,
          reason,
          problem_summary: problemSummary.trim(),
          what_agent_checked: 'User requested human support directly.',
          urgency,
          language,
          preferred_follow_up_method: followUpMethod,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Unable to create your request right now. Please try again.');
      }

      setCreatedRequest(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to create your request right now. Please try again.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  // SUCCESS SCREEN
  if (createdRequest) {
    return (
      <div className="krishi-page min-h-svh py-10">
        <section className="krishi-welcome-card max-w-2xl py-10">
          <div className="mx-auto flex size-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
            <CheckCircle2 className="size-10" />
          </div>
          <h1 className="mt-4 text-2xl font-extrabold text-[#183d24] sm:text-3xl">
            Human Help Request Created
          </h1>
          <p className="mt-2 text-sm text-[#527059] sm:text-base">
            Your request has been successfully submitted to the human support team.
          </p>

          <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-5 text-left">
            <div className="flex items-center justify-between border-b border-emerald-200 pb-3">
              <span className="text-xs font-semibold tracking-wider text-emerald-800 uppercase">
                Reference ID / रेफरेंस आईडी
              </span>
              <span className="rounded-md border border-emerald-300 bg-white px-3 py-1 font-mono text-base font-bold text-emerald-900 shadow-xs">
                {createdRequest.reference_id}
              </span>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-stone-700 sm:text-sm">
              <div>
                <span className="font-semibold text-stone-500">Farmer:</span>{' '}
                {createdRequest.farmer_name || 'Not specified'}
              </div>
              <div>
                <span className="font-semibold text-stone-500">Urgency:</span>{' '}
                <span className="font-semibold text-emerald-800 uppercase">
                  {createdRequest.urgency}
                </span>
              </div>
              <div>
                <span className="font-semibold text-stone-500">Language:</span>{' '}
                {createdRequest.language}
              </div>
              <div>
                <span className="font-semibold text-stone-500">Follow-up:</span>{' '}
                {createdRequest.preferred_follow_up_method}
              </div>
            </div>

            {createdRequest.duplicate && (
              <p className="mt-3 rounded-lg bg-amber-100 p-2 text-xs font-medium text-amber-900">
                ℹ️ An open request with identical details already exists under this reference ID.
              </p>
            )}
          </div>

          <div className="mt-6 rounded-xl border border-[#d7e9c7] bg-[#f8fbed] p-4 text-left">
            <h3 className="text-sm font-bold text-[#183d24]">
              What happens next? / आगे क्या होगा?
            </h3>
            <p className="mt-1 text-xs text-[#42634a] sm:text-sm">
              Your request is now open and can be reviewed by the human support team. The team will
              follow up using your selected method when available.
            </p>
          </div>

          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="/" className="w-full sm:w-auto">
              <Button size="lg" className="krishi-start-button mt-0 w-full sm:w-auto">
                <ArrowLeft className="mr-1 size-5" /> Back to KrishiMitra
              </Button>
            </Link>
            <Link href="/escalations" className="w-full sm:w-auto">
              <Button
                size="lg"
                variant="outline"
                className="h-14 w-full rounded-xl border-[#287a3d] px-5 font-bold text-[#1f6a36] hover:bg-[#edf6df]"
              >
                <ShieldAlert className="mr-1 size-5" /> Support Dashboard
              </Button>
            </Link>
          </div>
        </section>
      </div>
    );
  }

  const isFormInvalid =
    !farmerName.trim() ||
    !problemSummary.trim() ||
    !permissionGranted ||
    !!sensitiveWarning ||
    isSubmitting;

  return (
    <div className="krishi-page min-h-svh">
      <div className="mx-auto max-w-2xl">
        <div className="mb-4 flex items-center justify-between">
          <Link
            href="/"
            className="inline-flex items-center text-sm font-semibold text-[#1f6a36] hover:underline"
          >
            <ArrowLeft className="mr-1 size-4" /> Back to KrishiMitra
          </Link>
          <div className="krishi-brand text-base">
            <Sprout /> KrishiMitra AI
          </div>
        </div>

        <section className="krishi-welcome-card p-6 text-left sm:p-8">
          <div className="flex items-center gap-3">
            <div className="flex size-12 items-center justify-center rounded-2xl bg-[#edf6df] text-[#287a3d]">
              <Headset className="size-6" />
            </div>
            <div>
              <h1 className="mt-0 text-left text-2xl font-extrabold text-[#183d24] sm:text-3xl">
                Human Help
              </h1>
              <p className="mt-0.5 text-xs text-[#55724c] sm:text-sm">
                Need help from a human? Tell us briefly what happened and our support team can
                review your request.
              </p>
            </div>
          </div>

          {error && (
            <div
              className="mt-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800 sm:text-sm"
              role="alert"
            >
              <AlertTriangle className="mt-0.5 size-5 shrink-0 text-red-600" />
              <span>{error}</span>
            </div>
          )}

          {sensitiveWarning && (
            <div
              className="mt-4 flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 sm:text-sm"
              role="alert"
            >
              <AlertTriangle className="mt-0.5 size-5 shrink-0 text-amber-600" />
              <span>{sensitiveWarning}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
            {/* FIELD 1: FARMER NAME */}
            <div>
              <label
                htmlFor="farmerName"
                className="block text-xs font-bold tracking-wide text-[#183d24] uppercase"
              >
                Your Name <span className="text-red-600">*</span>
              </label>
              <input
                id="farmerName"
                type="text"
                required
                value={farmerName}
                onChange={(e) => setFarmerName(e.target.value)}
                placeholder="Enter your name"
                className="mt-1.5 w-full rounded-xl border border-[#d5e5c5] bg-white px-4 py-2.5 text-sm text-stone-900 transition outline-none focus:border-[#287a3d] focus:ring-2 focus:ring-[#287a3d]/20"
              />
            </div>

            {/* FIELD 2: REASON */}
            <div>
              <label
                htmlFor="reason"
                className="block text-xs font-bold tracking-wide text-[#183d24] uppercase"
              >
                Reason for Human Help
              </label>
              <select
                id="reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-[#d5e5c5] bg-white px-4 py-2.5 text-sm text-stone-900 transition outline-none focus:border-[#287a3d] focus:ring-2 focus:ring-[#287a3d]/20"
              >
                <option value="SERIOUS_CROP_PROBLEM">Serious Crop Problem</option>
                <option value="MARKET_DATA_UNAVAILABLE_OR_STALE">
                  Market Data Missing or Outdated
                </option>
                <option value="OTHER">Other Farm & Field Issue</option>
              </select>
            </div>

            {/* FIELD 3: PROBLEM DESCRIPTION */}
            <div>
              <div className="flex items-center justify-between">
                <label
                  htmlFor="problemSummary"
                  className="block text-xs font-bold tracking-wide text-[#183d24] uppercase"
                >
                  What happened? <span className="text-red-600">*</span>
                </label>
                <span className="text-[11px] text-stone-500">{problemSummary.length}/500</span>
              </div>
              <textarea
                id="problemSummary"
                required
                maxLength={500}
                rows={3}
                value={problemSummary}
                onChange={handleSummaryChange}
                placeholder="Briefly describe your problem..."
                className="mt-1.5 w-full rounded-xl border border-[#d5e5c5] bg-white p-3 text-sm text-stone-900 transition outline-none focus:border-[#287a3d] focus:ring-2 focus:ring-[#287a3d]/20"
              />
            </div>

            {/* GRID FOR URGENCY, LANGUAGE, FOLLOW-UP */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {/* FIELD 4: URGENCY */}
              <div>
                <label
                  htmlFor="urgency"
                  className="block text-xs font-bold tracking-wide text-[#183d24] uppercase"
                >
                  How urgent is this?
                </label>
                <select
                  id="urgency"
                  value={urgency}
                  onChange={(e) => setUrgency(e.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-[#d5e5c5] bg-white px-3 py-2 text-xs text-stone-900 transition outline-none focus:border-[#287a3d] sm:text-sm"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="emergency">Emergency</option>
                </select>
              </div>

              {/* FIELD 5: LANGUAGE */}
              <div>
                <label
                  htmlFor="language"
                  className="block text-xs font-bold tracking-wide text-[#183d24] uppercase"
                >
                  Preferred Language
                </label>
                <select
                  id="language"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-[#d5e5c5] bg-white px-3 py-2 text-xs text-stone-900 transition outline-none focus:border-[#287a3d] sm:text-sm"
                >
                  <option value="Hindi">Hindi</option>
                  <option value="English">English</option>
                  <option value="Hinglish">Hinglish</option>
                </select>
              </div>

              {/* FIELD 6: FOLLOW-UP METHOD */}
              <div>
                <label
                  htmlFor="followUpMethod"
                  className="block text-xs font-bold tracking-wide text-[#183d24] uppercase"
                >
                  Follow-up Method
                </label>
                <select
                  id="followUpMethod"
                  value={followUpMethod}
                  onChange={(e) => setFollowUpMethod(e.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-[#d5e5c5] bg-white px-3 py-2 text-xs text-stone-900 transition outline-none focus:border-[#287a3d] sm:text-sm"
                >
                  <option value="Phone Call">Phone Call</option>
                  <option value="Voice Call">Voice Call</option>
                  <option value="Chat">Chat</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>

            {/* PRIVACY NOTICE */}
            <div className="mt-2 flex items-start gap-2.5 rounded-xl border border-[#d7e9c7] bg-[#f8fbed] p-3 text-xs text-[#3d5e45]">
              <Lock className="mt-0.5 size-4 shrink-0 text-[#287a3d]" />
              <div>
                <p className="font-semibold text-[#183d24]">Privacy Notice</p>
                <p className="mt-0.5">
                  Please do not enter passwords, OTPs, PINs, bank details, account numbers, or other
                  sensitive information. We will share only the information needed to handle your
                  request.
                </p>
              </div>
            </div>

            {/* PERMISSION CHECKBOX */}
            <div className="mt-1 flex items-start gap-2.5">
              <input
                id="permissionCheckbox"
                type="checkbox"
                required
                checked={permissionGranted}
                onChange={(e) => setPermissionGranted(e.target.checked)}
                className="mt-1 size-4 rounded border-[#287a3d] text-[#287a3d] focus:ring-[#287a3d]"
              />
              <label
                htmlFor="permissionCheckbox"
                className="cursor-pointer text-xs font-medium text-stone-800"
              >
                I agree to share this information with the human support team for help with my
                request. <span className="text-red-600">*</span>
              </label>
            </div>

            {/* SUBMIT BUTTON */}
            <Button
              type="submit"
              size="lg"
              disabled={isFormInvalid}
              className="krishi-start-button mt-4 h-14 w-full"
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <span className="krishi-spinner size-5 border-white border-t-transparent" />
                  Creating Request...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Send className="size-5" /> Request Human Help
                </span>
              )}
            </Button>
          </form>
        </section>
      </div>
    </div>
  );
}
