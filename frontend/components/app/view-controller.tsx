'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { FarmSessionView } from '@/components/app/farm-session-view';
import { WelcomeView } from '@/components/app/welcome-view';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(FarmSessionView);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.5,
    ease: 'linear',
  },
};

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, connectionState, start } = useSessionContext();
  const [hasEnded, setHasEnded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isConnecting = connectionState === 'connecting';

  const startCall = async () => {
    setHasEnded(false);
    setError(null);
    try {
      await start({ tracks: { microphone: { enabled: true } } });
    } catch (caughtError) {
      const message =
        caughtError instanceof Error ? caughtError.message : 'We could not access your microphone.';
      setError(message);
    }
  };

  const startChat = async () => {
    setHasEnded(false);
    setError(null);
    try {
      await start({ tracks: { microphone: { enabled: false } } });
    } catch (caughtError) {
      const message =
        caughtError instanceof Error
          ? caughtError.message
          : 'We could not connect to KrishiMitra AI.';
      setError(message);
    }
  };

  return (
    <AnimatePresence mode="wait">
      {/* Welcome view */}
      {!isConnected && !hasEnded && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          startButtonText={appConfig.startButtonText}
          onStartCall={startCall}
          onStartChat={startChat}
          isConnecting={isConnecting}
          error={error}
        />
      )}
      {!isConnected && hasEnded && (
        <motion.section
          key="ended"
          {...VIEW_MOTION_PROPS}
          className="farm-shell flex min-h-svh items-center justify-center px-4 text-center"
        >
          <div className="farm-card w-full max-w-lg p-8">
            <p className="text-5xl">🌾</p>
            <h1 className="mt-5 text-3xl font-bold">Call ended / बातचीत समाप्त</h1>
            <p className="text-muted-foreground mt-3">Thank you for talking with KrishiMitra AI.</p>
            <button
              type="button"
              onClick={startCall}
              className="bg-primary text-primary-foreground mt-7 min-h-14 w-full rounded-2xl px-6 text-base font-bold shadow-lg"
            >
              🔄 Start Again / फिर से शुरू करें
            </button>
          </div>
        </motion.section>
      )}
      {/* Session view */}
      {isConnected && (
        <MotionSessionView
          key="session-view"
          {...VIEW_MOTION_PROPS}
          onEnd={() => setHasEnded(true)}
        />
      )}
    </AnimatePresence>
  );
}
