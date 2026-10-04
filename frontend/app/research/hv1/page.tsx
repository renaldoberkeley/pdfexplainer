"use client";

import Image from "next/image";
import { useMemo, useState } from "react";

import {
  Hv1RatingSubmitRequest,
  Hv1SessionStartResponse,
  Hv1TaskPayload,
  startHv1Session,
  submitHv1Rating,
} from "@/lib/api";

type ScoreKey =
  | "factual_correctness"
  | "document_grounding"
  | "completeness"
  | "teaching_clarity"
  | "visual_grounding"
  | "visual_detail_accuracy";

const CORE_DIMENSIONS: Array<{ key: ScoreKey; label: string }> = [
  { key: "factual_correctness", label: "Factual correctness" },
  { key: "document_grounding", label: "Document grounding" },
  { key: "completeness", label: "Completeness" },
  { key: "teaching_clarity", label: "Teaching clarity" },
];

const VISUAL_DIMENSIONS: Array<{ key: ScoreKey; label: string }> = [
  { key: "visual_grounding", label: "Visual grounding" },
  { key: "visual_detail_accuracy", label: "Visual-detail accuracy" },
];

export default function Hv1ResearchPage() {
  const [session, setSession] = useState<Hv1SessionStartResponse | null>(null);
  const [task, setTask] = useState<Hv1TaskPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scoreState, setScoreState] = useState<Record<ScoreKey, number | null>>({
    factual_correctness: null,
    document_grounding: null,
    completeness: null,
    teaching_clarity: null,
    visual_grounding: null,
    visual_detail_accuracy: null,
  });
  const [comment, setComment] = useState("");

  const completed = session?.progress.completed ?? 0;
  const total = session?.progress.total ?? 0;
  const remaining = session?.progress.remaining ?? 0;

  const canSubmit = useMemo(() => {
    if (!task) return false;
    const coreReady = CORE_DIMENSIONS.every((dimension) => scoreState[dimension.key] !== null);
    if (!coreReady) return false;
    if (!task.is_visual_case) return true;
    return VISUAL_DIMENSIONS.every((dimension) => scoreState[dimension.key] !== null);
  }, [scoreState, task]);

  const beginSession = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams(window.location.search);
      const payload = {
        prolific_pid: params.get("PROLIFIC_PID") || undefined,
        study_id: params.get("STUDY_ID") || undefined,
        session_id: params.get("SESSION_ID") || undefined,
      };
      const response = await startHv1Session(payload);
      setSession(response);
      setTask(response.next_task);
      resetForm();
    } catch (sessionError) {
      setError(sessionError instanceof Error ? sessionError.message : "Failed to initialize HV1 session.");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setScoreState({
      factual_correctness: null,
      document_grounding: null,
      completeness: null,
      teaching_clarity: null,
      visual_grounding: null,
      visual_detail_accuracy: null,
    });
    setComment("");
  };

  const handleSubmit = async () => {
    if (!session || !task) return;
    if (!canSubmit) {
      setError("Please rate all required dimensions before submitting.");
      return;
    }

    const payload: Hv1RatingSubmitRequest = {
      hv1_response_id: task.hv1_response_id,
      factual_correctness: scoreState.factual_correctness ?? 0,
      document_grounding: scoreState.document_grounding ?? 0,
      completeness: scoreState.completeness ?? 0,
      teaching_clarity: scoreState.teaching_clarity ?? 0,
      visual_grounding: task.is_visual_case ? scoreState.visual_grounding : null,
      visual_detail_accuracy: task.is_visual_case ? scoreState.visual_detail_accuracy : null,
      comment: comment.trim() ? comment.trim() : null,
    };

    setSubmitting(true);
    setError(null);
    try {
      const response = await submitHv1Rating(session.participant_session_id, payload);
      setSession((current) =>
        current
          ? {
              ...current,
              progress: response.progress,
            }
          : current,
      );
      setTask(response.next_task);
      resetForm();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to submit rating.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-bg p-4 text-slate-100 md:p-6">
      <div className="mx-auto max-w-6xl space-y-4">
        <header className="rounded-xl border border-slate-700 bg-panel p-4">
          <h1 className="text-2xl font-semibold">HV1 Human Evaluation (Local Research Instrument)</h1>
          <p className="mt-2 text-sm text-slate-300">
            This surface is intentionally isolated from the tutor UX. It is designed for blinded human scoring of
            frozen E2 responses.
          </p>
          <p className="mt-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
            DRAFT — REQUIRES PRE-LAUNCH ETHICS/IRB REVIEW. Recruitment and real participant data collection are not
            enabled.
          </p>
          {!session ? (
            <button
              type="button"
              className="mt-4 rounded-md bg-accent px-4 py-2 text-sm font-medium text-slate-900 hover:bg-blue-300 disabled:opacity-60"
              onClick={beginSession}
              disabled={loading}
            >
              {loading ? "Initializing..." : "Begin local HV1 session"}
            </button>
          ) : (
            <div className="mt-3 text-sm text-slate-300">
              <p>
                Participant session: <span className="font-mono text-xs">{session.participant_session_id}</span>
              </p>
              <p>
                Progress: {completed}/{total} completed ({remaining} remaining)
              </p>
            </div>
          )}
          {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}
        </header>

        {session ? (
          <section className="grid gap-4 lg:grid-cols-3">
            <div className="space-y-4 lg:col-span-2">
              <article className="rounded-xl border border-slate-700 bg-panel p-4">
                <h2 className="text-lg font-semibold">Participant introduction (draft)</h2>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-300">
                  <li>Neutral purpose statement: evaluate quality of AI explanations against source material.</li>
                  <li>Estimated task duration and workload are finalized before launch.</li>
                  <li>Participation is voluntary and participants can stop any time.</li>
                  <li>Data handling details and contact channels will be finalized after ethics review.</li>
                  <li>Consent language remains draft and must be approved before launch.</li>
                </ul>
              </article>

              <article className="rounded-xl border border-slate-700 bg-panel p-4">
                <h2 className="text-lg font-semibold">Calibration example (synthetic)</h2>
                <p className="mt-2 text-sm text-slate-300">
                  {session.calibration_example.notes}
                </p>
                <div className="mt-3 space-y-2 text-sm">
                  <p>
                    <span className="text-slate-400">Question:</span> {session.calibration_example.question}
                  </p>
                  <p>
                    <span className="text-slate-400">Answer:</span> {session.calibration_example.answer}
                  </p>
                </div>
              </article>

              {task ? (
                <article className="rounded-xl border border-slate-700 bg-panel p-4">
                  <h2 className="text-lg font-semibold">Current rating task</h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Response ID: {task.hv1_response_id} (condition-hidden)
                  </p>
                  <p className="mt-3 text-sm">
                    <span className="font-medium text-slate-300">Question:</span> {task.question}
                  </p>
                  <div className="mt-3 rounded-md bg-soft p-3 text-sm whitespace-pre-wrap">{task.answer}</div>

                  <h3 className="mt-5 text-sm font-semibold uppercase tracking-wide text-slate-300">Source material</h3>
                  <div className="mt-2 space-y-4">
                    {task.source_pages.map((page) => (
                      <div key={page.page_number} className="rounded-md border border-slate-700 bg-soft p-3">
                        <p className="text-xs text-slate-400">Page {page.page_number}</p>
                        <Image
                          className="mt-2 w-full rounded border border-slate-600"
                          src={`data:${page.image_mime_type};base64,${page.image_base64}`}
                          alt={`Source page ${page.page_number}`}
                          width={page.width}
                          height={page.height}
                          unoptimized
                        />
                        <details className="mt-2">
                          <summary className="cursor-pointer text-xs text-slate-300">Show extracted text</summary>
                          <pre className="mt-2 max-h-48 overflow-y-auto whitespace-pre-wrap text-xs text-slate-300">
                            {page.extracted_text}
                          </pre>
                        </details>
                      </div>
                    ))}
                  </div>
                </article>
              ) : (
                <article className="rounded-xl border border-emerald-600/50 bg-emerald-900/20 p-4">
                  <h2 className="text-lg font-semibold text-emerald-200">All assigned tasks completed</h2>
                  <p className="mt-2 text-sm text-emerald-100">
                    This local session has no remaining ratings. Real participant collection is still disabled.
                  </p>
                </article>
              )}
            </div>

            <aside className="space-y-4">
              <article className="rounded-xl border border-slate-700 bg-panel p-4">
                <h2 className="text-lg font-semibold">Rubric quick help</h2>
                <p className="mt-2 text-sm text-slate-300">{session.rubric.abstention_policy}</p>
                <div className="mt-3 space-y-3">
                  {session.rubric.criteria.map((criterion) => (
                    <details key={criterion.name} className="rounded-md border border-slate-600 px-2 py-1">
                      <summary className="cursor-pointer text-sm capitalize">{criterion.name.replaceAll("_", " ")}</summary>
                      <ul className="mt-2 space-y-1 text-xs text-slate-300">
                        {Object.entries(criterion.anchors).map(([score, text]) => (
                          <li key={score}>
                            <span className="font-semibold">{score}:</span> {text}
                          </li>
                        ))}
                      </ul>
                    </details>
                  ))}
                </div>
              </article>

              {task ? (
                <article className="rounded-xl border border-slate-700 bg-panel p-4">
                  <h2 className="text-lg font-semibold">Submit rating</h2>
                  <div className="mt-3 space-y-3">
                    {CORE_DIMENSIONS.map((dimension) => (
                      <ScoreRow
                        key={dimension.key}
                        label={dimension.label}
                        value={scoreState[dimension.key]}
                        onChange={(value) =>
                          setScoreState((current) => ({
                            ...current,
                            [dimension.key]: value,
                          }))
                        }
                      />
                    ))}

                    {task.is_visual_case ? (
                      <>
                        {VISUAL_DIMENSIONS.map((dimension) => (
                          <ScoreRow
                            key={dimension.key}
                            label={dimension.label}
                            value={scoreState[dimension.key]}
                            onChange={(value) =>
                              setScoreState((current) => ({
                                ...current,
                                [dimension.key]: value,
                              }))
                            }
                          />
                        ))}
                      </>
                    ) : (
                      <p className="text-xs text-slate-400">
                        Visual criteria are not required for this non-visual task.
                      </p>
                    )}

                    <label className="block text-sm">
                      <span className="text-slate-300">Optional comment</span>
                      <textarea
                        className="mt-1 h-24 w-full rounded-md border border-slate-600 bg-soft px-2 py-1 text-sm"
                        value={comment}
                        onChange={(event) => setComment(event.target.value)}
                      />
                    </label>
                  </div>
                  <button
                    type="button"
                    className="mt-4 w-full rounded-md bg-accent px-4 py-2 text-sm font-medium text-slate-900 hover:bg-blue-300 disabled:opacity-60"
                    disabled={!canSubmit || submitting}
                    onClick={handleSubmit}
                  >
                    {submitting ? "Submitting..." : "Submit & next"}
                  </button>
                </article>
              ) : null}
            </aside>
          </section>
        ) : null}
      </div>
    </main>
  );
}

interface ScoreRowProps {
  label: string;
  value: number | null;
  onChange: (value: number) => void;
}

function ScoreRow({ label, value, onChange }: ScoreRowProps) {
  return (
    <fieldset>
      <legend className="mb-1 text-sm text-slate-300">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {[0, 1, 2, 3, 4].map((score) => (
          <button
            key={score}
            type="button"
            className={`min-w-9 rounded border px-2 py-1 text-xs ${
              value === score
                ? "border-blue-300 bg-blue-200 text-slate-900"
                : "border-slate-500 bg-soft text-slate-200"
            }`}
            onClick={() => onChange(score)}
          >
            {score}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
