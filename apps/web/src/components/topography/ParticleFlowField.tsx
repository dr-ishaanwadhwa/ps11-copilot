'use client';

import React, { useRef, useMemo, useEffect } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

interface ParticleFlowFieldProps {
  particleCount?: number;
}

export function ParticleFlowField({ particleCount = 1200 }: ParticleFlowFieldProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  // Initialize particle positions and velocities
  const particles = useMemo(() => {
    return Array.from({ length: particleCount }, () => ({
      x: (Math.random() - 0.5) * 80,
      y: (Math.random() - 0.5) * 12,
      z: (Math.random() - 0.5) * 25,
      speed: 0.15 + Math.random() * 0.35,
      scale: 0.2 + Math.random() * 0.4,
    }));
  }, [particleCount]);

  useEffect(() => {
    if (!meshRef.current) return;
    const color = new THREE.Color();

    for (let i = 0; i < particleCount; i++) {
      const p = particles[i];
      dummy.position.set(p.x, p.y, p.z);
      dummy.scale.set(p.scale, p.scale, p.scale);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);

      // Inflow particles (emerald), Outflow particles (sky blue/amber)
      if (p.x < 0) {
        color.set(0x38bdf8); // Inflow sky
      } else {
        color.set(0x10b981); // Surplus emerald
      }
      meshRef.current.setColorAt(i, color);
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true;
    }
  }, [particles, particleCount, dummy]);

  useFrame(() => {
    if (!meshRef.current) return;

    for (let i = 0; i < particleCount; i++) {
      const p = particles[i];
      p.x += p.speed;

      // Wrap around bounds
      if (p.x > 40) {
        p.x = -40;
        p.y = (Math.random() - 0.5) * 10;
      }

      dummy.position.set(p.x, p.y + Math.sin(p.x * 0.1) * 2, p.z);
      dummy.scale.set(p.scale, p.scale, p.scale);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  const sphereGeometry = useMemo(() => new THREE.SphereGeometry(0.5, 6, 6), []);
  const material = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.8,
      }),
    []
  );

  return (
    <instancedMesh
      ref={meshRef}
      args={[sphereGeometry, material, particleCount]}
    />
  );
}
