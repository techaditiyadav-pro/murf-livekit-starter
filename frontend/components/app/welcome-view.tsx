import { Mic, Sprout } from 'lucide-react';
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
      <section className="krishi-welcome-card">
        <div className="krishi-brand">
          <Sprout /> KrishiMitra AI
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
        <Button
          size="lg"
          onClick={onStartCall}
          disabled={isConnecting}
          className="krishi-start-button"
        >
          <Mic />{' '}
          {isConnecting ? 'Connecting...' : error ? '🔄 Try Again' : `🎙️ ${startButtonText}`}
        </Button>
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
