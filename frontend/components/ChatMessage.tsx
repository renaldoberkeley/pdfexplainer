"use client";

import ReactMarkdown from "react-markdown";

import AudioPlayer from "./AudioPlayer";

export interface TutorMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  pages?: number[];
  audioDataUrl?: string | null;
}

interface ChatMessageProps {
  message: TutorMessage;
  isGeneratingAudio: boolean;
  onListen: (message: TutorMessage) => void;
}

export default function ChatMessage({ message, isGeneratingAudio, onListen }: ChatMessageProps) {
  const isAssistant = message.role === "assistant";
  return (
    <div className={`rounded-lg p-3 ${isAssistant ? "bg-soft" : "bg-slate-700/60"}`}>
      <p className="mb-1 text-xs uppercase tracking-wide text-slate-400">
        {isAssistant ? "AI Tutor" : "You"}
      </p>
      <div className="prose prose-invert max-w-none prose-p:my-2 prose-headings:my-2 prose-ul:my-2">
        <ReactMarkdown>{message.content}</ReactMarkdown>
      </div>
      {isAssistant ? (
        <div className="mt-2 space-y-2">
          <button
            className="rounded-md bg-accent px-3 py-1 text-sm font-medium text-slate-900 disabled:opacity-60"
            onClick={() => onListen(message)}
            disabled={isGeneratingAudio}
          >
            {isGeneratingAudio ? "Generating audio..." : "Listen"}
          </button>
          <AudioPlayer audioDataUrl={message.audioDataUrl ?? null} />
        </div>
      ) : null}
    </div>
  );
}

