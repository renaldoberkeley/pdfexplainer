"use client";

import { useMemo, useState } from "react";

import ChatMessage, { TutorMessage } from "./ChatMessage";
import PageSelector from "./PageSelector";

interface TutorPanelProps {
  pageCount: number;
  currentPage: number;
  messages: TutorMessage[];
  isExplaining: boolean;
  isGeneratingAudioForId: string | null;
  onSendQuestion: (question: string, pages: number[]) => void;
  onListen: (message: TutorMessage) => void;
}

export default function TutorPanel({
  pageCount,
  currentPage,
  messages,
  isExplaining,
  isGeneratingAudioForId,
  onSendQuestion,
  onListen,
}: TutorPanelProps) {
  const [question, setQuestion] = useState("");
  const [selectedPages, setSelectedPages] = useState<number[]>([currentPage]);

  const canSend = useMemo(
    () => question.trim().length > 0 && selectedPages.length > 0 && !isExplaining,
    [question, selectedPages, isExplaining],
  );

  return (
    <div className="flex h-full flex-col rounded-xl bg-panel p-4">
      <div className="mb-3">
        <h2 className="text-lg font-semibold text-slate-100">AI Tutor</h2>
        <p className="text-sm text-slate-400">Ask focused questions about selected pages.</p>
      </div>

      <div className="mb-3">
        <PageSelector
          currentPage={currentPage}
          pageCount={pageCount}
          onPagesChange={setSelectedPages}
        />
      </div>

      <div className="mb-3 flex-1 space-y-3 overflow-auto pr-1">
        {messages.length === 0 ? (
          <p className="rounded-lg bg-soft p-3 text-sm text-slate-400">
            Upload a PDF, select a page, and ask your first question.
          </p>
        ) : (
          messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message}
              onListen={onListen}
              isGeneratingAudio={isGeneratingAudioForId === message.id}
            />
          ))
        )}
        {isExplaining ? (
          <div className="rounded-lg bg-soft p-3 text-sm text-slate-300">Thinking...</div>
        ) : null}
      </div>

      <div className="space-y-2">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about this page..."
          rows={4}
          className="w-full resize-none rounded-lg border border-slate-600 bg-soft px-3 py-2 text-sm text-slate-100 focus:border-accent focus:outline-none"
        />
        <div className="flex items-center gap-2">
          <button
            className="rounded-md border border-slate-600 bg-soft px-3 py-2 text-sm text-slate-200"
            title="Speech input coming soon"
            type="button"
          >
            🎙️
          </button>
          <button
            className="ml-auto rounded-md bg-accent px-4 py-2 text-sm font-semibold text-slate-900 disabled:opacity-60"
            disabled={!canSend}
            onClick={() => {
              onSendQuestion(question.trim(), selectedPages);
              setQuestion("");
            }}
          >
            {isExplaining ? "Sending..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

