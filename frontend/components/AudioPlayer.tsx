"use client";

interface AudioPlayerProps {
  audioDataUrl: string | null;
}

export default function AudioPlayer({ audioDataUrl }: AudioPlayerProps) {
  if (!audioDataUrl) return null;
  return (
    <audio
      controls
      className="mt-2 w-full"
      src={audioDataUrl}
      preload="none"
    >
      Your browser does not support audio playback.
    </audio>
  );
}

