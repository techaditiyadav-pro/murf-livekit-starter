'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Headset, Send, Sprout, UserRound } from 'lucide-react';
import { useAgent, useRoomContext, useSessionMessages } from '@livekit/components-react';

type LocalMessage = { id: string; text: string };

const QUICK_QUESTIONS = [
  'फसल की जानकारी',
  'सिंचाई कब करें?',
  'गेहूं की खेती कैसे करें?',
  'फसल में कीड़े लग गए हैं',
  'मौसम का खेती पर असर',
];

export function FarmChat() {
  const room = useRoomContext();
  const { state } = useAgent();
  const { messages } = useSessionMessages();
  const [input, setInput] = useState('');
  const [localMessages, setLocalMessages] = useState<LocalMessage[]>([]);
  const [waitingForReply, setWaitingForReply] = useState(false);
  const [retryMessage, setRetryMessage] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const agentMessages = messages.filter((message) => message.type === 'agentTranscript');
  const isThinking = waitingForReply || state === 'thinking';

  useEffect(() => {
    if (agentMessages.length && waitingForReply) {
      setWaitingForReply(false);
      setError(false);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    }
  }, [agentMessages.length, waitingForReply]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [agentMessages.length, localMessages.length, isThinking, error]);

  useEffect(
    () => () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    },
    []
  );

  const sendMessage = async (text: string) => {
    const message = text.trim();
    if (!message || waitingForReply) return;

    setInput('');
    setError(false);
    setRetryMessage(message);
    setLocalMessages((current) => [...current, { id: crypto.randomUUID(), text: message }]);
    setWaitingForReply(true);

    try {
      await room.localParticipant.sendText(message, { topic: 'krishimitra-chat' });
      timeoutRef.current = setTimeout(() => {
        setWaitingForReply(false);
        setError(true);
      }, 30000);
    } catch {
      setWaitingForReply(false);
      setError(true);
    }
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void sendMessage(input);
  };

  return (
    <section className="farm-card mt-6 overflow-hidden text-left" aria-label="KrishiMitra AI chat">
      <header className="border-primary/15 bg-primary/5 flex items-center justify-between gap-3 border-b px-4 py-4 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="bg-primary text-primary-foreground flex size-10 items-center justify-center rounded-xl">
            <Sprout className="size-5" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-foreground font-bold">🌾 KrishiMitra AI</h2>
            <p className="text-muted-foreground text-xs">आपका खेती-बाड़ी का AI साथी</p>
            <p className="text-primary mt-1 text-xs font-semibold">● Online • Farming Assistant</p>
          </div>
        </div>

        <Link href="/help">
          <button
            type="button"
            className="flex items-center gap-1.5 rounded-xl bg-amber-600 px-3 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-amber-700"
          >
            <Headset className="size-4" /> Human Help
          </button>
        </Link>
      </header>

      <div
        className="max-h-[26rem] min-h-72 space-y-4 overflow-y-auto px-4 py-5 sm:px-6"
        aria-live="polite"
      >
        {!localMessages.length && !agentMessages.length && (
          <div className="bg-primary/5 rounded-2xl p-4 text-sm leading-6">
            <p className="font-bold">🌾 नमस्ते! मैं KrishiMitra AI हूँ।</p>
            <p className="text-muted-foreground mt-1">
              आप खेती-बाड़ी से जुड़ा कोई भी सवाल पूछ सकते हैं।
            </p>
          </div>
        )}

        {localMessages.map((message) => (
          <div key={message.id} className="ml-auto max-w-[88%]">
            <p className="text-muted-foreground mb-1 flex items-center justify-end gap-1 text-xs font-semibold">
              आप <UserRound className="size-3" aria-hidden="true" />
            </p>
            <p className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-6 break-words">
              {message.text}
            </p>
          </div>
        ))}

        {agentMessages.map((message) => (
          <div key={message.id} className="max-w-[88%]">
            <p className="text-primary mb-1 text-xs font-semibold">🌾 KrishiMitra AI</p>
            <p className="bg-secondary rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-6 break-words">
              {message.message}
            </p>
          </div>
        ))}

        {isThinking && (
          <div className="max-w-[88%]" role="status">
            <p className="text-primary mb-1 text-xs font-semibold">🌾 KrishiMitra AI</p>
            <div className="bg-secondary rounded-2xl rounded-tl-sm px-4 py-3 text-sm">
              KrishiMitra AI जवाब तैयार कर रहा है...
              <span className="ml-2 animate-pulse tracking-[0.3em]">•••</span>
            </div>
          </div>
        )}

        {error && (
          <div
            className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950"
            role="alert"
          >
            कुछ समस्या आ गई। कृपया दोबारा कोशिश करें।
            <button
              type="button"
              className="ml-3 font-bold underline underline-offset-2"
              onClick={() => retryMessage && void sendMessage(retryMessage)}
            >
              🔄 Try Again
            </button>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-primary/15 border-t px-4 py-4 sm:px-6">
        <p className="text-muted-foreground mb-2 text-xs font-semibold">💡 पूछकर देखें:</p>
        <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
          {QUICK_QUESTIONS.map((question) => (
            <button
              key={question}
              type="button"
              onClick={() => void sendMessage(question)}
              disabled={waitingForReply}
              className="border-primary/20 text-primary hover:bg-primary/10 shrink-0 rounded-full border px-3 py-1.5 text-xs font-semibold transition disabled:opacity-50"
            >
              {question}
            </button>
          ))}
        </div>
        <form onSubmit={onSubmit} className="flex items-end gap-2">
          <label htmlFor="farming-question" className="sr-only">
            अपना खेती से जुड़ा सवाल लिखें
          </label>
          <textarea
            id="farming-question"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                void sendMessage(input);
              }
            }}
            placeholder="अपना खेती से जुड़ा सवाल लिखें..."
            rows={2}
            disabled={waitingForReply}
            className="border-input bg-background focus-visible:ring-ring min-h-12 flex-1 resize-none rounded-xl border px-3 py-2 text-sm outline-none focus-visible:ring-2 disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={!input.trim() || waitingForReply}
            className="bg-primary text-primary-foreground hover:bg-primary/90 focus-visible:ring-ring flex min-h-12 items-center gap-1 rounded-xl px-4 text-sm font-bold shadow-sm outline-none focus-visible:ring-2 disabled:opacity-50"
            aria-label="Send farming question"
          >
            <Send className="size-4" aria-hidden="true" /> भेजें
          </button>
        </form>
      </div>
    </section>
  );
}
