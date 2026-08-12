import Link from 'next/link';
import { Headset, Mic, ShieldAlert, Sprout } from 'lucide-react';
import { Button } from '@/components/ui/button';

const cards = [
  ['🌱', 'Crop Guidance', 'फसल की सलाह'],
  ['💧', 'Irrigation Support', 'सिंचाई सहायता'],
  ['🌦️', 'Weather Questions', 'मौसम की जानकारी'],
  ['🌾', 'Farming Assistance', 'खेती में मदद'],
];
export function WelcomeView({
  startButtonText,
  onStartCall,
  isConnecting = false,
  error,
  ref,
}: React.ComponentProps<'div'> & {
  startButtonText: string;
  onStartCall: () => void;
  isConnecting?: boolean;
  error?: string | null;
}) {
  return (
    <div ref={ref} className="krishi-page">
      <section className="krishi-welcome-card relative">
        <div className="mb-2 flex items-center justify-between border-b border-[#d5e5c5] pb-3">
          <div className="krishi-brand text-lg sm:text-xl">
            <Sprout /> KrishiMitra AI
          </div>
          <div className="flex items-center gap-2">
            <Link href="/help">
              <Button
                size="sm"
                variant="outline"
                className="h-9 rounded-lg border-[#287a3d] text-xs font-bold text-[#1f6a36] hover:bg-[#edf6df]"
              >
                <Headset className="mr-1 size-3.5" /> Human Help
              </Button>
            </Link>
            <Link href="/escalations">
              <Button
                size="sm"
                variant="ghost"
                className="h-9 rounded-lg text-xs text-stone-600 hover:text-stone-900"
              >
                <ShieldAlert className="mr-1 size-3.5" /> Dashboard
              </Button>
            </Link>
          </div>
        </div>

        <p className="krishi-subtitle">आपका खेती-बाड़ी का AI साथी</p>
        <div className="krishi-field-art" aria-hidden="true">
          🌾 <span>🌱</span> ☀️
        </div>
        <h1>Your Voice Assistant for Smarter Farming</h1>
        <p className="krishi-description">
          Talk to KrishiMitra AI for simple farming guidance, crop-related questions, and field
          assistance.
        </p>
        {error ? (
          <div className="krishi-error" role="alert">
            <strong>🎙️ Microphone Access Needed</strong>
            <p>{error}</p>
          </div>
        ) : isConnecting ? (
          <div className="krishi-connecting" role="status">
            <span className="krishi-spinner" />
            <div>
              <strong>Connecting to KrishiMitra AI...</strong>
              <br />
              Please wait while we connect you.
            </div>
          </div>
        ) : (
          <p className="krishi-ready">● Ready to help you</p>
        )}

        <div className="mx-auto mt-5 flex w-full max-w-md flex-col items-center justify-center gap-3 sm:flex-row">
          <Button
            size="lg"
            onClick={onStartCall}
            disabled={isConnecting}
            className="krishi-start-button mt-0 w-full flex-1"
          >
            <Mic />{' '}
            {isConnecting ? 'Connecting...' : error ? '🔄 Try Again' : `🎙️ ${startButtonText}`}
          </Button>
          <Link href="/help" className="w-full sm:w-auto">
            <Button
              size="lg"
              variant="outline"
              className="mt-0 h-14 w-full rounded-xl border-[#287a3d] bg-white px-5 font-bold text-[#1f6a36] shadow-md hover:bg-[#edf6df]"
            >
              <Headset className="mr-1.5 size-5" /> Human Help
            </Button>
          </Link>
        </div>
        <div className="krishi-support-grid">
          {cards.map(([icon, title, hindi]) => (
            <div className="krishi-support-card" key={title}>
              <span>{icon}</span>
              <strong>{title}</strong>
              <small>{hindi}</small>
            </div>
          ))}
        </div>
        <div className="krishi-questions">
          <strong>Try asking / पूछकर देखें:</strong>
          <span>“मेरी फसल के लिए कौनसी खाद अच्छी है?”</span>
          <span>“फसल में कीड़े लग गए हैं, क्या करूँ?”</span>
        </div>
      </section>
    </div>
  );
}
