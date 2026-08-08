import { Sprout } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
  isConnecting?: boolean;
  error?: string | null;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  isConnecting = false,
  error,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => (
  <div ref={ref} className="w-full">
    <section className="farm-shell mx-auto w-full max-w-5xl px-4 py-8 text-center sm:px-6">
      <div className="farm-card overflow-hidden px-5 py-8 sm:px-10 sm:py-10">
        <div className="bg-primary text-primary-foreground mx-auto flex size-16 items-center justify-center rounded-3xl shadow-lg">
          <Sprout className="size-8" aria-hidden="true" />
        </div>
        <p className="text-primary mt-5 text-sm font-semibold tracking-[0.18em] uppercase">
          Farm &amp; Field
        </p>
        <h1 className="text-foreground mt-2 text-4xl font-bold tracking-tight sm:text-5xl">
          🌾 KrishiMitra AI
        </h1>
        <p className="text-primary mt-2 text-lg font-semibold">आपका खेती-बाड़ी का AI साथी</p>
        <p className="text-muted-foreground mx-auto mt-5 max-w-xl text-base leading-7">
          Talk to KrishiMitra AI for simple farming guidance, crop-related questions, and field
          assistance.
        </p>
        <div className="farm-illustration mt-7" aria-hidden="true">
          <span>☀️</span>
          <span>🌾</span>
          <span>🚜</span>
          <span>🌾</span>
        </div>

        {error ? (
          <div
            role="alert"
            className="mx-auto mt-7 max-w-xl rounded-2xl border border-amber-300 bg-amber-50 p-5 text-left text-amber-950"
          >
            <p className="font-bold">🎙️ Microphone Access Needed</p>
            <p className="mt-2 text-sm leading-6">
              KrishiMitra AI needs microphone access to hear you. Please allow microphone permission
              in your browser settings and try again.
            </p>
            <p className="mt-2 text-xs opacity-75">{error}</p>
          </div>
        ) : isConnecting ? (
          <div className="mt-8" aria-live="polite">
            <div className="farm-spinner mx-auto" />
            <p className="text-primary mt-4 text-lg font-bold">Connecting to KrishiMitra AI...</p>
            <p className="text-muted-foreground mt-1 text-sm">Please wait while we connect you.</p>
          </div>
        ) : (
          <>
            <Button
              size="lg"
              onClick={onStartCall}
              className="mt-8 min-h-14 w-full max-w-md rounded-2xl text-base font-bold shadow-lg sm:w-96"
            >
              {startButtonText}
            </Button>
            <p className="text-primary mt-4 text-sm font-semibold">● Ready to help you</p>
          </>
        )}
        {error && (
          <Button
            size="lg"
            onClick={onStartCall}
            className="mt-5 min-h-14 w-full max-w-md rounded-2xl text-base font-bold sm:w-96"
          >
            🔄 Try Again
          </Button>
        )}
      </div>
      <div className="mt-6 grid grid-cols-2 gap-3 text-left sm:grid-cols-4">
        <Feature icon="🌱" title="Crop Guidance" />
        <Feature icon="💧" title="Irrigation Support" />
        <Feature icon="🌦️" title="Weather Questions" />
        <Feature icon="🌾" title="Farming Assistance" />
      </div>
      <div className="farm-card mt-6 p-5 text-left sm:p-6">
        <p className="text-foreground font-bold">Try asking / पूछकर देखें</p>
        <ul className="text-muted-foreground mt-3 space-y-2 text-sm leading-6">
          <li>“Meri fasal ke liye kaunsi khaad achhi hai?”</li>
          <li>“Mujhe gehun ki kheti ke baare mein batao.”</li>
          <li>“Fasal mein keede lag gaye hain, kya karun?”</li>
        </ul>
      </div>
    </section>
  </div>
);

function Feature({ icon, title }: { icon: string; title: string }) {
  return (
    <div className="farm-card p-4">
      <span className="text-2xl">{icon}</span>
      <p className="text-foreground mt-2 text-sm font-bold">{title}</p>
    </div>
  );
}
