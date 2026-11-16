'use client';

import React from 'react';
import { formatINR } from '@/lib/types';
import type { ForecastSimulationPoint } from '@/lib/types';

interface Fallback2DTopographyProps {
  simulationPoints?: ForecastSimulationPoint[];
  creditLimit?: number;
  height?: number;
}

export function Fallback2DTopography({
  simulationPoints = [],
  creditLimit = 2500000,
  height = 320,
}: Fallback2DTopographyProps) {
  // Generate mock simulation points if not provided
  const points = simulationPoints.length > 0
    ? simulationPoints
    : Array.from({ length: 30 }, (_, i) => {
        const day = i * 3;
        const p50 = 1239000 + Math.sin(i / 3) * 500000 - (i === 1 ? 465000 : 0);
        return {
          dayIndex: day,
          date: `2026-10-${String((day % 30) + 1).padStart(2, '0')}`,
          p10WorstCase: p50 - 400000,
          p50Median: p50,
          p90Optimistic: p50 + 600000,
          ccFacilityLimit: creditLimit,
        };
      });

  const maxVal = 2500000;
  const minVal = -creditLimit;
  const range = maxVal - minVal;

  const width = 800;
  const svgHeight = height;
  const padding = { top: 20, right: 30, bottom: 40, left: 70 };

  const scaleX = (index: number) =>
    padding.left + (index / (points.length - 1)) * (width - padding.left - padding.right);

  const scaleY = (val: number) =>
    padding.top + (1 - (val - minVal) / range) * (svgHeight - padding.top - padding.bottom);

  // SVG Area paths
  const p90Area = `M ${scaleX(0)} ${scaleY(points[0].p90Optimistic)} ` +
    points.map((p, i) => `L ${scaleX(i)} ${scaleY(p.p90Optimistic)}`).join(' ') +
    ` L ${scaleX(points.length - 1)} ${scaleY(points[points.length - 1].p10WorstCase)} ` +
    [...points].reverse().map((p, i) => `L ${scaleX(points.length - 1 - i)} ${scaleY(p.p10WorstCase)}`).join(' ') +
    ' Z';

  const p50Line = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(i)} ${scaleY(p.p50Median)}`)
    .join(' ');

  const zeroLineY = scaleY(0);
  const ccLineY = scaleY(-creditLimit);

  return (
    <div className="relative w-full overflow-hidden rounded-xl bg-slate-950 p-4 text-white shadow-xl">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <h4 className="text-sm font-semibold text-slate-200">2D Cartographic Cash Elevation Fallback</h4>
        </div>
        <span className="text-xs text-slate-400">P10 - P90 Probability Bands</span>
      </div>

      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${svgHeight}`}
          className="w-full h-auto min-w-[600px]"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="p90Gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.05" />
            </linearGradient>
            <linearGradient id="flowPulse" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0" />
              <stop offset="50%" stopColor="#38bdf8" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line
            x1={padding.left}
            y1={zeroLineY}
            x2={width - padding.right}
            y2={zeroLineY}
            stroke="#475569"
            strokeDasharray="4 4"
            strokeWidth="1"
          />
          <text x={padding.left - 8} y={zeroLineY + 4} textAnchor="end" className="fill-slate-400 text-[10px]">
            ₹0
          </text>

          {/* CC Danger Limit Line */}
          <line
            x1={padding.left}
            y1={ccLineY}
            x2={width - padding.right}
            y2={ccLineY}
            stroke="#ef4444"
            strokeWidth="1.5"
            strokeDasharray="6 3"
          />
          <text x={padding.left - 8} y={ccLineY + 4} textAnchor="end" className="fill-red-400 font-mono text-[10px]">
            -₹25L (CC Limit)
          </text>

          {/* P10 - P90 Area */}
          <path d={p90Area} fill="url(#p90Gradient)" />

          {/* P50 Median Line */}
          <path d={p50Line} fill="none" stroke="#10b981" strokeWidth="2.5" />

          {/* 48 CSS-animated flow stream strokes */}
          {Array.from({ length: 8 }, (_, idx) => {
            const step = Math.floor((points.length / 8) * idx);
            const x = scaleX(step);
            const y = scaleY(points[step]?.p50Median || 0);
            return (
              <circle
                key={`flow-${idx}`}
                cx={x}
                cy={y}
                r="4"
                fill="#38bdf8"
                className="animate-ping"
                style={{ animationDuration: `${2 + (idx % 3)}s` }}
              />
            );
          })}

          {/* Landmark Milestone Pin */}
          <g transform={`translate(${scaleX(1)}, ${scaleY(points[1]?.p10WorstCase || 0)})`}>
            <circle cx="0" cy="0" r="4" fill="#f59e0b" />
            <line x1="0" y1="0" x2="0" y2="-20" stroke="#f59e0b" strokeWidth="1.5" />
            <rect x="-45" y="-36" width="90" height="16" rx="3" fill="#1e293b" stroke="#f59e0b" strokeWidth="1" />
            <text x="0" y="-25" textAnchor="middle" className="fill-amber-300 text-[9px] font-medium">
              1 Oct: Salaries
            </text>
          </g>
        </svg>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
        <span>T0: Today (30 Sep)</span>
        <span className="text-emerald-400 font-mono">P50 Peak: {formatINR(points[0]?.p50Median || 1239000, { compact: true })}</span>
        <span>T+90: Horizon (31 Dec)</span>
      </div>
    </div>
  );
}
