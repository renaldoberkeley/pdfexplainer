"use client";

import { useCallback, useState } from "react";

interface PDFUploaderProps {
  onFileSelected: (file: File) => void;
  isUploading: boolean;
}

export default function PDFUploader({ onFileSelected, isUploading }: PDFUploaderProps) {
  const [dragging, setDragging] = useState(false);

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      const file = fileList?.[0];
      if (file) {
        onFileSelected(file);
      }
    },
    [onFileSelected],
  );

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        handleFiles(event.dataTransfer.files);
      }}
      className={`flex h-56 w-full items-center justify-center rounded-xl border-2 border-dashed p-6 text-center transition ${
        dragging ? "border-accent bg-blue-500/10" : "border-slate-600 bg-panel"
      }`}
    >
      <div className="space-y-3">
        <p className="text-base font-medium text-slate-200">
          Drag and drop a PDF here
        </p>
        <p className="text-sm text-slate-400">or choose a file to start tutoring.</p>
        <label className="inline-flex cursor-pointer items-center rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-slate-900 hover:opacity-90">
          {isUploading ? "Uploading..." : "Choose PDF"}
          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            disabled={isUploading}
            onChange={(event) => handleFiles(event.target.files)}
          />
        </label>
      </div>
    </div>
  );
}

