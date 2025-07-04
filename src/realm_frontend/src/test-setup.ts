import { vi } from 'vitest';

Object.defineProperty(globalThis, 'window', {
  value: globalThis.window || {},
  writable: true
});

Object.defineProperty(globalThis, 'document', {
  value: globalThis.document || {},
  writable: true
});

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

globalThis.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

globalThis.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

Object.defineProperty(window, 'URL', {
  writable: true,
  value: class MockURL extends URL {
    static createObjectURL = vi.fn(() => 'mock-blob-url');
    static revokeObjectURL = vi.fn();
    
    constructor(url, base) {
      super(url || 'http://localhost', base);
    }
  },
});

vi.mock('$app/navigation', () => ({
  goto: vi.fn(),
  afterNavigate: vi.fn()
}));

vi.mock('$app/stores', () => ({
  page: {
    subscribe: vi.fn(() => () => {}),
    url: { pathname: '/' }
  }
}));

vi.mock('maplibre-gl', () => ({
  default: {
    Map: vi.fn().mockImplementation(() => ({
      addControl: vi.fn(),
      on: vi.fn(),
      addSource: vi.fn(),
      addLayer: vi.fn(),
      fitBounds: vi.fn(),
      getCanvas: vi.fn(() => ({
        style: { cursor: '' }
      }))
    })),
    NavigationControl: vi.fn(),
    FullscreenControl: vi.fn(),
    Popup: vi.fn().mockImplementation(() => ({
      setLngLat: vi.fn().mockReturnThis(),
      setHTML: vi.fn().mockReturnThis(),
      addTo: vi.fn().mockReturnThis()
    })),
    LngLatBounds: vi.fn().mockImplementation(() => ({
      extend: vi.fn(),
      isEmpty: vi.fn(() => false)
    }))
  }
}));
