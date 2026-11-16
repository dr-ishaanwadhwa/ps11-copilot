'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { WaveformCanvas } from './WaveformCanvas';

export interface VernacularAudioPlayerProps {
  /** Audio URL. When missing or failing to load, an empty state is shown. */
  src?: string;
  title: string;
  /** Language label, e.g. "Hindi". */
  language: string;
  transcript?: string;
}

const SPEEDS = [1, 1.25, 1.5] as const;
const SEEK_STEP = 5;

function fmt(t: number): string {
  if (!Number.isFinite(t) || t < 0) return '0:00';
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// createMediaElementSource silences cross-origin media without CORS headers, so only
// route same-origin or blob/data URLs through the analyser.
function canAnalyse(src: string): boolean {
  try {
    const u = new URL(src, window.location.href);
    return u.origin === window.location.origin || u.protocol === 'blob:' || u.protocol === 'data:';
  } catch {
    return false;
  }
}

export function VernacularAudioPlayer({ src, title, language, transcript }: VernacularAudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);

  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);
  const [playing, setPlaying] = useState(false);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
    setPlaying(false);
    setCurrent(0);
    setDuration(0);
  }, [src]);

  // Close the AudioContext on unmount.
  useEffect(() => {
    return () => {
      try {
        sourceRef.current?.disconnect();
      } catch {
        /* already disconnected */
      }
      sourceRef.current = null;
      const ctx = ctxRef.current;
      ctxRef.current = null;
      if (ctx && ctx.state !== 'closed') void ctx.close().catch(() => undefined);
    };
  }, []);

  const ensureAnalyser = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || !src || sourceRef.current || !canAnalyse(src)) return;
    const Ctor: typeof AudioContext | undefined =
      typeof window !== 'undefined'
        ? window.AudioContext ??
          (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
        : undefined;
    if (!Ctor) return;
    try {
      const ctx = new Ctor();
      const node = ctx.createAnalyser();
      node.fftSize = 256;
      node.smoothingTimeConstant = 0.8;
      const source = ctx.createMediaElementSource(audio);
      source.connect(node);
      node.connect(ctx.destination);
      ctxRef.current = ctx;
      sourceRef.current = source;
      setAnalyser(node);
    } catch {
      // Web Audio unavailable: keep plain element playback and the static bar.
    }
  }, [src]);

  const toggle = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio || !src || failed) return;
    if (audio.paused) {
      ensureAnalyser();
      try {
        if (ctxRef.current?.state === 'suspended') await ctxRef.current.resume();
        await audio.play();
      } catch {
        setPlaying(false);
      }
    } else {
      audio.pause();
    }
  }, [src, failed, ensureAnalyser]);

  const seekBy = useCallback((delta: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    const max = Number.isFinite(audio.duration) ? audio.duration : Infinity;
    audio.currentTime = Math.min(max, Math.max(0, audio.currentTime + delta));
    setCurrent(audio.currentTime);
  }, []);

  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    // Let native controls (buttons, range, select) handle their own keys.
    if (e.target !== e.currentTarget) return;
    if (e.key === ' ') {
      e.preventDefault();
      void toggle();
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      seekBy(SEEK_STEP);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      seekBy(-SEEK_STEP);
    }
  };

  const changeSpeed = (s: (typeof SPEEDS)[number]) => {
    setSpeed(s);
    if (audioRef.current) audioRef.current.playbackRate = s;
  };

  if (!src || failed) {
    return (
      <div
        role="status"
        className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-400"
      >
        <p className="font-semibold text-slate-200">{title}</p>
        <p className="mt-1">No briefing audio available yet</p>
      </div>
    );
  }

  const progress = duration > 0 ? current / duration : 0;

  return (
    <div
      role="group"
      aria-label={`${title} audio briefing, ${language}`}
      tabIndex={0}
      onKeyDown={onKeyDown}
      className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-slate-200 outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
    >
      <audio
        ref={audioRef}
        src={src}
        preload="metadata"
        onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
        onDurationChange={(e) => setDuration(e.currentTarget.duration)}
        onTimeUpdate={(e) => setCurrent(e.currentTarget.currentTime)}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onError={() => setFailed(true)}
      />

      <div className="flex items-baseline justify-between gap-3">
        <p className="text-sm font-semibold">{title}</p>
        <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-300">{language}</span>
      </div>

      <div className="mt-3">
        <WaveformCanvas analyser={analyser} playing={playing} progress={progress} />
      </div>

      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          onClick={() => void toggle()}
          aria-label={playing ? `Pause ${title}` : `Play ${title}`}
          aria-pressed={playing}
          className="h-10 min-w-16 rounded-lg bg-emerald-500 px-4 text-sm font-semibold text-slate-950 hover:bg-emerald-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-300"
        >
          {playing ? 'Pause' : 'Play'}
        </button>

        <span className="w-10 text-right text-xs tabular-nums text-slate-400" aria-hidden="true">
          {fmt(current)}
        </span>
        <input
          type="range"
          min={0}
          max={duration > 0 ? duration : 0}
          step={0.1}
          value={Math.min(current, duration || 0)}
          disabled={!(duration > 0)}
          onChange={(e) => {
            const t = Number(e.target.value);
            if (audioRef.current) audioRef.current.currentTime = t;
            setCurrent(t);
          }}
          aria-label="Seek"
          aria-valuetext={`${fmt(current)} of ${fmt(duration)}`}
          className="min-w-0 flex-1 accent-emerald-400"
        />
        <span className="w-10 text-xs tabular-nums text-slate-400" aria-hidden="true">
          {fmt(duration)}
        </span>

        <label className="sr-only" htmlFor={`speed-${title}`}>
          Playback speed
        </label>
        <select
          id={`speed-${title}`}
          value={speed}
          onChange={(e) => changeSpeed(Number(e.target.value) as (typeof SPEEDS)[number])}
          className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-200"
        >
          {SPEEDS.map((s) => (
            <option key={s} value={s}>
              {s}x
            </option>
          ))}
        </select>
      </div>

      {transcript ? (
        <details className="mt-3 text-sm text-slate-300">
          <summary className="cursor-pointer text-xs text-slate-400">Transcript</summary>
          <p className="mt-2 whitespace-pre-wrap leading-relaxed">{transcript}</p>
        </details>
      ) : null}
    </div>
  );
}
