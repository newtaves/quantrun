import React, { createContext, useContext, useState } from 'react';

type Toast = { id: number; message: string; type: 'success' | 'error' };
const ToastContext = createContext<{ addToast: (message: string, type: Toast['type']) => void }>({ addToast: () => {} });

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const addToast = (message: string, type: Toast['type']) => {
    const id = Date.now();
    setToasts(items => [...items, { id, message, type }]);
    window.setTimeout(() => setToasts(items => items.filter(item => item.id !== id)), 3500);
  };
  return <ToastContext.Provider value={{ addToast }}>{children}<div className="toast-container">{toasts.map(t => <div key={t.id} className={`toast ${t.type}`}>{t.message}</div>)}</div></ToastContext.Provider>;
};
export const useToast = () => useContext(ToastContext);
