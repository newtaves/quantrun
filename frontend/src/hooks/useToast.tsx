import React, { createContext, useContext, useState, useCallback, useRef } from 'react';

type ToastType = 'success' | 'error' | 'info';

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  addToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({ addToast: () => {} });

export const useToast = () => useContext(ToastContext);

let nextId = 0;

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  const removeToast = useCallback((id: number) => {
    const t = timers.current.get(id);
    if (t) { clearTimeout(t); timers.current.delete(id); }
    setToasts(prev => prev.filter(x => x.id !== id));
  }, []);

  const addToast = useCallback((message: string, type: ToastType = 'error') => {
    const id = nextId++;
    setToasts(prev => [...prev, { id, type, message }]);
    const timer = setTimeout(() => removeToast(id), 5000);
    timers.current.set(id, timer);
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div style={{
        position: 'fixed', top: '20px', right: '20px', zIndex: 9999,
        display: 'flex', flexDirection: 'column', gap: '8px',
        pointerEvents: 'none', maxWidth: '400px',
      }}>
        {toasts.map(t => (
          <div
            key={t.id}
            onClick={() => removeToast(t.id)}
            style={{
              pointerEvents: 'auto', cursor: 'pointer',
              padding: '12px 16px',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.78rem',
              fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: '10px',
              border: `1px solid ${t.type === 'success' ? 'var(--success)' : t.type === 'error' ? 'var(--danger)' : 'var(--warning)'}`,
              background: 'var(--panel-bg)',
              color: t.type === 'success' ? 'var(--success)' : t.type === 'error' ? 'var(--danger)' : 'var(--warning)',
              boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
              animation: 'toast-in 0.2s ease-out',
            }}
          >
            <span style={{ fontWeight: 900, fontSize: '0.7rem' }}>
              {t.type === 'success' ? '[OK]' : t.type === 'error' ? '[ERR]' : '[!]'}
            </span>
            <span style={{ flex: 1 }}>{t.message}</span>
            <span style={{ opacity: 0.4, fontSize: '0.65rem' }}>DISMISS</span>
          </div>
        ))}
      </div>
      <style>{`
        @keyframes toast-in {
          from { opacity: 0; transform: translateX(20px); }
          to { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </ToastContext.Provider>
  );
};
