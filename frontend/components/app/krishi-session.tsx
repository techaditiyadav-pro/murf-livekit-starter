'use client';

import { Mic, PhoneOff, Sprout, Volume2 } from 'lucide-react';
import { useAgent, useSessionContext } from '@livekit/components-react';
import { AudioVisualizer } from '@/components/agents-ui/blocks/agent-session-view-01/components/audio-visualizer';
import { Button } from '@/components/ui/button';

export function KrishiSession({ onEnd }: { onEnd: () => void }) {
  const { state } = useAgent();
  const { end } = useSessionContext();
  const speaking = state === 'speaking';
  const thinking = state === 'thinking';
  const title = speaking
    ? 'KrishiMitra AI is speaking...'
    : thinking
      ? 'KrishiMitra AI is preparing an answer...'
      : 'Listening to you...';
  const hindi = speaking
    ? 'KrishiMitra AI जवाब दे रहा है'
    : thinking
      ? 'आपके सवाल पर विचार कर रहा हूँ'
      : 'आपकी बात सुन रहा हूँ';
  return (
    <section className="krishi-page krishi-call-page">
      <div className="krishi-call-card">
        <div className="krishi-brand">
          <Sprout /> KrishiMitra AI
        </div>
        <p className="krishi-subtitle">Your farming companion / आपका खेती-बाड़ी का AI साथी</p>
        <div className={`krishi-orb ${speaking ? 'is-speaking' : ''}`}>
          {speaking ? <Volume2 /> : <Mic />}
        </div>
        <div className="krishi-wave">
          <AudioVisualizer
            audioVisualizerType="wave"
            audioVisualizerColor="#287a3d"
            audioVisualizerWaveLineWidth={4}
            isChatOpen={false}
          />
        </div>
        <p className="krishi-live-label">
          {speaking ? '🔊 Agent speaking' : '🎙️ Your turn to speak'}
        </p>
        <h1>{title}</h1>
        <p className="krishi-subtitle">{hindi}</p>
        <p className="krishi-tip">Ask about crops, irrigation, weather, or pests.</p>
        <Button
          size="lg"
          variant="outline"
          onClick={() => {
            end();
            onEnd();
          }}
          className="krishi-end-button"
        >
          <PhoneOff /> End call / बातचीत समाप्त करें
        </Button>
      </div>
    </section>
  );
}
