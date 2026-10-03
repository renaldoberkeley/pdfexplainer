"use client";

import { useCallback, useEffect, useState } from "react";

import PDFUploader from "@/components/PDFUploader";
import PDFViewer from "@/components/PDFViewer";
import ProviderConfigPanel from "@/components/ProviderConfigPanel";
import TutorPanel from "@/components/TutorPanel";
import { TutorMessage } from "@/components/ChatMessage";
import { getProviderConfig, ProviderConfig, requestExplanation, requestSpeech, uploadDocument } from "@/lib/api";

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pageCount, setPageCount] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [isUploading, setIsUploading] = useState(false);
  const [isExplaining, setIsExplaining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<TutorMessage[]>([]);
  const [isGeneratingAudioForId, setIsGeneratingAudioForId] = useState<string | null>(null);
  const [providerConfig, setProviderConfig] = useState<ProviderConfig | null>(null);
  const [isProviderConfigLoading, setIsProviderConfigLoading] = useState(true);
  const [providerConfigError, setProviderConfigError] = useState<string | null>(null);

  useEffect(() => {
    const loadConfig = async () => {
      setIsProviderConfigLoading(true);
      setProviderConfigError(null);
      try {
        const config = await getProviderConfig();
        setProviderConfig(config);
      } catch (configError) {
        setProviderConfigError(
          configError instanceof Error ? configError.message : "Failed to load provider config",
        );
      } finally {
        setIsProviderConfigLoading(false);
      }
    };
    void loadConfig();
  }, []);

  const handleFileSelected = useCallback(async (nextFile: File) => {
    setError(null);
    setIsUploading(true);
    try {
      const uploaded = await uploadDocument(nextFile);
      setFile(nextFile);
      setDocumentId(uploaded.document_id);
      setPageCount(uploaded.page_count);
      setPageNumber(1);
      setMessages([]);
      setZoom(1);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Failed to upload PDF");
    } finally {
      setIsUploading(false);
    }
  }, []);

  const handleSendQuestion = useCallback(
    async (question: string, pages: number[]) => {
      if (!documentId) {
        setError("Upload a document first.");
        return;
      }
      setError(null);
      setIsExplaining(true);
      const userMessage: TutorMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: question,
        pages,
      };
      setMessages((current) => [...current, userMessage]);
      try {
        const explanation = await requestExplanation({ document_id: documentId, pages, question });
        const assistantMessage: TutorMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: explanation.answer,
          pages: explanation.pages_used,
          audioDataUrl: null,
        };
        setMessages((current) => [...current, assistantMessage]);
      } catch (explainError) {
        setError(explainError instanceof Error ? explainError.message : "Failed to generate explanation");
      } finally {
        setIsExplaining(false);
      }
    },
    [documentId],
  );

  const handleListen = useCallback(async (message: TutorMessage) => {
    if (message.role !== "assistant") return;
    setError(null);
    setIsGeneratingAudioForId(message.id);
    try {
      const response = await requestSpeech(message.content);
      const audioDataUrl = `data:${response.mime_type};base64,${response.audio_base64}`;
      setMessages((current) =>
        current.map((entry) =>
          entry.id === message.id
            ? {
                ...entry,
                audioDataUrl,
              }
            : entry,
        ),
      );
    } catch (audioError) {
      setError(audioError instanceof Error ? audioError.message : "Failed to generate speech");
    } finally {
      setIsGeneratingAudioForId(null);
    }
  }, []);

  return (
    <main className="min-h-screen bg-bg p-4 text-slate-100 md:p-6">
      <div className="mx-auto mb-4 max-w-7xl">
        <h1 className="text-2xl font-bold md:text-3xl">Open-Source AI PDF Tutor</h1>
        <p className="mt-1 text-sm text-slate-400">
          Upload a PDF, navigate pages, ask questions, and listen to explanations.
        </p>
        {error ? (
          <div className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </div>
        ) : null}
      </div>

      <div className="mx-auto grid max-w-7xl gap-4 lg:grid-cols-5">
        <section className="lg:col-span-3">
          {!file ? (
            <PDFUploader onFileSelected={handleFileSelected} isUploading={isUploading} />
          ) : (
            <PDFViewer
              file={file}
              pageNumber={pageNumber}
              pageCount={pageCount}
              zoom={zoom}
              onPageCountChange={setPageCount}
              onPageChange={(page) =>
                setPageNumber(Math.max(1, Math.min(pageCount > 0 ? pageCount : page, page)))
              }
              onZoomChange={setZoom}
            />
          )}
        </section>
        <section className="lg:col-span-2">
          <div className="flex h-full flex-col gap-4">
            <ProviderConfigPanel
              config={providerConfig}
              loading={isProviderConfigLoading}
              error={providerConfigError}
            />
            <div className="flex-1">
              <TutorPanel
                pageCount={pageCount}
                currentPage={pageNumber}
                messages={messages}
                isExplaining={isExplaining}
                isGeneratingAudioForId={isGeneratingAudioForId}
                onSendQuestion={handleSendQuestion}
                onListen={handleListen}
              />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
