'use client';

import React, { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import type { ForecastSimulationPoint } from '@/lib/types';

interface TerrainMeshProps {
  points?: ForecastSimulationPoint[];
  creditLimit?: number;
}

const vertexShader = `
  varying vec3 vPosition;
  varying float vElevation;

  void main() {
    vPosition = position;
    vElevation = position.z;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const fragmentShader = `
  precision highp float;

  varying vec3 vPosition;
  varying float vElevation;

  uniform vec3 uColorSurplus;   // Emerald
  uniform vec3 uColorDeficit;   // Ruby
  uniform vec3 uColorWarning;   // Amber
  uniform float uCreditLimit;

  void main() {
    float normElevation = vElevation / 15.0;
    vec3 baseColor = mix(uColorDeficit, uColorSurplus, smoothstep(-0.5, 0.8, normElevation));

    // Procedural Topographic Isolines
    float isofactor = fract(vElevation * 0.8);
    float line = smoothstep(0.04, 0.0, min(isofactor, 1.0 - isofactor));

    // Danger wash if below CC facility limit floor
    if (vElevation < -8.0) {
      baseColor = vec3(0.85, 0.15, 0.15);
    }

    vec3 finalColor = mix(baseColor, vec3(1.0, 1.0, 1.0), line * 0.4);
    gl_FragColor = vec4(finalColor, 0.92);
  }
`;

export function TerrainMesh({ creditLimit = 2500000 }: TerrainMeshProps) {
  const meshRef = useRef<THREE.Mesh>(null);

  const { geometry, uniforms } = useMemo(() => {
    const geom = new THREE.PlaneGeometry(90, 30, 90, 30);
    const pos = geom.attributes.position;

    // Displace vertices along Z (which becomes height after rotation)
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const y = pos.getY(i);

      // Heightfield formula simulating cash peaks and salary dips
      const timePhase = (x + 45) / 90; // 0 to 1
      let elevation = Math.sin(timePhase * Math.PI * 2.5) * 6.0;

      // Salary dip at 1 Oct (near beginning)
      if (timePhase > 0.05 && timePhase < 0.18) {
        elevation -= 7.5 * Math.sin(((timePhase - 0.05) / 0.13) * Math.PI);
      }

      // Add cross-sectional ridge across categories (Y axis)
      elevation += Math.cos((y / 15) * Math.PI * 0.5) * 3.0;

      pos.setZ(i, elevation);
    }

    geom.computeVertexNormals();

    const u = {
      uColorSurplus: { value: new THREE.Color(0x10b981) },
      uColorDeficit: { value: new THREE.Color(0xef4444) },
      uColorWarning: { value: new THREE.Color(0xf59e0b) },
      uCreditLimit: { value: creditLimit },
    };

    return { geometry: geom, uniforms: u };
  }, [creditLimit]);

  useFrame((state) => {
    if (meshRef.current) {
      // Subtle organic breathing animation
      const t = state.clock.getElapsedTime();
      meshRef.current.position.y = Math.sin(t * 0.5) * 0.2;
    }
  });

  return (
    <mesh
      ref={meshRef}
      geometry={geometry}
      rotation={[-Math.PI / 2.5, 0, 0]}
      position={[0, 0, 0]}
    >
      <shaderMaterial
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        transparent
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}
