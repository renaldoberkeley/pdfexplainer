"use client";

import { useMemo } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

interface PDFViewerProps {
  file: File | null;
  pageNumber: number;
  pageCount: number;
  zoom: number;
  onPageCountChange: (count: number) => void;
  onPageChange: (page: number) => void;
  onZoomChange: (zoom: number) => void;
}

export default function PDFViewer({
  file,
  pageNumber,
  pageCount,
  zoom,
  onPageCountChange,
  onPageChange,
  onZoomChange,
}: PDFViewerProps) {
  const width = useMemo(() => Math.round(680 * zoom), [zoom]);

  return (
    <div className="flex h-full flex-col rounded-xl bg-panel p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg bg-soft p-3 text-sm">
        <button
          className="rounded bg-slate-700 px-3 py-1 disabled:opacity-40"
          onClick={() => onPageChange(pageNumber - 1)}
          disabled={pageNumber <= 1}
        >
          Prev
        </button>
        <button
          className="rounded bg-slate-700 px-3 py-1 disabled:opacity-40"
          onClick={() => onPageChange(pageNumber + 1)}
          disabled={pageCount > 0 && pageNumber >= pageCount}
        >
          Next
        </button>
        <span className="text-slate-300">
          Page {pageCount > 0 ? pageNumber : 0} / {pageCount}
        </span>
        <div className="ml-auto flex items-center gap-2">
          <button
            className="rounded bg-slate-700 px-3 py-1"
            onClick={() => onZoomChange(Math.max(0.6, Number((zoom - 0.1).toFixed(1))))}
          >
            -
          </button>
          <span className="min-w-14 text-center text-slate-300">{Math.round(zoom * 100)}%</span>
          <button
            className="rounded bg-slate-700 px-3 py-1"
            onClick={() => onZoomChange(Math.min(2.4, Number((zoom + 0.1).toFixed(1))))}
          >
            +
          </button>
        </div>
      </div>
      <div className="flex flex-1 items-start justify-center overflow-auto rounded-lg bg-[#0b1227] p-4">
        {file ? (
          <Document
            file={file}
            onLoadSuccess={({ numPages }) => {
              onPageCountChange(numPages);
              if (pageNumber > numPages) {
                onPageChange(numPages);
              }
            }}
            loading={<p className="text-slate-400">Loading PDF...</p>}
            error={<p className="text-red-300">Failed to render PDF.</p>}
          >
            <Page pageNumber={pageNumber} width={width} />
          </Document>
        ) : (
          <p className="pt-16 text-slate-500">Upload a PDF to begin.</p>
        )}
      </div>
    </div>
  );
}

