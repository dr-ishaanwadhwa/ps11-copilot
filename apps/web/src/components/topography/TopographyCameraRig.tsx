'use client';

import React, {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
} from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';

export type Vec3Tuple = [number, number, number];

export interface TopographyCameraRigHandle {
  /** Fly (or jump, under reduced motion) to look at a world-space point. */
  flyTo: (target: Vec3Tuple) => void;
  /** Cancel an in-progress fly-to, leaving the camera where it is. */
  cancel: () => void;
}

export interface TopographyCameraRigProps {
  /** When this changes to a non-null value, fly to it. Pass a new array to re-trigger. */
  flyToTarget?: Vec3Tuple | null;
  /** Offset of the camera from the target at the end of a fly-to. */
  flyOffset?: Vec3Tuple;
  /** Fly duration in seconds. */
  flyDuration?: number;
  minDistance?: number;
  maxDistance?: number;
  onFlyComplete?: () => void;
}

const DEFAULT_OFFSET: Vec3Tuple = [0, 14, 24];

const easeInOutCubic = (t: number) =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

type ControlsImpl = React.ElementRef<typeof OrbitControls>;

/**
 * Constrained, damped orbit camera with an eased, cancellable fly-to move.
 * Orbit uses drei's OrbitControls (already a dependency) rather than a hand-written
 * rig; the fly-to animation is driven from useFrame with preallocated vectors.
 */
export const TopographyCameraRig = forwardRef<TopographyCameraRigHandle, TopographyCameraRigProps>(
  function TopographyCameraRig(
    {
      flyToTarget = null,
      flyOffset = DEFAULT_OFFSET,
      flyDuration = 1.5,
      minDistance = 18,
      maxDistance = 140,
      onFlyComplete,
    },
    ref,
  ) {
    const controlsRef = useRef<ControlsImpl>(null);
    const camera = useThree((s) => s.camera);

    const scratch = useMemo(
      () => ({
        startPos: new THREE.Vector3(),
        endPos: new THREE.Vector3(),
        startTarget: new THREE.Vector3(),
        endTarget: new THREE.Vector3(),
      }),
      [],
    );
    const anim = useRef({ active: false, elapsed: 0, duration: 1.5 });
    const onCompleteRef = useRef(onFlyComplete);
    onCompleteRef.current = onFlyComplete;
    const offsetRef = useRef(flyOffset);
    offsetRef.current = flyOffset;
    const durationRef = useRef(flyDuration);
    durationRef.current = flyDuration;

    const cancel = useCallback(() => {
      anim.current.active = false;
    }, []);

    const flyTo = useCallback(
      (target: Vec3Tuple) => {
        const controls = controlsRef.current;
        if (!controls) return;
        const o = offsetRef.current;
        scratch.endTarget.set(target[0], target[1], target[2]);
        scratch.endPos.set(target[0] + o[0], target[1] + o[1], target[2] + o[2]);

        if (prefersReducedMotion()) {
          anim.current.active = false;
          camera.position.copy(scratch.endPos);
          controls.target.copy(scratch.endTarget);
          controls.update();
          onCompleteRef.current?.();
          return;
        }
        scratch.startPos.copy(camera.position);
        scratch.startTarget.copy(controls.target);
        anim.current.elapsed = 0;
        anim.current.duration = Math.max(0.01, durationRef.current);
        anim.current.active = true;
      },
      [camera, scratch],
    );

    useImperativeHandle(ref, () => ({ flyTo, cancel }), [flyTo, cancel]);

    useEffect(() => {
      if (flyToTarget) flyTo(flyToTarget);
    }, [flyToTarget, flyTo]);

    // User input cancels a cinematic move.
    useEffect(() => {
      const controls = controlsRef.current;
      if (!controls) return;
      controls.addEventListener('start', cancel);
      return () => controls.removeEventListener('start', cancel);
    }, [cancel]);

    useEffect(() => {
      const controls = controlsRef.current;
      return () => {
        anim.current.active = false;
        controls?.dispose();
      };
    }, []);

    useFrame((_, delta) => {
      const a = anim.current;
      const controls = controlsRef.current;
      if (!a.active || !controls) return;
      a.elapsed += Math.min(delta, 0.05);
      const t = Math.min(1, a.elapsed / a.duration);
      const k = easeInOutCubic(t);
      camera.position.lerpVectors(scratch.startPos, scratch.endPos, k);
      controls.target.lerpVectors(scratch.startTarget, scratch.endTarget, k);
      controls.update();
      if (t >= 1) {
        a.active = false;
        onCompleteRef.current?.();
      }
    });

    return (
      <OrbitControls
        ref={controlsRef}
        makeDefault
        enablePan
        enableZoom
        enableRotate
        enableDamping
        dampingFactor={0.08}
        minDistance={minDistance}
        maxDistance={maxDistance}
        minPolarAngle={Math.PI / 9}
        // Stay above the terrain: never reach the horizon, let alone go under it.
        maxPolarAngle={(5 * Math.PI) / 12}
        minAzimuthAngle={-Math.PI / 4}
        maxAzimuthAngle={Math.PI / 4}
      />
    );
  },
);
