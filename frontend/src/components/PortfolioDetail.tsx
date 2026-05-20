import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { DollarSign, ArrowUpRight, ArrowDownRight, RefreshCw, X, ShieldAlert, Award, Edit2, Check, CornerDownRight } from 'lucide-react';
import { CoinIcon } from './CoinIcon';

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

interface Order {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  limit_price: number | null;
  status: string;
  target: number | null;
  stoploss: number | null;
  created_at: string;
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
  target: number | null;
  stoploss: number | null;
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
  token: string;
  fastapiBaseUrl: string;
  onRefreshList: () => void;
}

export const PortfolioDetail: React.FC<PortfolioDetailProps> = ({ portfolio, token, fastapiBaseUrl, onRefreshList }) => {
  const [summary, setSummary] = useState<any>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [history, setHistory] = useState<TradeRecord[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<any[]>([]);

  // Inline Position Modifier States
  const [editingPositionId, setEditingPositionId] = useState<number | null>(null);
  const [editStoploss, setEditStoploss] = useState<string>('');
  const [editTarget, setEditTarget] = useState<string>('');
  const [isUpdatingPos, setIsUpdatingPos] = useState<boolean>(false);

  const fetchDetails = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      
      // 1. Fetch Summary
      const summaryResp = await fetch(`${fastapiBaseUrl}/portfolio/${portfolio.id}/summary`, { headers });
      if (!summaryResp.ok) throw new Error('Failed to fetch portfolio summary');
      const summaryData = await summaryResp.json();
      setSummary(summaryData);

      // 2. Fetch Positions
      const posResp = await fetch(`${fastapiBaseUrl}/portfolio/${portfolio.id}/positions`, { headers });
      if (posResp.ok) {
        const posData = await posResp.json();
        setPositions(posData.positions || []);
      }

      // 3. Fetch Orders
      const orderResp = await fetch(`${fastapiBaseUrl}/portfolio/${portfolio.id}/orders`, { headers });
      if (orderResp.ok) {
        const orderData = await orderResp.json();
        setOrders(orderData.orders || []);
      }

      // 4. Fetch Trade History (Past Trades)
      const histResp = await fetch(`${fastapiBaseUrl}/portfolio/${portfolio.id}/history`, { headers });
      if (histResp.ok) {
        const histData = await histResp.json();
        const records = histData.history || [];
        setHistory(records);

        // Generate Flat Chart Data based on realized PnL over time
        let rollingPnL = 0;
        const mappedHistory = records
          .slice()
          .reverse()
          .map((item: any, idx: number) => {
            rollingPnL += item.realized_pnl;
            return {
              name: `T${idx + 1}`,
              PnL: parseFloat(rollingPnL.toFixed(2)),
              raw: item.realized_pnl
            };
          });

        setChartData(mappedHistory.length > 0 ? mappedHistory : [{ name: 'START', PnL: 0 }]);
      }
    } catch (e: any) {
      console.error(e);
      setError(e.message || 'FastAPI Server unreachable');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
    const interval = setInterval(fetchDetails, 3000);
    return () => clearInterval(interval);
  }, [portfolio.id, fastapiBaseUrl]);

  useEffect(() => {
    setSummary((prev: any) => {
      if (!prev) return prev;
      return {
        ...prev,
        available_cash: portfolio.available_cash,
        invested_cash: portfolio.invested_cash,
      };
    });
  }, [portfolio.available_cash, portfolio.invested_cash]);
  const handleCancelOrder = async (orderId: number) => {
    try {
      const resp = await fetch(`${fastapiBaseUrl}/order/${orderId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (resp.ok) {
        fetchDetails();
        onRefreshList();
      } else {
        const data = await resp.json();
        alert(data.detail || 'Failed to cancel order');
      }
    } catch (e) {
      alert('Error connecting to FastAPI');
    }
  };

  // Exit Trade (Manually close open position at market price)
  const handleClosePosition = async (positionId: number) => {
    if (!window.confirm(`EXIT TRADE: Are you sure you want to close this position immediately at market price?`)) {
      return;
    }
    try {
      const resp = await fetch(`${fastapiBaseUrl}/portfolio/${portfolio.id}/positions/${positionId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (resp.ok) {
        fetchDetails();
        onRefreshList();
      } else {
        const data = await resp.json();
        alert(data.detail || 'Failed to close position');
      }
    } catch (e) {
      alert('Error connecting to FastAPI');
    }
  };

  // Modify Position Target and Stoploss
  const handleStartEditPosition = (pos: Position) => {
    setEditingPositionId(pos.position_id);
    setEditStoploss(pos.stoploss ? pos.stoploss.toString() : '');
    setEditTarget(pos.target ? pos.target.toString() : '');
  };

  const handleUpdatePosition = async (positionId: number) => {
    setIsUpdatingPos(true);
    try {
      const url = new URL(`${fastapiBaseUrl}/portfolio/${portfolio.id}/positions/${positionId}`);
      if (editTarget.trim()) {
        url.searchParams.append('target', editTarget.trim());
      }
      if (editStoploss.trim()) {
        url.searchParams.append('stoploss', editStoploss.trim());
      }

      const resp = await fetch(url.toString(), {
        method: 'PUT',
        headers: { 
          'Authorization': `Bearer ${token}`
        }
      });

      if (resp.ok) {
        setEditingPositionId(null);
        fetchDetails();
      } else {
        const data = await resp.json();
        alert(data.detail || 'Failed to update position risk parameters.');
      }
    } catch (e) {
      alert('Error connecting to matching engine to update position.');
    } finally {
      setIsUpdatingPos(false);
    }
  };

  const pendingOrders = orders.filter(o => o.status === 'PENDING');
  const pnlVal = summary ? summary.total_pnl : 0;
  const isPnlPositive = pnlVal >= 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Portfolio Title Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {portfolio.name}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '4px', fontFamily: 'JetBrains Mono, monospace' }}>
            {portfolio.description}
          </p>
        </div>
        <button onClick={fetchDetails} className="btn" style={{ padding: '6px 12px' }}>
          <RefreshCw size={14} className={isLoading ? 'spin-anim' : ''} />
          SYNC ENGINE
        </button>
      </div>

      {error && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          background: 'rgba(255, 56, 56, 0.08)',
          border: '1px solid var(--danger)',
          padding: '12px',
          color: 'var(--danger)',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '0.8rem'
        }}>
          <ShieldAlert size={16} />
          <div>
            <strong>[ENGINE_CONNECTION_FAILURE]:</strong> The matching engine is currently offline. Restart uvicorn on port 8001.
          </div>
        </div>
      )}

      {/* Metric Cards Row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '12px'
      }}>
        {/* Available Cash */}
        <div className="glass-panel" style={{ padding: '16px', borderLeft: '1px solid var(--text-primary)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '0.72rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
            AVAILABLE CAPITAL
            <DollarSign size={12} />
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '8px', color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
            ${summary ? summary.available_cash.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : portfolio.available_cash.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>

        {/* Invested Capital */}
        <div className="glass-panel" style={{ padding: '16px', borderLeft: '1px solid var(--text-primary)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '0.72rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
            EXPOSURE CAPITAL
            <DollarSign size={12} />
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '8px', color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
            ${summary ? summary.invested_cash.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : portfolio.invested_cash.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>

        {/* Realized / Unrealized */}
        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em', marginBottom: '8px' }}>
            P&L BREAKDOWN (REAL/UNREAL)
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.8rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>REAL: </span>
              <span style={{ fontWeight: 700, color: summary && summary.realized_pnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                ${summary ? summary.realized_pnl.toFixed(2) : '0.00'}
              </span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>UNREAL: </span>
              <span style={{ fontWeight: 700, color: summary && summary.unrealized_pnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                ${summary ? summary.unrealized_pnl.toFixed(2) : '0.00'}
              </span>
            </div>
          </div>
        </div>

        {/* Total Net Profit / Loss */}
        <div className="glass-panel" style={{
          padding: '16px',
          borderLeft: `2px solid ${isPnlPositive ? 'var(--success)' : 'var(--danger)'}`,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '0.72rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
            TOTAL P&L METRIC
            {isPnlPositive ? <ArrowUpRight size={14} color="var(--success)" /> : <ArrowDownRight size={14} color="var(--danger)" />}
          </div>
          <div style={{
            fontSize: '1.4rem',
            fontWeight: 700,
            marginTop: '8px',
            color: isPnlPositive ? 'var(--success)' : 'var(--danger)',
            fontFamily: 'JetBrains Mono, monospace'
          }}>
            {isPnlPositive ? '+' : ''}${pnlVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>
      </div>

      {/* Chart Section */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 style={{ fontSize: '0.8rem', color: 'var(--text-primary)', marginBottom: '12px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
          <Award size={14} /> PORTFOLIO PERFORMANCE CURVE (REALIZED P&L)
        </h3>
        <div style={{ width: '100%', height: '180px' }}>
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

      {/* Open Positions Grid */}
      <div className="glass-panel" style={{ padding: '20px', overflow: 'hidden' }}>
        <h3 style={{ fontSize: '0.85rem', color: 'var(--text-primary)', marginBottom: '12px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
          ACTIVE RISK EXPOSURE ({positions.length} OPEN POSITIONS)
        </h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr>
                <th>SYMBOL</th>
                <th>SIDE</th>
                <th>QUANTITY</th>
                <th>ENTRY</th>
                <th>CURRENT</th>
                <th>LIMIT TRIGGER LEVEL (SL/TP)</th>
                <th>UNREALIZED P&L</th>
                <th style={{ textAlign: 'right' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {positions.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem' }}>
                    [NO ACTIVE RISK EXPOSURES RECORDED]
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
                        <td>
                          <span className={`badge ${pos.side === 'BUY' ? 'badge-buy' : 'badge-sell'}`}>{pos.side}</span>
                        </td>
                        <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{pos.quantity}</td>
                        <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>${pos.entry_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>${pos.current_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', fontFamily: 'JetBrains Mono, monospace' }}>
                            <span>SL: {pos.stoploss ? `$${pos.stoploss.toFixed(2)}` : 'NONE'}</span>
                            <span style={{ color: 'var(--text-muted)' }}>|</span>
                            <span>TP: {pos.target ? `$${pos.target.toFixed(2)}` : 'NONE'}</span>
                          </div>
                        </td>
                        <td style={{
                          fontWeight: 700,
                          fontFamily: 'JetBrains Mono, monospace',
                          color: isPosPnlPositive ? 'var(--success)' : 'var(--danger)'
                        }}>
                          {isPosPnlPositive ? '+' : ''}${pos.unrealized_pnl.toFixed(2)}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                            <button 
                              onClick={() => handleStartEditPosition(pos)} 
                              className="btn" 
                              style={{ padding: '4px 8px', fontSize: '0.7rem' }}
                            >
                              <Edit2 size={12} />
                              EDIT SL/TP
                            </button>
                            <button 
                              onClick={() => handleClosePosition(pos.position_id)} 
                              className="btn btn-danger" 
                              style={{ padding: '4px 8px', fontSize: '0.7rem' }}
                            >
                              EXIT
                            </button>
                          </div>
                        </td>
                      </tr>

                      {/* Inline Stoploss/Target Editor */}
                      {isEditing && (
                        <tr>
                          <td colSpan={8} style={{ background: 'var(--panel-hover)', borderBottom: '1px solid var(--panel-border)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '8px 12px' }}>
                              <CornerDownRight size={14} style={{ color: 'var(--text-muted)' }} />
                              <span style={{ fontSize: '0.72rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-secondary)' }}>
                                MODIFY LIMIT CHECKS FOR {pos.symbol}:
                              </span>
                              
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <label style={{ fontSize: '0.65rem', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-muted)' }}>SL TRIGGER ($)</label>
                                <input
                                  type="number"
                                  step="any"
                                  className="form-input"
                                  style={{ width: '100px', padding: '4px 8px', fontSize: '0.75rem' }}
                                  value={editStoploss}
                                  onChange={(e) => setEditStoploss(e.target.value)}
                                  placeholder="NONE"
                                />
                              </div>

                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <label style={{ fontSize: '0.65rem', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-muted)' }}>TP TARGET ($)</label>
                                <input
                                  type="number"
                                  step="any"
                                  className="form-input"
                                  style={{ width: '100px', padding: '4px 8px', fontSize: '0.75rem' }}
                                  value={editTarget}
                                  onChange={(e) => setEditTarget(e.target.value)}
                                  placeholder="NONE"
                                />
                              </div>

                              <button 
                                onClick={() => handleUpdatePosition(pos.position_id)} 
                                disabled={isUpdatingPos}
                                className="btn btn-primary" 
                                style={{ padding: '4px 10px', fontSize: '0.7rem' }}
                              >
                                <Check size={12} />
                                {isUpdatingPos ? 'SAVING...' : 'SAVE'}
                              </button>
                              <button 
                                onClick={() => setEditingPositionId(null)} 
                                className="btn" 
                                style={{ padding: '4px 10px', fontSize: '0.7rem' }}
                              >
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
      </div>

      {/* Two Column Layout for Pending and Trade History */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
        
        {/* Pending Orders Column */}
        <div className="glass-panel" style={{ padding: '16px' }}>
          <h3 style={{ fontSize: '0.8rem', color: 'var(--text-primary)', marginBottom: '12px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
            PENDING LIMIT ORDERS ({pendingOrders.length})
          </h3>
          <div style={{ overflowX: 'auto', maxHeight: '200px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr>
                  <th>SYMBOL</th>
                  <th>SIDE</th>
                  <th>QTY</th>
                  <th>LIMIT</th>
                  <th style={{ textAlign: 'right' }}>CANCEL</th>
                </tr>
              </thead>
              <tbody>
                {pendingOrders.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.72rem' }}>
                      [NO ACTIVE PENDING LIMIT TASKS]
                    </td>
                  </tr>
                ) : (
                  pendingOrders.map((order) => (
                    <tr key={order.id} style={{ borderBottom: '1px solid var(--panel-border)' }}>
                      <td style={{ fontWeight: 700 }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                          <CoinIcon symbol={order.symbol} style={{ width: '16px', height: '16px' }} />
                          <span>{order.symbol}</span>
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${order.side === 'BUY' ? 'badge-buy' : 'badge-sell'}`} style={{ padding: '1px 4px', fontSize: '0.62rem' }}>
                          {order.side}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{order.quantity}</td>
                      <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{order.limit_price ? `$${order.limit_price.toLocaleString()}` : 'MKT'}</td>
                      <td style={{ textAlign: 'right' }}>
                        <button onClick={() => handleCancelOrder(order.id)} style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', padding: 0 }}>
                          <X size={14} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* PAST TRADES Column (Using /portfolio/{portfolio_id}/history) */}
        <div className="glass-panel" style={{ padding: '16px' }}>
          <h3 style={{ fontSize: '0.8rem', color: 'var(--text-primary)', marginBottom: '12px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
            PAST TRADES (COMPLETED / CLOSED)
          </h3>
          <div style={{ overflowX: 'auto', maxHeight: '200px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr>
                  <th>SYMBOL</th>
                  <th>SIDE</th>
                  <th>QTY</th>
                  <th>PNL</th>
                  <th>REASON</th>
                  <th style={{ textAlign: 'right' }}>DATE</th>
                </tr>
              </thead>
              <tbody>
                {history.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.72rem' }}>
                      [NO COMPLETED TRADES REGISTERED]
                    </td>
                  </tr>
                ) : (
                  history.slice(0, 10).map((record) => {
                    const isRecordPositive = record.realized_pnl >= 0;
                    return (
                      <tr key={record.id} style={{ borderBottom: '1px solid var(--panel-border)' }}>
                        <td style={{ fontWeight: 700 }}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                            <CoinIcon symbol={record.symbol} style={{ width: '16px', height: '16px' }} />
                            <span>{record.symbol}</span>
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${record.side === 'BUY' ? 'badge-buy' : 'badge-sell'}`} style={{ padding: '1px 4px', fontSize: '0.62rem' }}>
                            {record.side}
                          </span>
                        </td>
                        <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{record.quantity}</td>
                        <td style={{
                          fontWeight: 700,
                          fontFamily: 'JetBrains Mono, monospace',
                          color: isRecordPositive ? 'var(--success)' : 'var(--danger)'
                        }}>
                          {isRecordPositive ? '+' : ''}${record.realized_pnl.toFixed(2)}
                        </td>
                        <td style={{ color: 'var(--text-secondary)', fontSize: '0.7rem', fontFamily: 'JetBrains Mono, monospace' }}>
                          {record.exit_reason.toUpperCase()}
                        </td>
                        <td style={{ textAlign: 'right', color: 'var(--text-muted)', fontSize: '0.68rem', fontFamily: 'JetBrains Mono, monospace' }}>
                          {new Date(record.closed_at).toLocaleDateString()}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>

      <style>{`
        .spin-anim {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
