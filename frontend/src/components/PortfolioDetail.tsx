import React, { useState, useEffect } from 'react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { DollarSign, ArrowUpRight, ArrowDownRight, RefreshCw, X, ShieldAlert, Award, Edit2, Check, CornerDownRight, Briefcase, Clock, History, TrendingUp } from 'lucide-react';
import { CoinIcon } from './CoinIcon';
import { getHistory, cancelOrder, closePosition, updatePosition } from '../api/api';
import { usePortfolioWs } from '../hooks/useWs';
import { useToast } from '../hooks/useToast';

interface Position {
  position_id: number;
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  target: number | null;
  stoploss: number | null;
}

interface TradeRecord {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  exit_price: number;
  realized_pnl: number;
  exit_reason: string;
  opened_at: string;
  closed_at: string;
}

interface Portfolio {
  id: number;
  name: string;
  description: string;
  available_cash: number;
  invested_cash: number;
}

interface PortfolioDetailProps {
  portfolio: Portfolio;
  onRefresh: () => void;
}

type TabKey = 'positions' | 'orders' | 'history' | 'pnl';

const TABS: { key: TabKey; label: string; icon: React.ReactNode }[] = [
  { key: 'positions', label: 'POSITIONS', icon: <Briefcase size={13} /> },
  { key: 'orders', label: 'ORDERS', icon: <Clock size={13} /> },
  { key: 'history', label: 'HISTORY', icon: <History size={13} /> },
  { key: 'pnl', label: 'P&L', icon: <TrendingUp size={13} /> },
];

export const PortfolioDetail: React.FC<PortfolioDetailProps> = ({ portfolio, onRefresh }) => {
  const wsData = usePortfolioWs(portfolio.id);
  const { addToast } = useToast();
  const [history, setHistory] = useState<TradeRecord[]>([]);
  const [chartData, setChartData] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<TabKey>('positions');

  // Inline Position Modifier
  const [editingPositionId, setEditingPositionId] = useState<number | null>(null);
  const [editStoploss, setEditStoploss] = useState<string>('');
  const [editTarget, setEditTarget] = useState<string>('');

  const pnl = wsData.pnl;
  const positions = wsData.positions || [];
  const orders = wsData.orders || [];
  const livePortfolio = wsData.portfolio || portfolio;

  const fetchHistory = async () => {
    try {
      const histData = await getHistory(portfolio.id).catch(() => ({ history: [] }));
      const records = histData.history || [];
      setHistory(records);

      let rollingPnL = 0;
      const mappedHistory = records.slice().reverse().map((item: any, idx: number) => {
        rollingPnL += item.realized_pnl;
        return { name: `T${idx + 1}`, PnL: parseFloat(rollingPnL.toFixed(2)) };
      });
      setChartData(mappedHistory.length > 0 ? mappedHistory : [{ name: 'START', PnL: 0 }]);
    } catch {}
  };

  useEffect(() => {
    fetchHistory();
  }, [portfolio.id]);

  const handleCancelOrder = async (orderId: number) => {
    try {
      await cancelOrder(orderId);
      await wsData.refresh();
      onRefresh();
      addToast('Order cancelled', 'success');
    } catch (e: any) {
      addToast(e.message || 'Failed to cancel order', 'error');
    }
  };

  const handleClosePosition = async (positionId: number) => {
    if (!window.confirm('EXIT TRADE: Close this position at market price?')) return;
    try {
      await closePosition(portfolio.id, positionId);
      await wsData.refresh();
      onRefresh();
      addToast('Position closed', 'success');
    } catch (e: any) {
      addToast(e.message || 'Failed to close position', 'error');
    }
  };

  const handleStartEditPosition = (pos: Position) => {
    setEditingPositionId(pos.position_id);
    setEditStoploss(pos.stoploss ? pos.stoploss.toString() : '');
    setEditTarget(pos.target ? pos.target.toString() : '');
  };

  const handleUpdatePosition = async (positionId: number) => {
    try {
      await updatePosition(portfolio.id, positionId, editTarget ? parseFloat(editTarget) : undefined, editStoploss ? parseFloat(editStoploss) : undefined);
      await wsData.refresh();
      setEditingPositionId(null);
      addToast('Position protection updated', 'success');
    } catch (e: any) {
      addToast(e.message || 'Failed to update position', 'error');
    }
  };

  const pendingOrders = orders.filter(o => o.status === 'PENDING');
  const realizedPnl = pnl ? pnl.realized_pnl : 0;
  const unrealizedPnl = pnl ? pnl.unrealized_pnl : 0;
  const totalPnl = realizedPnl + unrealizedPnl;
  const isPnlPositive = totalPnl >= 0;
  const winTrades = history.filter(t => t.realized_pnl > 0).length;
  const totalTrades = history.length;
  const winRate = totalTrades > 0 ? ((winTrades / totalTrades) * 100).toFixed(1) : '0.0';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Title Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {livePortfolio.name}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '4px', fontFamily: 'JetBrains Mono, monospace' }}>
            {livePortfolio.description || 'Paper trading portfolio'}
          </p>
        </div>
        <button onClick={() => { fetchHistory(); wsData.refresh(); onRefresh(); }} className="btn" style={{ padding: '6px 12px' }}>
          <RefreshCw size={14} />
          SYNC ENGINE
        </button>
      </div>

      {wsData.pnl === null && positions.length === 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '12px',
          background: 'rgba(255, 180, 0, 0.08)', border: '1px solid var(--warning)',
          padding: '12px', color: 'var(--warning)', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.8rem'
        }}>
          <ShieldAlert size={16} />
          <div><strong>[CONNECTING]:</strong> Waiting for engine connection...</div>
        </div>
      )}

      {/* Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
        <div className="glass-panel" style={{ padding: '16px', borderLeft: '1px solid var(--text-primary)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '0.72rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
            AVAILABLE CAPITAL
            <DollarSign size={12} />
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '8px', color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
            ${livePortfolio.available_cash.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px', borderLeft: '1px solid var(--text-primary)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '0.72rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
            EXPOSURE CAPITAL
            <DollarSign size={12} />
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '8px', color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
            ${livePortfolio.invested_cash.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em', marginBottom: '8px' }}>
            P&L BREAKDOWN
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.8rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>REALIZED: </span>
              <span style={{ fontWeight: 700, color: realizedPnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                ${realizedPnl.toFixed(2)}
              </span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>UNREAL: </span>
              <span style={{ fontWeight: 700, color: unrealizedPnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                ${unrealizedPnl.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{
          padding: '16px',
          borderLeft: `2px solid ${isPnlPositive ? 'var(--success)' : 'var(--danger)'}`,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '0.72rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
            TOTAL P&L
            {isPnlPositive ? <ArrowUpRight size={14} color="var(--success)" /> : <ArrowDownRight size={14} color="var(--danger)" />}
          </div>
          <div style={{
            fontSize: '1.4rem', fontWeight: 700, marginTop: '8px',
            color: isPnlPositive ? 'var(--success)' : 'var(--danger)',
            fontFamily: 'JetBrains Mono, monospace'
          }}>
            {isPnlPositive ? '+' : ''}${totalPnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>
      </div>

      {/* Tab Bar */}
      <div style={{ display: 'flex', gap: '0', borderBottom: '1px solid var(--panel-border)' }}>
        {TABS.map(tab => {
          const isActive = activeTab === tab.key;
          const count = tab.key === 'positions' ? positions.length
            : tab.key === 'orders' ? pendingOrders.length
            : tab.key === 'history' ? history.length
            : undefined;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '10px 16px',
                background: isActive ? 'var(--panel-bg)' : 'transparent',
                border: '1px solid var(--panel-border)',
                borderBottom: isActive ? '1px solid var(--panel-bg)' : '1px solid var(--panel-border)',
                marginTop: isActive ? '-1px' : '0',
                color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                fontWeight: isActive ? 700 : 500,
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '0.75rem',
                letterSpacing: '0.05em',
                cursor: 'pointer',
                transition: 'all 0.1s ease',
                zIndex: isActive ? 1 : 0,
                position: 'relative',
              }}
            >
              {tab.icon}
              {tab.label}
              {count !== undefined && (
                <span style={{
                  fontSize: '0.62rem',
                  padding: '1px 5px',
                  background: isActive ? 'var(--text-primary)' : 'var(--panel-border)',
                  color: isActive ? 'var(--bg-color)' : 'var(--text-muted)',
                  fontWeight: 700,
                }}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
        <div style={{ flex: 1, borderBottom: '1px solid var(--panel-border)' }} />
      </div>

      {/* Tab Content */}
      <div className="glass-panel" style={{ padding: '20px', minHeight: '300px', position: 'relative', zIndex: 0 }}>

        {/* POSITIONS TAB */}
        {activeTab === 'positions' && (
          <div style={{ overflowX: 'auto' }}>
            <h3 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
              ACTIVE RISK EXPOSURE ({positions.length} OPEN)
            </h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr>
                  <th>SYMBOL</th>
                  <th>SIDE</th>
                  <th>QUANTITY</th>
                  <th>ENTRY</th>
                  <th>CURRENT</th>
                  <th>SL / TP</th>
                  <th>UNREALIZED P&L</th>
                  <th style={{ textAlign: 'right' }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {positions.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem' }}>
                      [NO ACTIVE RISK EXPOSURES]
                    </td>
                  </tr>
                ) : (
                  positions.map((pos) => {
                    const isPosPnlPositive = pos.unrealized_pnl >= 0;
                    const isEditing = editingPositionId === pos.position_id;
                    return (
                      <React.Fragment key={pos.position_id}>
                        <tr style={{ borderBottom: '1px solid var(--panel-border)' }}>
                          <td style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                              <CoinIcon symbol={pos.symbol} style={{ width: '16px', height: '16px' }} />
                              <span>{pos.symbol}</span>
                            </span>
                          </td>
                          <td><span className={`badge ${pos.side === 'BUY' ? 'badge-buy' : 'badge-sell'}`}>{pos.side}</span></td>
                          <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{pos.quantity}</td>
                          <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>${pos.entry_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                          <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>${pos.current_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                          <td style={{ fontSize: '0.75rem', fontFamily: 'JetBrains Mono, monospace' }}>
                            <span>SL: {pos.stoploss ? `$${pos.stoploss.toFixed(2)}` : 'NONE'}</span>
                            <span style={{ color: 'var(--text-muted)' }}> | </span>
                            <span>TP: {pos.target ? `$${pos.target.toFixed(2)}` : 'NONE'}</span>
                          </td>
                          <td style={{ fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: isPosPnlPositive ? 'var(--success)' : 'var(--danger)' }}>
                            {isPosPnlPositive ? '+' : ''}${pos.unrealized_pnl.toFixed(2)}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                              <button onClick={() => handleStartEditPosition(pos)} className="btn" style={{ padding: '4px 8px', fontSize: '0.7rem' }}>
                                <Edit2 size={12} /> EDIT
                              </button>
                              <button onClick={() => handleClosePosition(pos.position_id)} className="btn btn-danger" style={{ padding: '4px 8px', fontSize: '0.7rem' }}>
                                EXIT
                              </button>
                            </div>
                          </td>
                        </tr>
                        {isEditing && (
                          <tr>
                            <td colSpan={8} style={{ background: 'var(--panel-hover)', borderBottom: '1px solid var(--panel-border)' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '8px 12px' }}>
                                <CornerDownRight size={14} style={{ color: 'var(--text-muted)' }} />
                                <span style={{ fontSize: '0.72rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-secondary)' }}>
                                  MODIFY {pos.symbol}:
                                </span>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <label style={{ fontSize: '0.65rem', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-muted)' }}>SL</label>
                                  <input type="number" step="any" className="form-input" style={{ width: '100px', padding: '4px 8px', fontSize: '0.75rem' }}
                                    value={editStoploss} onChange={(e) => setEditStoploss(e.target.value)} placeholder="NONE" />
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <label style={{ fontSize: '0.65rem', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-muted)' }}>TP</label>
                                  <input type="number" step="any" className="form-input" style={{ width: '100px', padding: '4px 8px', fontSize: '0.75rem' }}
                                    value={editTarget} onChange={(e) => setEditTarget(e.target.value)} placeholder="NONE" />
                                </div>
                                <button onClick={() => handleUpdatePosition(pos.position_id)} className="btn btn-primary" style={{ padding: '4px 10px', fontSize: '0.7rem' }}>
                                  <Check size={12} /> SAVE
                                </button>
                                <button onClick={() => setEditingPositionId(null)} className="btn" style={{ padding: '4px 10px', fontSize: '0.7rem' }}>
                                  CANCEL
                                </button>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* ORDERS TAB */}
        {activeTab === 'orders' && (
          <div style={{ overflowX: 'auto' }}>
            <h3 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
              PENDING LIMIT ORDERS ({pendingOrders.length})
            </h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr>
                  <th>SYMBOL</th>
                  <th>SIDE</th>
                  <th>QUANTITY</th>
                  <th>LIMIT PRICE</th>
                  <th>TARGET</th>
                  <th>STOPLOSS</th>
                  <th>CREATED</th>
                  <th style={{ textAlign: 'right' }}>CANCEL</th>
                </tr>
              </thead>
              <tbody>
                {pendingOrders.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem' }}>
                      [NO PENDING LIMIT ORDERS]
                    </td>
                  </tr>
                ) : (
                  pendingOrders.map((order) => (
                    <tr key={order.order_id} style={{ borderBottom: '1px solid var(--panel-border)' }}>
                      <td style={{ fontWeight: 700 }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                          <CoinIcon symbol={order.symbol} style={{ width: '16px', height: '16px' }} />
                          <span>{order.symbol}</span>
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${order.side === 'BUY' ? 'badge-buy' : 'badge-sell'}`}>
                          {order.side}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{order.quantity}</td>
                      <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{order.limit_price ? `$${order.limit_price.toLocaleString()}` : 'MKT'}</td>
                      <td style={{ fontFamily: 'JetBrains Mono, monospace', color: order.target ? 'var(--success)' : 'var(--text-muted)' }}>
                        {order.target ? `$${order.target.toLocaleString()}` : '--'}
                      </td>
                      <td style={{ fontFamily: 'JetBrains Mono, monospace', color: order.stoploss ? 'var(--danger)' : 'var(--text-muted)' }}>
                        {order.stoploss ? `$${order.stoploss.toLocaleString()}` : '--'}
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.7rem', fontFamily: 'JetBrains Mono, monospace' }}>
                        {order.created_at ? new Date(order.created_at).toLocaleString() : '-'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button onClick={() => handleCancelOrder(order.order_id)} className="btn btn-danger" style={{ padding: '4px 8px', fontSize: '0.7rem' }}>
                          <X size={12} /> CANCEL
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* HISTORY TAB */}
        {activeTab === 'history' && (
          <div style={{ overflowX: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
                COMPLETED TRADES ({history.length})
              </h3>
              <div style={{ display: 'flex', gap: '16px', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.72rem' }}>
                <span>
                  <span style={{ color: 'var(--text-muted)' }}>WIN RATE: </span>
                  <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{winRate}%</span>
                </span>
                <span>
                  <span style={{ color: 'var(--text-muted)' }}>WINS: </span>
                  <span style={{ fontWeight: 700, color: 'var(--success)' }}>{winTrades}</span>
                </span>
                <span>
                  <span style={{ color: 'var(--text-muted)' }}>LOSSES: </span>
                  <span style={{ fontWeight: 700, color: 'var(--danger)' }}>{totalTrades - winTrades}</span>
                </span>
              </div>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr>
                  <th>SYMBOL</th>
                  <th>SIDE</th>
                  <th>QUANTITY</th>
                  <th>ENTRY</th>
                  <th>EXIT</th>
                  <th>P&L</th>
                  <th>REASON</th>
                  <th style={{ textAlign: 'right' }}>DATE</th>
                </tr>
              </thead>
              <tbody>
                {history.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem' }}>
                      [NO COMPLETED TRADES YET]
                    </td>
                  </tr>
                ) : (
                  history.map((record: any, idx: number) => {
                    const isPositive = record.realized_pnl >= 0;
                    return (
                      <tr key={idx} style={{ borderBottom: '1px solid var(--panel-border)' }}>
                        <td style={{ fontWeight: 700 }}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                            <CoinIcon symbol={record.symbol} style={{ width: '16px', height: '16px' }} />
                            <span>{record.symbol}</span>
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${record.side === 'BUY' ? 'badge-buy' : 'badge-sell'}`}>
                            {record.side}
                          </span>
                        </td>
                        <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{record.quantity}</td>
                        <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>${record.entry_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                        <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>${record.exit_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                        <td style={{ fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: isPositive ? 'var(--success)' : 'var(--danger)' }}>
                          {isPositive ? '+' : ''}${record.realized_pnl.toFixed(2)}
                        </td>
                        <td style={{ color: 'var(--text-secondary)', fontSize: '0.7rem', fontFamily: 'JetBrains Mono, monospace' }}>
                          {(record.exit_reason || '').toUpperCase()}
                        </td>
                        <td style={{ textAlign: 'right', color: 'var(--text-muted)', fontSize: '0.68rem', fontFamily: 'JetBrains Mono, monospace' }}>
                          {record.closed_at ? new Date(record.closed_at).toLocaleString() : '-'}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* P&L TAB */}
        {activeTab === 'pnl' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* PnL Summary Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
              <div style={{ padding: '12px', background: 'var(--bg-color)', border: '1px solid var(--panel-border)' }}>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em', marginBottom: '6px' }}>
                  REALIZED P&L
                </div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: realizedPnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                  {realizedPnl >= 0 ? '+' : ''}${realizedPnl.toFixed(2)}
                </div>
              </div>
              <div style={{ padding: '12px', background: 'var(--bg-color)', border: '1px solid var(--panel-border)' }}>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em', marginBottom: '6px' }}>
                  UNREALIZED P&L
                </div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: unrealizedPnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                  {unrealizedPnl >= 0 ? '+' : ''}${unrealizedPnl.toFixed(2)}
                </div>
              </div>
              <div style={{ padding: '12px', background: 'var(--bg-color)', border: '1px solid var(--panel-border)' }}>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em', marginBottom: '6px' }}>
                  TOTAL P&L
                </div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: totalPnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                  {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
                </div>
              </div>
              <div style={{ padding: '12px', background: 'var(--bg-color)', border: '1px solid var(--panel-border)' }}>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em', marginBottom: '6px' }}>
                  WIN RATE
                </div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-primary)' }}>
                  {winRate}%
                </div>
                <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', marginTop: '4px' }}>
                  {winTrades}W / {totalTrades - winTrades}L
                </div>
              </div>
            </div>

            {/* Cumulative P&L Curve */}
            <div>
              <h3 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '12px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
                <Award size={14} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
                CUMULATIVE REALIZED P&L
              </h3>
              <div style={{ width: '100%', height: '200px' }}>
                <ResponsiveContainer>
                  <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                    <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={10} tickLine={false} style={{ fontFamily: 'JetBrains Mono, monospace' }} />
                    <YAxis stroke="var(--text-muted)" fontSize={10} tickLine={false} style={{ fontFamily: 'JetBrains Mono, monospace' }} />
                    <Tooltip
                      contentStyle={{ background: 'var(--panel-bg)', borderColor: 'var(--panel-border)', color: 'var(--text-primary)', fontSize: '11px', fontFamily: 'JetBrains Mono, monospace' }}
                      cursor={{ stroke: 'var(--panel-border)' }}
                    />
                    <Area type="monotone" dataKey="PnL" stroke="var(--text-primary)" strokeWidth={1} fill="rgba(148, 163, 184, 0.05)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Per-Trade P&L Bar Chart */}
            {history.length > 0 && (
              <div>
                <h3 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '12px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
                  PER-TRADE P&L
                </h3>
                <div style={{ width: '100%', height: '160px' }}>
                  <ResponsiveContainer>
                    <BarChart data={history.slice().reverse().map((t: any, i: number) => ({
                      name: `${t.symbol}#${i + 1}`,
                      PnL: t.realized_pnl,
                    }))} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                      <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={9} tickLine={false} style={{ fontFamily: 'JetBrains Mono, monospace' }} />
                      <YAxis stroke="var(--text-muted)" fontSize={10} tickLine={false} style={{ fontFamily: 'JetBrains Mono, monospace' }} />
                      <Tooltip
                        contentStyle={{ background: 'var(--panel-bg)', borderColor: 'var(--panel-border)', color: 'var(--text-primary)', fontSize: '11px', fontFamily: 'JetBrains Mono, monospace' }}
                        cursor={{ fill: 'var(--panel-hover)' }}
                      />
                      <Bar dataKey="PnL" radius={[0, 0, 0, 0]}>
                        {history.slice().reverse().map((entry: any, index: number) => (
                          <Cell key={index} fill={entry.realized_pnl >= 0 ? 'var(--success)' : 'var(--danger)'} fillOpacity={0.6} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <style>{`
        .spin-anim { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};
