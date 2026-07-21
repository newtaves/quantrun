import React, { useState, useEffect } from 'react';
import { PortfolioDetail } from './PortfolioDetail';
import { TradingTerminal } from './TradingTerminal';
import { ChartBrowser } from './ChartBrowser';
import { listPortfolios, createPortfolio, deletePortfolio } from '../api/api';
import { usePricesWs } from '../hooks/useWs';
import { useToast } from '../hooks/useToast';
import {
  Plus,
  Terminal,
  Briefcase,
  BarChart3,
  Sun,
  Moon,
  X,
  Trash2
} from 'lucide-react';

interface Portfolio {
  portfolio_id: number;
  name: string;
  description: string;
  available_cash: number;
  invested_cash: number;
}

export const Dashboard: React.FC = () => {
  const prices = usePricesWs();
  const { addToast } = useToast();
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState<Portfolio | null>(null);
  const [currentTab, setCurrentTab] = useState<'trading' | 'charts'>('trading');
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('theme') as 'light' | 'dark') || 'dark';
  });

  // Modal
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [newPortName, setNewPortName] = useState<string>('');
  const [newPortDesc, setNewPortDesc] = useState<string>('');
  const [newPortCash, setNewPortCash] = useState<string>('100000');
  const [isCreating, setIsCreating] = useState<boolean>(false);

  useEffect(() => {
    if (theme === 'light') {
      document.body.classList.add('light-mode');
    } else {
      document.body.classList.remove('light-mode');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  const fetchPortfolios = async () => {
    try {
      const data = await listPortfolios();
      setPortfolios(data.portfolios || []);
    } catch (e) {
      console.error("Failed to load portfolios", e);
    }
  };

  useEffect(() => {
    fetchPortfolios();
  }, []);

  const handleCreatePortfolio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPortName.trim()) return;
    const cash = parseFloat(newPortCash);
    if (isNaN(cash) || cash <= 0) {
      alert('Please enter a valid cash amount');
      return;
    }
    setIsCreating(true);
    try {
      const data = await createPortfolio(newPortName.trim(), cash, newPortDesc.trim());
      setNewPortName('');
      setNewPortDesc('');
      setNewPortCash('100000');
      setIsModalOpen(false);
      if (data.portfolio && data.portfolio.portfolio_id) {
        setSelectedPortfolio(data.portfolio);
      }
      await fetchPortfolios();
      addToast('Portfolio created successfully', 'success');
    } catch (err: any) {
      addToast(err.message || 'Failed to create portfolio', 'error');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeletePortfolio = async (id: number) => {
    if (!window.confirm('DELETE PORTFOLIO? All positions and orders will be lost.')) return;
    try {
      await deletePortfolio(id);
      if (selectedPortfolio?.portfolio_id === id) setSelectedPortfolio(null);
      await fetchPortfolios();
      addToast('Portfolio deleted', 'success');
    } catch (e: any) {
      addToast(e.message || 'Failed to delete portfolio', 'error');
    }
  };

  const toggleTheme = () => setTheme(prev => prev === 'dark' ? 'light' : 'dark');

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '260px 1fr',
      minHeight: '100vh',
      background: 'var(--bg-color)',
      position: 'relative'
    }}>
      {/* LEFT SIDEBAR */}
      <aside className="glass-panel" style={{
        margin: '16px 0 16px 16px',
        padding: '20px 16px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        height: 'calc(100vh - 32px)',
        position: 'sticky',
        top: '16px'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingLeft: '8px' }}>
            <div style={{
              width: '28px', height: '28px',
              background: 'var(--text-primary)', color: 'var(--bg-color)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              border: '1px solid var(--text-primary)'
            }}>
              <Terminal size={16} style={{ strokeWidth: 2.5 }} />
            </div>
            <span style={{ fontSize: '1rem', fontWeight: 800, letterSpacing: '0.08em', fontFamily: 'JetBrains Mono, monospace' }}>
              QUANTRUN
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-muted)', paddingLeft: '8px', letterSpacing: '0.1em', fontFamily: 'JetBrains Mono, monospace', marginBottom: '4px' }}>
              TRADING PORTFOLIOS
            </span>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '180px', overflowY: 'auto', paddingRight: '4px' }}>
              {portfolios.map((p) => (
                <div key={p.portfolio_id} style={{ display: 'flex', alignItems: 'center', gap: '4px', minWidth: 0 }}>
                  <button
                  onClick={() => { setSelectedPortfolio(p); setCurrentTab('trading'); }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '10px', flex: 1,
                    minWidth: 0, overflow: 'hidden',
                    padding: '8px 10px',
                    border: '1px solid ' + (currentTab === 'trading' && selectedPortfolio?.portfolio_id === p.portfolio_id ? 'var(--text-primary)' : 'transparent'),
                    background: currentTab === 'trading' && selectedPortfolio?.portfolio_id === p.portfolio_id ? 'var(--panel-hover)' : 'transparent',
                    color: currentTab === 'trading' && selectedPortfolio?.portfolio_id === p.portfolio_id ? 'var(--text-primary)' : 'var(--text-secondary)',
                    fontWeight: currentTab === 'trading' && selectedPortfolio?.portfolio_id === p.portfolio_id ? 700 : 500,
                      textAlign: 'left', cursor: 'pointer', fontSize: '0.8rem',
                      fontFamily: 'JetBrains Mono, monospace'
                    }}
                  >
                    <Briefcase size={14} style={{ flexShrink: 0 }} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name.toUpperCase()}</span>
                  </button>
                  <button
                    onClick={() => handleDeletePortfolio(p.portfolio_id)}
                    style={{
                      background: 'none', border: 'none', color: 'var(--text-muted)',
                      cursor: 'pointer', padding: '4px'
                    }}
                    title="Delete portfolio"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={() => setIsModalOpen(true)}
              className="btn btn-secondary"
              style={{ marginTop: '4px', padding: '6px 10px', fontSize: '0.72rem', justifyContent: 'center', gap: '6px', borderStyle: 'dashed' }}
            >
              <Plus size={12} /> NEW PORTFOLIO
            </button>

            <div style={{ height: '1px', background: 'var(--panel-border)', margin: '10px 0' }} />

            <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-muted)', paddingLeft: '8px', letterSpacing: '0.1em', fontFamily: 'JetBrains Mono, monospace', marginBottom: '4px' }}>
              MARKET DATA
            </span>

            <button
              onClick={() => { setCurrentTab('charts'); setSelectedPortfolio(null); }}
              style={{
                display: 'flex', alignItems: 'center', gap: '10px', width: '100%',
                padding: '8px 10px',
                border: '1px solid ' + (currentTab === 'charts' ? 'var(--text-primary)' : 'transparent'),
                background: currentTab === 'charts' ? 'var(--panel-hover)' : 'transparent',
                color: currentTab === 'charts' ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: currentTab === 'charts' ? 700 : 500,
                cursor: 'pointer', fontSize: '0.8rem', fontFamily: 'JetBrains Mono, monospace'
              }}
            >
              <BarChart3 size={14} />
              PRICE CHARTS
            </button>
          </div>
        </div>

        {/* Footer */}
        <div style={{ borderTop: '1px solid var(--panel-border)', paddingTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <button onClick={toggleTheme} className="theme-toggle-btn" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', width: '100%', padding: '6px' }}>
            {theme === 'dark' ? <><Sun size={12} /> LIGHT MODE</> : <><Moon size={12} /> NIGHT MODE</>}
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingLeft: '4px' }}>
            <div style={{
              width: '28px', height: '28px',
              border: '1px solid var(--panel-border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--text-primary)', fontWeight: 700, fontSize: '0.8rem',
              fontFamily: 'JetBrains Mono, monospace'
            }}>QR</div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
                QUANTRUN
              </span>
              <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
                PAPER TRADING ENGINE
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* MAIN WORKSPACE */}
      <main style={{ padding: '24px 32px 32px 32px', maxHeight: '100vh', overflowY: 'auto' }}>
        {currentTab === 'charts' ? (
          <ChartBrowser />
        ) : selectedPortfolio ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px', alignItems: 'start' }}>
            <PortfolioDetail
              portfolio={selectedPortfolio}
              onRefresh={fetchPortfolios}
            />
            <TradingTerminal
              portfolioId={selectedPortfolio.portfolio_id}
              prices={prices}
              onOrderPlaced={fetchPortfolios}
            />
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 'calc(100vh - 60px)' }}>
            <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', maxWidth: '500px' }}>
              <div style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                width: '48px', height: '48px', background: 'var(--panel-hover)',
                color: 'var(--text-primary)', border: '1px solid var(--panel-border)', marginBottom: '16px'
              }}>
                <Terminal size={24} />
              </div>
              <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace', marginBottom: '8px' }}>
                MATCHING DESK OFFLINE
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', fontFamily: 'JetBrains Mono, monospace', lineHeight: 1.6, marginBottom: '20px' }}>
                Select an active portfolio from the sidebar to examine positions and trade. Create a new portfolio to allocate paper capital.
              </p>
              <button onClick={() => setIsModalOpen(true)} className="btn btn-primary" style={{ padding: '10px 20px' }}>
                <Plus size={14} /> NEW TRADING PORTFOLIO
              </button>
            </div>
          </div>
        )}
      </main>

      {/* CREATE PORTFOLIO MODAL */}
      {isModalOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0, 0, 0, 0.7)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 100
        }}>
          <div className="glass-panel" style={{
            width: '100%', maxWidth: '400px', padding: '24px', position: 'relative',
            background: 'var(--panel-bg)', border: '1px solid var(--text-primary)'
          }}>
            <button onClick={() => setIsModalOpen(false)} style={{
              position: 'absolute', top: '12px', right: '12px',
              background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer'
            }}>
              <X size={16} />
            </button>

            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', marginBottom: '16px' }}>
              INITIALIZE PORTFOLIO
            </h3>

            <form onSubmit={handleCreatePortfolio} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div className="form-group">
                <label className="form-label">PORTFOLIO NAME</label>
                <input type="text" required className="form-input" placeholder="e.g. DAYTRADING_BOT"
                  value={newPortName} onChange={(e) => setNewPortName(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">STRATEGY DESCRIPTION</label>
                <textarea className="form-input" placeholder="Strategy description..."
                  style={{ minHeight: '60px', resize: 'none' }}
                  value={newPortDesc} onChange={(e) => setNewPortDesc(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">CAPITAL ALLOCATION ($)</label>
                <input type="number" required className="form-input" placeholder="100000"
                  value={newPortCash} onChange={(e) => setNewPortCash(e.target.value)} />
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '10px', marginTop: '6px' }} disabled={isCreating}>
                {isCreating ? 'ALLOCATING...' : 'ALLOCATE CAPITAL & DEPLOY'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
