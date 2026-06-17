import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { PortfolioDetail } from './PortfolioDetail';
import { TradingTerminal } from './TradingTerminal';
import { TokenManager } from './TokenManager';
import { ChartBrowser } from './ChartBrowser';
import { 
  LogOut, 
  Key, 
  Plus, 
  Terminal, 
  Briefcase,
  BarChart3,
  Sun,
  Moon,
  X 
} from 'lucide-react';

interface Portfolio {
  id: number;
  name: string;
  description: string;
  available_cash: number;
  invested_cash: number;
}

export const Dashboard: React.FC = () => {
  const { user, token, logout } = useAuth();
  
  // Probed ports
  const [fastapiPort, setFastapiPort] = useState<string>("8001");
  const [fastapiBaseUrl, setFastapiBaseUrl] = useState<string>("http://localhost:8001");
  
  // Workspace States
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState<Portfolio | null>(null);
  const [currentTab, setCurrentTab] = useState<'trading' | 'tokens' | 'charts'>('trading');

  // Night Mode / Light Mode Theme State
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('theme') as 'light' | 'dark') || 'dark';
  });

  // Modal States
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [newPortName, setNewPortName] = useState<string>('');
  const [newPortDesc, setNewPortDesc] = useState<string>('');
  const [newPortCash, setNewPortCash] = useState<string>('100000');
  const [isCreating, setIsCreating] = useState<boolean>(false);

  // Sync theme with body class list
  useEffect(() => {
    if (theme === 'light') {
      document.body.classList.add('light-mode');
    } else {
      document.body.classList.remove('light-mode');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Auto-probe FastAPI port on startup
  useEffect(() => {
    const probeFastApi = async () => {
      const ports = ["8001", "8000"]; 
      for (const port of ports) {
        try {
          const controller = new AbortController();
          const id = setTimeout(() => controller.abort(), 800); // quick probe
          const resp = await fetch(`http://localhost:${port}/prices`, { signal: controller.signal });
          clearTimeout(id);
          if (resp.ok) {
            setFastapiPort(port);
            setFastapiBaseUrl(`http://localhost:${port}`);
            console.log(`Dynamic Port Scanner: FastAPI active on port ${port}`);
            return;
          }
        } catch (e) {
          // continue checking
        }
      }
      console.warn("Dynamic Port Scanner: Defaulting to port 8001.");
    };
    probeFastApi();
  }, []);

  const fetchPortfolios = async () => {
    if (!token) return;
    try {
      const resp = await fetch(`${fastapiBaseUrl}/portfolio`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (resp.ok) {
        const data = await resp.json();
        const list = data.portfolios || [];
        setPortfolios(list);
        
        // Retain selected portfolio references if they still exist
        if (selectedPortfolio) {
          const updated = list.find((p: Portfolio) => p.id === selectedPortfolio.id);
          if (updated) setSelectedPortfolio(updated);
        }
      }
    } catch (e) {
      console.error("Failed to load portfolios from FastAPI", e);
    }
  };

  // Re-fetch portfolios whenever FastAPI URL/Port changes
  useEffect(() => {
    fetchPortfolios();
  }, [fastapiBaseUrl, token]);

  const handleCreatePortfolio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPortName.trim() || !token) return;

    const cash = parseFloat(newPortCash);
    if (isNaN(cash) || cash <= 0) {
      alert('Please enter a valid cash amount');
      return;
    }

    setIsCreating(true);
    try {
      const resp = await fetch(`${fastapiBaseUrl}/portfolio`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: newPortName.trim(),
          description: newPortDesc.trim() || 'Custom algo portfolio',
          available_cash: cash,
          invested_cash: 0.0,
          total_pnl: 0.0,
          user_id: user?.id || 0 
        })
      });

      if (resp.ok) {
        const data = await resp.json();
        setNewPortName('');
        setNewPortDesc('');
        setNewPortCash('100000');
        setIsModalOpen(false);
        await fetchPortfolios();
        
        // Auto select newly created portfolio
        if (data.portfolio) {
          setSelectedPortfolio(data.portfolio);
        }
      } else {
        const errData = await resp.json();
        alert(errData.detail || 'Failed to create portfolio');
      }
    } catch (err) {
      alert('Network error connecting to FastAPI');
    } finally {
      setIsCreating(false);
    }
  };

  const handleSelectPortfolio = (p: Portfolio) => {
    setSelectedPortfolio(p);
    setCurrentTab('trading');
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '260px 1fr',
      minHeight: '100vh',
      background: 'var(--bg-color)',
      position: 'relative'
    }}>
      
      {/* LEFT SIDEBAR PANEL */}
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
          
          {/* Logo Heading */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingLeft: '8px' }}>
            <div style={{
              width: '28px',
              height: '28px',
              background: 'var(--text-primary)',
              color: 'var(--bg-color)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid var(--text-primary)'
            }}>
              <Terminal size={16} style={{ strokeWidth: 2.5 }} />
            </div>
            <span style={{ fontSize: '1rem', fontWeight: 800, letterSpacing: '0.08em', fontFamily: 'JetBrains Mono, monospace' }}>
              QUANTRUN
            </span>
          </div>

          {/* Navigation Links */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-muted)', paddingLeft: '8px', letterSpacing: '0.1em', fontFamily: 'JetBrains Mono, monospace', marginBottom: '4px' }}>
              TRADING PORTFOLIOS
            </span>
            
            {/* Portfolios Navigation */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '180px', overflowY: 'auto', paddingRight: '4px' }}>
              {portfolios.map((p) => (
                <button
                  key={p.id}
                  onClick={() => handleSelectPortfolio(p)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    width: '100%',
                    padding: '8px 10px',
                    border: '1px solid ' + (currentTab === 'trading' && selectedPortfolio?.id === p.id ? 'var(--text-primary)' : 'transparent'),
                    background: currentTab === 'trading' && selectedPortfolio?.id === p.id ? 'var(--panel-hover)' : 'transparent',
                    color: currentTab === 'trading' && selectedPortfolio?.id === p.id ? 'var(--text-primary)' : 'var(--text-secondary)',
                    fontWeight: currentTab === 'trading' && selectedPortfolio?.id === p.id ? 700 : 500,
                    textAlign: 'left',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    fontFamily: 'JetBrains Mono, monospace'
                  }}
                >
                  <Briefcase size={14} />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name.toUpperCase()}</span>
                </button>
              ))}
            </div>

            {/* Create New Portfolio Button */}
            <button
              onClick={() => setIsModalOpen(true)}
              className="btn btn-secondary"
              style={{
                marginTop: '4px',
                padding: '6px 10px',
                fontSize: '0.72rem',
                justifyContent: 'center',
                gap: '6px',
                borderStyle: 'dashed'
              }}
            >
              <Plus size={12} /> NEW PORTFOLIO
            </button>

            {/* Divider */}
            <div style={{ height: '1px', background: 'var(--panel-border)', margin: '10px 0' }} />

            <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-muted)', paddingLeft: '8px', letterSpacing: '0.1em', fontFamily: 'JetBrains Mono, monospace', marginBottom: '4px' }}>
              SYSTEM DESK
            </span>

            {/* Historical Charts Tab Button */}
            <button
              onClick={() => {
                setCurrentTab('charts');
                setSelectedPortfolio(null);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                width: '100%',
                padding: '8px 10px',
                border: '1px solid ' + (currentTab === 'charts' ? 'var(--text-primary)' : 'transparent'),
                background: currentTab === 'charts' ? 'var(--panel-hover)' : 'transparent',
                color: currentTab === 'charts' ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: currentTab === 'charts' ? 700 : 500,
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontFamily: 'JetBrains Mono, monospace'
              }}
            >
              <BarChart3 size={14} />
              CHARTS BROWSER
            </button>
            
            {/* Tokens Tab Button */}
            <button
              onClick={() => {
                setCurrentTab('tokens');
                setSelectedPortfolio(null);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                width: '100%',
                padding: '8px 10px',
                border: '1px solid ' + (currentTab === 'tokens' ? 'var(--text-primary)' : 'transparent'),
                background: currentTab === 'tokens' ? 'var(--panel-hover)' : 'transparent',
                color: currentTab === 'tokens' ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: currentTab === 'tokens' ? 700 : 500,
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontFamily: 'JetBrains Mono, monospace'
              }}
            >
              <Key size={14} />
              API CREDENTIALS
            </button>
          </div>
        </div>

        {/* User Account Info and Log Out */}
        <div style={{
          borderTop: '1px solid var(--panel-border)',
          paddingTop: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
        }}>
          
          {/* Night Mode Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            className="theme-toggle-btn"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              width: '100%',
              padding: '6px'
            }}
          >
            {theme === 'dark' ? (
              <>
                <Sun size={12} />
                LIGHT MODE
              </>
            ) : (
              <>
                <Moon size={12} />
                NIGHT MODE
              </>
            )}
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingLeft: '4px' }}>
            <div style={{
              width: '28px',
              height: '28px',
              border: '1px solid var(--panel-border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-primary)',
              fontWeight: 700,
              fontSize: '0.8rem',
              fontFamily: 'JetBrains Mono, monospace'
            }}>
              {user?.username.substring(0, 2).toUpperCase()}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                {user?.username.toUpperCase()}
              </span>
              <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
                FASTAPI_PORT: {fastapiPort}
              </span>
            </div>
          </div>

          <button
            onClick={logout}
            className="btn"
            style={{
              padding: '6px',
              width: '100%',
              fontSize: '0.75rem',
              justifyContent: 'center',
              background: 'transparent',
              borderColor: 'var(--danger)',
              color: 'var(--danger)'
            }}
          >
            <LogOut size={12} /> LOG OUT
          </button>
        </div>
      </aside>

      {/* CORE WORKSPACE PANEL */}
      <main style={{
        padding: '24px 32px 32px 32px',
        maxHeight: '100vh',
        overflowY: 'auto'
      }}>
        {currentTab === 'tokens' ? (
          <TokenManager token={token!} />
        ) : currentTab === 'charts' ? (
          <ChartBrowser fastapiBaseUrl={fastapiBaseUrl} />
        ) : selectedPortfolio ? (
          
          /* Split view for selected portfolio details + trading desk */
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 340px',
            gap: '24px',
            alignItems: 'start'
          }}>
            <PortfolioDetail 
              portfolio={selectedPortfolio} 
              token={token!} 
              fastapiBaseUrl={fastapiBaseUrl}
              onRefreshList={fetchPortfolios}
            />
            <TradingTerminal 
              portfolioId={selectedPortfolio.id} 
              token={token!} 
              fastapiBaseUrl={fastapiBaseUrl}
              onOrderPlaced={fetchPortfolios}
            />
          </div>
          
        ) : (
          
          /* Welcome View asking user to select or create a portfolio */
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: 'calc(100vh - 60px)'
          }}>
            <div className="glass-panel" style={{
              padding: '40px',
              textAlign: 'center',
              maxWidth: '500px',
            }}>
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '48px',
                height: '48px',
                background: 'var(--panel-hover)',
                color: 'var(--text-primary)',
                border: '1px solid var(--panel-border)',
                marginBottom: '16px'
              }}>
                <Terminal size={24} />
              </div>
              <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace', marginBottom: '8px' }}>
                MATCHING DESK OFFLINE
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', fontFamily: 'JetBrains Mono, monospace', lineHeight: 1.6, marginBottom: '20px' }}>
                Select an active portfolio from the sidebar catalog to examine position limits and transmit strategies. If no portfolios are created yet, spin one up to allocate mock capital.
              </p>
              <button onClick={() => setIsModalOpen(true)} className="btn btn-primary" style={{ padding: '10px 20px' }}>
                <Plus size={14} /> NEW TRADING PORTFOLIO
              </button>
            </div>
          </div>
          
        )}
      </main>

      {/* CREATE PORTFOLIO GLASS MODAL */}
      {isModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          background: 'rgba(0, 0, 0, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100
        }}>
          <div className="glass-panel" style={{
            width: '100%',
            maxWidth: '400px',
            padding: '24px',
            position: 'relative',
            background: 'var(--panel-bg)',
            border: '1px solid var(--text-primary)'
          }}>
            <button 
              onClick={() => setIsModalOpen(false)}
              style={{
                position: 'absolute',
                top: '12px',
                right: '12px',
                background: 'none',
                border: 'none',
                color: 'var(--text-secondary)',
                cursor: 'pointer'
              }}
            >
              <X size={16} />
            </button>

            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', marginBottom: '16px' }}>
              INITIALIZE PORTFOLIO
            </h3>

            <form onSubmit={handleCreatePortfolio} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div className="form-group">
                <label className="form-label">PORTFOLIO NAME</label>
                <input
                  type="text"
                  required
                  className="form-input"
                  placeholder="e.g. DAYTRADING_BOT"
                  value={newPortName}
                  onChange={(e) => setNewPortName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">STRATEGY DESCRIPTION</label>
                <textarea
                  className="form-input"
                  placeholder="Strategy description..."
                  style={{ minHeight: '60px', resize: 'none' }}
                  value={newPortDesc}
                  onChange={(e) => setNewPortDesc(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">CAPITAL ALLOCATION ($)</label>
                <input
                  type="number"
                  required
                  className="form-input"
                  placeholder="100000"
                  value={newPortCash}
                  onChange={(e) => setNewPortCash(e.target.value)}
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%', padding: '10px', marginTop: '6px' }}
                disabled={isCreating}
              >
                {isCreating ? 'ALLOCATING...' : 'ALLOCATE CAPITAL & DEPLOY'}
              </button>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
