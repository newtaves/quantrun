import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { getAgentEquity, getAgentLeaderboard } from '../api/api';

type Agent = {
  agent_id: number; agent_name: string; strategy: string; total_pnl: number; equity: number;
  trade_count: number; win_rate: number; sharpe: number; max_loss: number; max_profit: number; max_drawdown: number;
};

export const AgentLeaderboard: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [chartData, setChartData] = useState<Record<string, string | number>[]>([]);

  useEffect(() => {
    const load = async () => {
      const data = await getAgentLeaderboard();
      const rows: Agent[] = data.agents || [];
      setAgents(rows);
      const series = await Promise.all(rows.map(async agent => ({ agent, data: (await getAgentEquity(agent.agent_id)).series || [] })));
      const merged = new Map<string, Record<string, string | number>>();
      for (const { agent, data: points } of series) for (const point of points) {
        const row = merged.get(point.timestamp) || { timestamp: point.timestamp };
        row[agent.agent_name] = point.pnl;
        merged.set(point.timestamp, row);
      }
      setChartData([...merged.values()]);
    };
    load().catch(console.error);
  }, []);

  return <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
    <div><h2 style={{ color: 'var(--text-primary)', fontSize: '1.4rem' }}>AGENT LEADERBOARD</h2><p style={{ color: 'var(--text-secondary)', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem' }}>Hourly equity, risk, and trade performance</p></div>
    <div className="glass-panel" style={{ padding: '16px', height: 280 }}><div style={{ color: 'var(--text-muted)', fontSize: '0.7rem', fontFamily: 'JetBrains Mono, monospace', marginBottom: '8px' }}>CUMULATIVE P&amp;L</div>
      <ResponsiveContainer width="100%" height="100%"><LineChart data={chartData}><XAxis dataKey="timestamp" hide /><YAxis /><Tooltip /><>{agents.map((agent, index) => <Line key={agent.agent_id} type="monotone" dataKey={agent.agent_name} stroke={['#00f2fe', '#a78bfa', '#34d399', '#fb7185'][index % 4]} dot={false} />)}</></LineChart></ResponsiveContainer>
    </div>
    <div className="glass-panel" style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.72rem' }}><thead><tr>{['AGENT', 'PNL', 'TRADES', 'WIN %', 'SHARPE', 'MAX LOSS', 'MAX PROFIT', 'DRAWDOWN'].map(label => <th key={label} style={{ padding: '12px', textAlign: 'left', color: 'var(--text-muted)' }}>{label}</th>)}</tr></thead><tbody>{agents.map(agent => <tr key={agent.agent_id}><td style={{ padding: '12px', color: 'var(--text-primary)' }}>{agent.agent_name}<br /><span style={{ color: 'var(--text-muted)' }}>{agent.strategy}</span></td><td style={{ padding: '12px', color: agent.total_pnl >= 0 ? '#34d399' : '#fb7185' }}>${agent.total_pnl.toFixed(2)}</td><td style={{ padding: '12px' }}>{agent.trade_count}</td><td style={{ padding: '12px' }}>{agent.win_rate.toFixed(1)}%</td><td style={{ padding: '12px' }}>{agent.sharpe.toFixed(2)}</td><td style={{ padding: '12px', color: '#fb7185' }}>${agent.max_loss.toFixed(2)}</td><td style={{ padding: '12px', color: '#34d399' }}>${agent.max_profit.toFixed(2)}</td><td style={{ padding: '12px' }}>{agent.max_drawdown.toFixed(2)}%</td></tr>)}</tbody></table>{agents.length === 0 && <p style={{ padding: '24px', color: 'var(--text-muted)' }}>No active agents yet. Create one with POST /agents.</p>}</div>
  </div>;
};
