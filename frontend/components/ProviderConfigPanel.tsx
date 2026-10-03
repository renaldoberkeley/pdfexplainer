"use client";

import { ProviderConfig } from "@/lib/api";

interface ProviderConfigPanelProps {
  config: ProviderConfig | null;
  loading: boolean;
  error: string | null;
}

export default function ProviderConfigPanel({ config, loading, error }: ProviderConfigPanelProps) {
  return (
    <div className="rounded-xl border border-slate-700 bg-panel p-4">
      <h2 className="text-lg font-semibold text-slate-100">Provider Configuration</h2>
      <p className="mt-1 text-sm text-slate-400">
        Active providers are controlled by backend environment variables.
      </p>

      {loading ? <p className="mt-3 text-sm text-slate-300">Loading provider status...</p> : null}
      {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}

      {config ? (
        <div className="mt-3 space-y-2 text-sm">
          <div className="rounded-md bg-soft p-2">
            <span className="text-slate-400">LLM:</span>{" "}
            <span className="font-medium text-slate-100">{config.llm_provider}</span>
            <span className="ml-2 text-slate-500">
              (available: {config.available_llm_providers.join(", ")})
            </span>
          </div>
          <div className="rounded-md bg-soft p-2">
            <span className="text-slate-400">Gemma model:</span>{" "}
            <span className="font-medium text-slate-100">
              {config.gemma_model_id || "not configured"}
            </span>
            <span className="ml-2 text-slate-500">
              (max tokens: {config.gemma_max_new_tokens})
            </span>
          </div>
          <div className="rounded-md bg-soft p-2">
            <span className="text-slate-400">TTS:</span>{" "}
            <span className="font-medium text-slate-100">{config.tts_provider}</span>
            <span className="ml-2 text-slate-500">
              (available: {config.available_tts_providers.join(", ")})
            </span>
          </div>
          <div className="rounded-md bg-soft p-2">
            <span className="text-slate-400">STT:</span>{" "}
            <span className="font-medium text-slate-100">{config.stt_provider}</span>
            <span className="ml-2 text-slate-500">
              (available: {config.available_stt_providers.join(", ")})
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
