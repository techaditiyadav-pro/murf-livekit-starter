'use client';

import Link from 'next/link';
import { Headset, Mic, PhoneOff, Volume2 } from 'lucide-react';
import { useAgent, useSessionContext } from '@livekit/components-react';
import { AudioVisualizer } from '@/components/agents-ui/blocks/agent-session-view-01/components/audio-visualizer';
import { FarmChat } from '@/components/app/farm-chat';
import { NavHeader } from '@/components/app/nav-header';
import { Button } from '@/components/ui/button';

interface FarmSessionViewProps {
  onEnd: () => void;
}

export function FarmSessionView({ onEnd }: FarmSessionViewProps) {
  const { state } = useAgent();
  const { end } = useSessionContext();
  const isSpeaking = state === 'speaking';
  const isThinking = state === 'thinking';
  const title = isSpeaking
    ? '🔊 KrishiMitra AI is speaking...'
    : isThinking
      ? '🌾 KrishiMitra AI is preparing an answer...'
      : '🎙️ Listening to you...';
  const hindi = isSpeaking
    ? 'KrishiMitra AI जवाब दे रहा है'
    : isThinking
      ? 'आपके सवाल पर सोच रहा हूँ'
      : 'आपकी बात सुन रहा हूँ';

  const leave = async () => {
    onEnd();
    await end();
  };

  return (
    <>
      <NavHeader />
      <section className="farm-shell min-h-svh px-4 py-8 text-center">
        <div className="mx-auto w-full max-w-2xl">
          <div className="farm-card px-5 py-9 sm:px-10">
            <p className="text-primary text-sm font-semibold tracking-[0.18em] uppercase">
              🌾 KrishiMitra AI
            </p>
            <div
              className={`farm-state-icon mx-auto mt-8 ${isSpeaking ? 'farm-speaking' : 'farm-listening'}`}
            >
              {isSpeaking ? <Volume2 className="size-10" /> : <Mic className="size-10" />}
            </div>
            <h1 className="text-foreground mt-6 text-2xl font-bold sm:text-3xl" aria-live="polite">
              {title}
            </h1>
            <p className="text-primary mt-2 text-base font-medium">{hindi}</p>
            <div className="bg-primary/5 relative mx-auto mt-5 flex h-32 max-w-md items-center justify-center overflow-hidden rounded-2xl">
              <AudioVisualizer
                audioVisualizerType="wave"
                audioVisualizerColor={isSpeaking ? '#c97819' : '#287a3e'}
                audioVisualizerWaveLineWidth={4}
                isChatOpen={false}
                className="scale-[0.28] sm:scale-[0.34]"
              />
            </div>
            <p className="text-muted-foreground mx-auto mt-5 max-w-md text-sm leading-6">
              {isSpeaking
                ? 'Please listen while your farming assistant responds.'
                : 'आप अपनी खेती से जुड़ा सवाल पूछ सकते हैं।'}
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Button
                variant="outline"
                size="lg"
                onClick={leave}
                className="min-h-12 rounded-xl border-red-200 px-6 font-bold text-red-700 hover:bg-red-50 hover:text-red-800"
              >
                <PhoneOff /> End Call / कॉल समाप्त करें
              </Button>
              <Link href="/help">
                <Button
                  variant="secondary"
                  size="lg"
                  className="flex min-h-12 items-center gap-2 rounded-xl border border-amber-300 bg-amber-100 px-6 font-bold text-amber-900 hover:bg-amber-200"
                >
                  <Headset className="size-5 text-amber-700" /> Human Help
                </Button>
              </Link>
            </div>
          </div>
          <FarmChat />
        </div>
      </section>
    </>
  );
}
