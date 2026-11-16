# 03. 3D Spatial Topography Specification (Three.js & React Three Fiber)

**Specification ID:** `SPEC-3D-003`  
**Classification:** Modular Engineering Specification  
**Target Repository:** `/Users/ishaanwadhwa/Projects/ps11-copilot`  
**Related Blueprint:** `docs/blueprints/nextjs-threejs-cashflow-copilot.md` §4  
**Related Invariants:** 60fps Performance Budget, WebGL Context Loss Recovery, 2D Fallback

---

## 1. Spatial Metaphor & Cartesian Coordinates

The 3D Spatial Cashflow Topography transforms 90 days of abstract balance sheets into an intuitive cartographic landscape:

```
                  [GREEN LIQUIDITY PLATEAU]
                     Y > 0: Usable Cash Buffer
                           /\
                          /  \
                         /    \     [AMBER STRENGTH RIDGE]
                        /      \      P50 Median Flow
                       /        \_________
                      /                   \
─────────────────────/─────────────────────\────────────────────── Y = 0 (Zero Cash Floor)
                    /                       \
                   /                         \______ [RED CC DANGER CLIFF]
                  /                                   Y = -₹25,00,000 Limit
                 /
      [PAYROLL TROUGH (CANYON)]
         1 Oct Salary Dip
```

### 1.1 Cartesian Axis Mapping
- **$X$-Axis (Timeline):** Continuous timeline spanning 90 days from $T_0$ (Today) to $T_{+90}$ (End of Quarter).
- **$Y$-Axis (Liquidity Elevation):** Rupee balance heightfield:
  - Plateaus ($Y > 0$): Rolling emerald green hills indicating spendable solvency (Bank + Drawer Cash).
  - Canyons ($Y < 0$): Valleys indicating statutory obligations (1 Oct Payroll, 20 Oct GST).
  - Translucent Red Floor ($Y = -₹25,00,000$): Fixed plane representing the Cash-Credit overdraft facility limit.
- **$Z$-Axis (Probability Envelopes):**
  - $Z_{-1}$: Conservative P10 trajectory (southern shoulder).
  - $Z_0$: Expected P50 median path (central ridgeline).
  - $Z_{+1}$: Optimistic P90 trajectory (northern shoulder).

---

## 2. Scene Graph & R3F Component Hierarchy

```tsx
<Canvas
  camera={{ position: [0, 55, 95], fov: 42, near: 0.1, far: 1000 }}
  dpr={[1, 2]}
  gl={{ antialias: true, alpha: false, powerPreference: 'high-performance' }}
>
  <color attach="background" args={['#020617']} />
  
  {/* Baked Lighting: Real-time shadow maps disabled to stay under draw call budget */}
  <ambientLight intensity={0.6} />
  <directionalLight position={[30, 60, 40]} intensity={1.0} castShadow={false} />
  <pointLight position={[0, 15, 0]} intensity={0.8} color="#22C55E" />

  <TopographyCameraRig />

  <group position={[-45, 0, 0]}>
    {/* 1. Continuous Procedural Heightfield Surface (1 Draw Call) */}
    <TerrainMesh points={dailyForecastPoints} creditLimit={2500000} />

    {/* 2. Translucent Sanctioned Credit Facility Limit Plane (1 Draw Call) */}
    <CreditLimitPlane limit={2500000} width={90} depth={30} />

    {/* 3. GPU Instanced Cash Velocity Vector Field (1 Draw Call, 1,500 particles) */}
    <ParticleFlowField particleCount={1500} velocityVectors={flowVectors} />

    {/* 4. Milestone Landmark Pins (Instanced Stems + HTML Billboards) */}
    <InstancedMilestonePins landmarks={milestonePins} />
  </group>
</Canvas>
```

---

## 3. Custom GLSL Shader Material & Procedural Isolines

The terrain mesh uses a custom Three.js `ShaderMaterial`. Vertices are dynamically displaced along $Y$ using daily P10/P50/P90 simulation data. The fragment shader procedurally renders cartographic contour lines (isolines) that snap to exact multiples of ₹1,00,000 without requiring expensive geometry subdivisions:

```glsl
// Fragment Shader: terrain.frag.glsl
precision highp float;

varying vec3 vPosition;
varying float vElevation;

uniform vec3 uColorSurplus;   // OKLCH Emerald vec3(0.14, 0.65, 0.32)
uniform vec3 uColorDeficit;   // OKLCH Ruby vec3(0.86, 0.15, 0.15)
uniform vec3 uColorWarning;   // OKLCH Amber vec3(0.85, 0.47, 0.02)
uniform float uCreditLimit;   // e.g. 2500000.0

void main() {
  // Normalize elevation relative to standard scale
  float normElevation = vElevation / 3000000.0;
  vec3 baseColor = mix(uColorDeficit, uColorSurplus, smoothstep(-0.5, 1.0, normElevation));

  // Procedural Topographic Isolines (Every ₹1,00,000)
  float isofactor = fract(vElevation / 100000.0);
  float line = smoothstep(0.02, 0.0, min(isofactor, 1.0 - isofactor));

  // Translucent danger wash if below CC limit floor
  if (vElevation < -uCreditLimit) {
    baseColor = vec3(0.85, 0.12, 0.12);
  }

  vec3 finalColor = mix(baseColor, vec3(1.0, 1.0, 1.0), line * 0.35);
  gl_FragColor = vec4(finalColor, 0.95);
}
```

---

## 4. Instanced Particle Flow Velocity Field

To visualize liquidity flow without bogging down the CPU or triggering garbage collection spikes, 1,500 particles are rendered via a single `THREE.InstancedMesh`:
- **Inflow Particles:** Emerge from customer retail nodes and converge into the central bank peak along cubic Bezier curves.
- **Outflow Particles:** Stream downward into vendor payables and salary canyon floors.
- **Velocity Formula:** Particle velocity scales with the square root of the transaction volume:
  $$v_i = v_{\text{base}} \cdot \sqrt{\frac{\text{Amount}_i}{\text{Median Transaction Amount}}}$$
- **Draw Call Efficiency:** Exactly **1 draw call** on the GPU; transforms are updated using a typed `Float32Array` matrix buffer.

---

## 5. Constrained Camera Kinematics & Cinematic Fly-Throughs

The camera rig uses `OrbitControls` with strict physical constraints to prevent spatial disorientation:
- **Polar Angle Clamping:** Clamped between $20^\circ$ and $75^\circ$ ($\frac{\pi}{9} \le \theta \le \frac{5\pi}{12}$), preventing the camera from flipping underneath the terrain or looking straight down.
- **Azimuth Angle Clamping:** Clamped to $[-45^\circ, +45^\circ]$ relative to the forward view axis, keeping the left-to-right chronological timeline oriented correctly.
- **Cinematic Fly-Through Presets:**
  1. `Macro Horizon`: Isometric overview of the complete 90-day trajectory.
  2. `Galla Close-Up`: Camera swoops to today's cash drawer float ($T_0$).
  3. `1 Oct Payroll Glide`: Low-angle valley flight verifying clearance above the CC danger limit floor.
  4. `Scenario Morphing`: Real-time vertex repositioning as the user drags stress sliders.

---

## 6. Performance Budget & Resource Allocations

To guarantee locked 60fps performance on standard integrated GPUs and budget Android tablets:

| Resource Metric | Budget Ceiling | Architectural Rationale |
|---|---|---|
| **Draw Calls** | $\le 32$ total draw calls | Keeps CPU command preparation under $2\text{ms}$ per frame. |
| **Triangles / Vertices** | $128 \times 64 = 8,192$ quads ($16,384$ triangles) | Low vertex count allows instant CPU/GPU morphing during slider dragging. |
| **Texture Memory** | $\le 16\text{MB}$ | Shaders are pure mathematical procedurals; zero heavy image textures. |
| **Frame Rate** | Locked 60fps (Frame time $\le 16.6\text{ms}$) | Smooth gesture panning on 90Hz/120Hz mobile screens. |

---

## 7. WebGL Context Loss Recovery Lifecycle

Cashiers routinely switch tabs or lock screens. Budget devices aggressively reclaim GPU contexts. The application handles WebGL context events deterministically:

1. **Context Loss Interception:**
   ```typescript
   canvas.addEventListener('webglcontextlost', (e) => {
     e.preventDefault();
     disposeThreeScene(scene);
     setIsContextLost(true); // Mounts Fallback2DTopography seamlessly
   }, false);
   ```
2. **Context Restoration & Epoch Remounting:**
   ```typescript
   canvas.addEventListener('webglcontextrestored', () => {
     setWebglEpoch((prev) => prev + 1); // Forces fresh Canvas mount and VBO allocation
     setIsContextLost(false);
   }, false);
   ```
3. **Deep Resource Cleanup:** Traverses the scene graph on unmount and explicitly calls `.dispose()` on all geometries, materials, and textures.

---

## 8. 2D Canvas / SVG Fallback Mode (`Fallback2DTopography`)

For low-end hardware, battery saver mode, or during WebGL context loss, the interface mounts a pure 2D elevation fallback:
- **Eradication of DOM Thrashing:** Replaces 1,500 moving SVG circle nodes with **48 lightweight CSS-animated flow stream gradient strokes** (`stroke-dasharray` and `stroke-dashoffset` keyframes). Layout calculation time drops from $40\text{ms}$ to $<0.5\text{ms}$, maintaining locked 60fps.
- **Full Data Parity:** Renders P10, P50, and P90 area envelopes, the sanctioned credit limit line, and milestone pin callouts with 100% numerical parity to the 3D scene.
