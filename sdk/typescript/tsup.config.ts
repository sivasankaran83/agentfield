import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts', 'examples/simulation/main.ts', 'examples/discovery-memory/main.ts'],
  format: ['esm'],
  dts: true,
  splitting: false,
  sourcemap: true,
  clean: true,
  treeshake: true
});
