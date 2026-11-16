import type { ThreeElements } from '@react-three/fiber';

declare global {
  namespace React.JSX {
    interface IntrinsicElements extends ThreeElements {}
  }
}
