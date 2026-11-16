'use client';

import React, { useRef, useEffect, useState, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import * as THREE from 'three';
import { TerrainMesh } from './TerrainMesh';
import { ParticleFlowField } from './ParticleFlowField';
import { Fallback2DTopography } from './Fallback2DTopography';
import { TopographyCameraRig, type Vec3Tuple } from './TopographyCameraRig';
import type { ForecastSimulationPoint } from '@/lib/types';

interface TopographyCanvasProps {
  simulationPoints?: ForecastSimulationPoint[];
  creditLimit?: number;
  height?: number;
  /** World-space point to fly the camera to (e.g. the lowest cash point). Pass a new array to re-trigger. */
  flyToTarget?: Vec3Tuple | null;
}

function SceneContent({
  creditLimit,
  flyToTarget,
}: {
  creditLimit: number;
  flyToTarget?: Vec3Tuple | null;
}) {
  return (
    <>
      <color attach="background" args={['#020617']} />
      <ambientLight intensity={0.7} />
      <directionalLight position={[30, 60, 40]} intensity={1.2} />
      <pointLight position={[0, 15, 0]} intensity={1.0} color="#10b981" />

      <TerrainMesh creditLimit={creditLimit} />
      <ParticleFlowField particleCount={1000} />

      {/* Credit limit danger datum plane */}
      <mesh position={[0, -8, 0]} rotation={[-Math.PI / 2.5, 0, 0]}>
        <planeGeometry args={[90, 30]} />
        <meshBasicMaterial
          color="#ef4444"
          transparent
          opacity={0.12}
          side={THREE.DoubleSide}
        />
      </mesh>

      <TopographyCameraRig flyToTarget={flyToTarget} />
    </>
  );
}

export function TopographyCanvas({
  simulationPoints,
  creditLimit = 2500000,
  height = 360,
  flyToTarget = null,
}: TopographyCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isContextLost, setIsContextLost] = useState(false);
  const [webglEpoch, setWebglEpoch] = useState(0);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const canvas = container.querySelector('canvas');
    if (!canvas) return;

    const handleContextLost = (e: Event) => {
      e.preventDefault();
      console.warn('WebGL Context Lost. Activating Fallback2DTopography.');
      setIsContextLost(true);
    };

    const handleContextRestored = () => {
      console.info('WebGL Context Restored. Remounting R3F Canvas.');
      setWebglEpoch((prev) => prev + 1);
      setIsContextLost(false);
    };

    canvas.addEventListener('webglcontextlost', handleContextLost, false);
    canvas.addEventListener('webglcontextrestored', handleContextRestored, false);

    return () => {
      canvas.removeEventListener('webglcontextlost', handleContextLost);
      canvas.removeEventListener('webglcontextrestored', handleContextRestored);
    };
  }, [webglEpoch]);

  if (isContextLost) {
    return (
      <Fallback2DTopography
        simulationPoints={simulationPoints}
        creditLimit={creditLimit}
        height={height}
      />
    );
  }

  return (
    <div
      ref={containerRef}
      className="relative w-full overflow-hidden rounded-xl border border-slate-800 bg-slate-950 shadow-2xl"
      style={{ height: `${height}px` }}
    >
      <div className="absolute top-3 left-4 z-10 flex items-center gap-2 rounded-md bg-slate-900/80 px-2.5 py-1 backdrop-blur-md border border-slate-700/50">
        <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-xs font-semibold text-slate-200">
          3D Spatial Cashflow Topography (R3F)
        </span>
      </div>

      <div className="absolute bottom-3 right-4 z-10 text-[10px] text-slate-400 bg-slate-900/80 px-2 py-0.5 rounded border border-slate-800">
        Drag to Orbit • Scroll to Zoom
      </div>

      <Suspense fallback={<Fallback2DTopography simulationPoints={simulationPoints} height={height} />}>
        <Canvas
          key={`r3f-epoch-${webglEpoch}`}
          camera={{ position: [0, 35, 65], fov: 42, near: 0.1, far: 1000 }}
          dpr={[1, 2]}
          gl={{
            antialias: true,
            alpha: false,
            powerPreference: 'high-performance',
          }}
        >
          <SceneContent creditLimit={creditLimit} flyToTarget={flyToTarget} />
        </Canvas>
      </Suspense>
    </div>
  );
}
