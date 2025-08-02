declare global {
  interface Window {
    initializeLogStream?: (sessionId: string) => void;
  }
}

export {};
