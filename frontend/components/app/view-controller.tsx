'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { KrishiSession } from '@/components/app/krishi-session';
import { WelcomeView } from '@/components/app/welcome-view';

type ViewState = 'ready' | 'connecting' | 'ended' | 'error';

export function ViewController({ appConfig }: { appConfig: AppConfig }) {
  const { isConnected, start } = useSessionContext();
  const [viewState, setViewState] = useState<ViewState>('ready');
  const connectedOnce = useRef(false);
  useEffect(() => {
    if (isConnected) {
      connectedOnce.current = true;
      setViewState('ready');
    } else if (connectedOnce.current && viewState === 'ready') setViewState('ended');
  }, [isConnected, viewState]);
  const startCall = async () => {
    setViewState('connecting');
    try {
      await start();
    } catch (error) {
      console.error('Unable to start KrishiMitra AI session:', error);
      setViewState('error');
    }
  };
  const errorText =
    'KrishiMitra AI needs microphone access to hear you. Please allow microphone permission in your browser settings and try again.';
  return (
    <AnimatePresence mode="wait">
      {isConnected ? (
        <motion.div
          key="call"
          className="fixed inset-0"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <KrishiSession onEnd={() => setViewState('ended')} />
        </motion.div>
      ) : (
        <motion.div
          key="welcome"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {viewState === 'ended' ? (
            <div className="krishi-page">
              <section className="krishi-ended-card">
                <span>🌾</span>
                <h1>Call ended / बातचीत समाप्त</h1>
                <p>Thank you for talking with KrishiMitra AI.</p>
                <p>फिर मिलेंगे — आपकी खेती के लिए हमेशा तैयार।</p>
                <button type="button" className="krishi-restart" onClick={startCall}>
                  🔄 Start Again / फिर से शुरू करें
                </button>
              </section>
            </div>
          ) : (
            <WelcomeView
              startButtonText={appConfig.startButtonText}
              onStartCall={startCall}
              isConnecting={viewState === 'connecting'}
              error={viewState === 'error' ? errorText : null}
            />
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
