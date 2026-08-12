'use client';

import Link from 'next/link';
import { Headset, Mic, PhoneOff, Sprout, Volume2 } from 'lucide-react';
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
        <div className="mb-2 flex items-center justify-between border-b border-[#d5e5c5] pb-3">
          <div className="krishi-brand text-lg sm:text-xl">
            <Sprout /> KrishiMitra AI
          </div>
          <Link href="/help" onClick={() => end()}>
            <Button
              size="sm"
              variant="outline"
              className="h-9 rounded-lg border-[#287a3d] text-xs font-bold text-[#1f6a36] hover:bg-[#edf6df]"
            >
              <Headset className="mr-1 size-3.5" /> Human Help
            </Button>
          </Link>
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

        <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button
            size="lg"
            variant="outline"
            onClick={() => {
              end();
              onEnd();
            }}
            className="krishi-end-button mt-0 w-full sm:w-auto"
          >
            <PhoneOff /> End call / बातचीत समाप्त करें
          </Button>
          <Link href="/help" onClick={() => end()} className="w-full sm:w-auto">
            <Button
              size="lg"
              variant="outline"
              className="mt-0 h-12 w-full rounded-xl border-[#287a3d] bg-white px-5 font-bold text-[#1f6a36] hover:bg-[#edf6df]"
            >
              <Headset className="mr-1.5 size-5" /> Human Help
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
}
