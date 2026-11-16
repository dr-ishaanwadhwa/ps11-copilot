'use client';

import React, { useEffect, useRef } from 'react';

export interface WaveformCanvasProps {
  /** Analyser fed by the playing audio. Null means Web Audio is unavailable: a static bar is drawn. */
  analyser: AnalyserNode | null;
  /** The draw loop only runs while this is true (and the tab is visible). */
  playing: boolean;
  /** Playback progress 0..1, used for the static fallback bar. */
  progress?: number;
  height?: number;
  className?: string;
}

const BAR_COUNT = 48;

export function WaveformCanvas({
  analyser,
  playing,
  progress = 0,
  height = 56,
  className,
}: WaveformCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const progressRef = useRef(progress);
  progressRef.current = progress;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let cssW = 0;
    let cssH = 0;
    const resize = () => {
      cssW = canvas.clientWidth;
      cssH = canvas.clientHeight;
      canvas.width = Math.max(1, Math.floor(cssW * dpr));
      canvas.height = Math.max(1, Math.floor(cssH * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => { resize(); drawOnce(); }) : null;
    ro?.observe(canvas);

    const data = analyser ? new Uint8Array(analyser.frequencyBinCount) : null;
    let raf = 0;

    const drawStatic = () => {
      ctx.clearRect(0, 0, cssW, cssH);
      const barH = Math.min(6, cssH);
      const y = (cssH - barH) / 2;
      ctx.fillStyle = 'rgba(148, 163, 184, 0.25)';
      ctx.fillRect(0, y, cssW, barH);
      ctx.fillStyle = '#34d399';
      ctx.fillRect(0, y, cssW * Math.min(1, Math.max(0, progressRef.current)), barH);
    };

    const drawBars = () => {
      if (!analyser || !data) return;
      analyser.getByteFrequencyData(data);
      ctx.clearRect(0, 0, cssW, cssH);
      const step = Math.max(1, Math.floor(data.length / BAR_COUNT));
      const slot = cssW / BAR_COUNT;
      const barW = Math.max(1, slot * 0.6);
      ctx.fillStyle = '#34d399';
      for (let i = 0; i < BAR_COUNT; i++) {
        const v = data[i * step] / 255;
        const h = Math.max(2, v * cssH);
        ctx.fillRect(i * slot + (slot - barW) / 2, (cssH - h) / 2, barW, h);
      }
    };

    function drawOnce() {
      if (analyser && data) drawBars();
      else drawStatic();
    }

    const loop = () => {
      drawOnce();
      raf = requestAnimationFrame(loop);
    };

    const stop = () => {
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
    };
    const start = () => {
      if (!raf && analyser && playing && !document.hidden) raf = requestAnimationFrame(loop);
    };

    const onVisibility = () => {
      if (document.hidden) stop();
      else {
        start();
        drawOnce();
      }
    };

    drawOnce();
    start();
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      stop();
      ro?.disconnect();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [analyser, playing]);

  // Keep the static bar current while no loop is running.
  useEffect(() => {
    if (analyser) return;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    const barH = Math.min(6, h);
    const y = (h - barH) / 2;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = 'rgba(148, 163, 184, 0.25)';
    ctx.fillRect(0, y, w, barH);
    ctx.fillStyle = '#34d399';
    ctx.fillRect(0, y, w * Math.min(1, Math.max(0, progress)), barH);
  }, [analyser, progress]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={className}
      style={{ width: '100%', height: `${height}px`, display: 'block' }}
    />
  );
}
