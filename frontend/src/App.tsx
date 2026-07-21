import { Dashboard } from './components/Dashboard';
import { ToastProvider } from './hooks/useToast';

function App() {
  return (
    <ToastProvider>
      <Dashboard />
    </ToastProvider>
  );
}

export default App;
