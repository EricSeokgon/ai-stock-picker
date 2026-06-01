import '@testing-library/jest-dom';

// jsdom은 ResizeObserver를 지원하지 않음 — Recharts ResponsiveContainer용 polyfill
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
