"use client";

import { useEffect, useState } from "react";

interface PageSelectorProps {
  currentPage: number;
  pageCount: number;
  onPagesChange: (pages: number[]) => void;
}

function parsePageSelection(input: string, pageCount: number): number[] {
  const trimmed = input.trim();
  if (!trimmed) {
    return [];
  }

  const pages = new Set<number>();
  const segments = trimmed.split(",");
  for (const segment of segments) {
    const chunk = segment.trim();
    if (!chunk) continue;
    if (chunk.includes("-")) {
      const [startRaw, endRaw] = chunk.split("-").map((part) => part.trim());
      const start = Number(startRaw);
      const end = Number(endRaw);
      if (!Number.isInteger(start) || !Number.isInteger(end) || start > end) {
        throw new Error(`Invalid range "${chunk}"`);
      }
      for (let page = start; page <= end; page += 1) {
        pages.add(page);
      }
    } else {
      const page = Number(chunk);
      if (!Number.isInteger(page)) {
        throw new Error(`Invalid page "${chunk}"`);
      }
      pages.add(page);
    }
  }

  const sorted = [...pages].sort((a, b) => a - b);
  const invalid = sorted.filter((page) => page < 1 || page > pageCount);
  if (invalid.length > 0) {
    throw new Error(`Out-of-range page(s): ${invalid.join(", ")}`);
  }
  return sorted;
}

export default function PageSelector({ currentPage, pageCount, onPagesChange }: PageSelectorProps) {
  const [value, setValue] = useState(String(currentPage));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setValue(String(currentPage));
    onPagesChange([currentPage]);
  }, [currentPage, onPagesChange]);

  return (
    <div className="space-y-1">
      <label htmlFor="pageSelector" className="text-xs text-slate-400">
        Pages (e.g. 4 or 2-4,7)
      </label>
      <input
        id="pageSelector"
        value={value}
        onChange={(event) => {
          const nextValue = event.target.value;
          setValue(nextValue);
          if (pageCount < 1) {
            onPagesChange([]);
            return;
          }
          try {
            const parsed = parsePageSelection(nextValue, pageCount);
            setError(null);
            onPagesChange(parsed);
          } catch (parseError) {
            setError(parseError instanceof Error ? parseError.message : "Invalid page selection");
            onPagesChange([]);
          }
        }}
        className="w-full rounded-md border border-slate-600 bg-soft px-3 py-2 text-sm text-slate-100"
      />
      {error ? <p className="text-xs text-red-300">{error}</p> : null}
    </div>
  );
}

