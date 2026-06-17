import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Search, TrendingUp, TrendingDown, Calendar, BarChart2, Loader2 } from 'lucide-react';
import { CoinIcon } from './CoinIcon';

interface ChartPoint {
  date: string;
  Price: number;
}

interface ChartBrowserProps {
  fastapiBaseUrl: string;
}

const CRYPTO_OPTIONS = [
  { value: 'BTCUSDT', label: 'Bitcoin (BTC)', symbol: '₿' },
  { value: 'ETHUSDT', label: 'Ethereum (ETH)', symbol: 'Ξ' },
  { value: 'SOLUSDT', label: 'Solana (SOL)', symbol: '◎' },
  { value: 'ADAUSDT', label: 'Cardano (ADA)', symbol: '₳' },
  { value: 'DOTUSDT', label: 'Polkadot (DOT)', symbol: '●' },
  { value: 'LTCUSDT', label: 'Litecoin (LTC)', symbol: 'Ł' },
  { value: 'XRPUSDT', label: 'Ripple (XRP)', symbol: '✕' },
  { value: 'DOGEUSDT', label: 'Dogecoin (DOGE)', symbol: 'Ð' },
  { value: 'BNBUSDT', label: 'BNB Coin (BNB)', symbol: '🔶' },
  { value: 'AVAXUSDT', label: 'Avalanche (AVAX)', symbol: '🔺' },
  { value: 'LINKUSDT', label: 'Chainlink (LINK)', symbol: '⬡' },
  { value: 'NEARUSDT', label: 'Near Protocol (NEAR)', symbol: 'Ⓝ' },
  { value: 'ATOMUSDT', label: 'Cosmos (ATOM)', symbol: '⚛' },
  { value: 'TRXUSDT', label: 'TRON (TRX)', symbol: '🔴' },
  { value: 'SHIBUSDT', label: 'Shiba Inu (SHIB)', symbol: '🐕' },
  { value: 'MATICUSDT', label: 'Polygon (MATIC)', symbol: '🟣' },
  { value: 'ETCUSDT', label: 'Ethereum Classic (ETC)', symbol: '🟢' },
  { value: 'FILUSDT', label: 'Filecoin (FIL)', symbol: '⨎' },
  { value: 'LDOUSDT', label: 'Lido DAO (LDO)', symbol: '💧' },
  { value: 'APTUSDT', label: 'Aptos (APT)', symbol: '▲' },
  { value: 'OPUSDT', label: 'Optimism (OP)', symbol: '🔴' },
  { value: 'ARBUSDT', label: 'Arbitrum (ARB)', symbol: '🔵' },
  { value: 'RENDERUSDT', label: 'Render (RENDER)', symbol: '⭕' },
  { value: 'INJUSDT', label: 'Injective (INJ)', symbol: '🥷' },
  { value: 'SUIUSDT', label: 'Sui Network (SUI)', symbol: '💧' },
  { value: 'TIAUSDT', label: 'Celestia (TIA)', symbol: '☄' },
  { value: 'SEIUSDT', label: 'Sei Network (SEI)', symbol: '🌊' },
  { value: 'ICPUSDT', label: 'Internet Computer (ICP)', symbol: '∞' },
  { value: 'STXUSDT', label: 'Stacks (STX)', symbol: '🪙' },
  { value: 'GRTUSDT', label: 'The Graph (GRT)', symbol: '📊' },
  { value: 'GALAUSDT', label: 'Gala Games (GALA)', symbol: '🎮' },
  { value: 'IMXUSDT', label: 'Immutable X (IMX)', symbol: '⚡' },
  { value: 'FTMUSDT', label: 'Fantom (FTM)', symbol: '👻' },
  { value: 'VETUSDT', label: 'VeChain (VET)', symbol: '🔷' }
];

const TIMEFRAME_MAP: Record<string, { interval: string; limit: number }> = {
  '1D': { interval: '1h', limit: 24 },
  '1W': { interval: '1d', limit: 7 },
  '1M': { interval: '1d', limit: 30 },
  '1Y': { interval: '1d', limit: 365 },
};

export const ChartBrowser: React.FC<ChartBrowserProps> = ({ fastapiBaseUrl }) => {
  const [selectedTicker, setSelectedTicker] = useState<string>('BTCUSDT');
  const [timeframe, setTimeframe] = useState<'1D' | '1W' | '1M' | '1Y'>('1Y');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const [chartData, setChartData] = useState<ChartPoint[]>([]);
  const [stats, setStats] = useState({ high: 0, low: 0, current: 0, changePct: 0 });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formatKlineDate = (openTime: number, tf: string) => {
    const d = new Date(openTime);
    if (tf === '1D') {
      return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false });
    }
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  const fetchKlines = async (ticker: string, tf: '1D' | '1W' | '1M' | '1Y') => {
    setIsLoading(true);
    setError(null);
    try {
      const { interval, limit } = TIMEFRAME_MAP[tf];
      const resp = await fetch(
        `${fastapiBaseUrl}/klines/${ticker}?interval=${interval}&limit=${limit}`
      );
      if (!resp.ok) {
        throw new Error(`Failed to fetch historical data for ${ticker}`);
      }
      const data = await resp.json();
      const klines = data.klines || [];

      if (klines.length === 0) {
        throw new Error(`No historical data available for ${ticker}`);
      }

      const points: ChartPoint[] = klines.map((k: any) => ({
        date: formatKlineDate(k.open_time, tf),
        Price: k.close,
      }));

      const prices = klines.map((k: any) => k.close);
      const high = Math.max(...prices);
      const low = Math.min(...prices);
      const current = prices[prices.length - 1];
      const start = prices[0];
      const changePct = ((current - start) / start) * 100;

      setChartData(points);
      setStats({ high, low, current, changePct });
    } catch (e: any) {
      setError(e.message || 'Failed to load chart data');
      setChartData([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchKlines(selectedTicker, timeframe);
  }, [selectedTicker, timeframe, fastapiBaseUrl]);

  const filteredCryptos = CRYPTO_OPTIONS.filter(opt => 
    opt.value.toUpperCase().includes(searchQuery.toUpperCase()) || 
    opt.label.toUpperCase().includes(searchQuery.toUpperCase())
  );

  // Dynamic search suggestion for custom cryptos
  const typedQuery = searchQuery.trim().toUpperCase();
  const validCustomTicker = typedQuery ? (typedQuery.endsWith('USDT') ? typedQuery : `${typedQuery}USDT`) : '';
  const showCustomOption = validCustomTicker && !CRYPTO_OPTIONS.some(o => o.value === validCustomTicker) && validCustomTicker.length >= 5;


  const getCryptoLabel = (sym: string) => {
    return CRYPTO_OPTIONS.find(c => c.value === sym)?.label || `${sym} Index`;
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '20px' }}>
      
      {/* Search and Browse Panel */}
      <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px', height: 'fit-content' }}>
        <h3 style={{ fontSize: '0.8rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
          BROWSE MARKETS
        </h3>
        
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <input
            type="text"
            className="form-input"
            style={{ paddingRight: '28px', fontSize: '0.8rem' }}
            placeholder="FILTER ASSETS..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <Search size={14} style={{ position: 'absolute', right: '10px', color: 'var(--text-muted)' }} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '350px', overflowY: 'auto' }}>
          {/* Custom suggestion row */}
          {showCustomOption && (
            <button
              onClick={() => {
                setSelectedTicker(validCustomTicker);
                setSearchQuery('');
              }}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                width: '100%',
                padding: '8px 10px',
                border: '1px dashed var(--text-primary)',
                background: 'transparent',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '0.78rem',
                fontWeight: 700
              }}
            >
              <span>⊕ CHOOSE: {validCustomTicker}</span>
            </button>
          )}

          {filteredCryptos.map((opt) => (
            <button
              key={opt.value}
              onClick={() => {
                setSelectedTicker(opt.value);
                setSearchQuery('');
              }}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                width: '100%',
                padding: '8px 10px',
                border: '1px solid ' + (selectedTicker === opt.value ? 'var(--text-primary)' : 'transparent'),
                background: selectedTicker === opt.value ? 'var(--panel-hover)' : 'transparent',
                color: selectedTicker === opt.value ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: selectedTicker === opt.value ? 700 : 500,
                textAlign: 'left',
                cursor: 'pointer',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '0.78rem'
              }}
            >
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <CoinIcon symbol={opt.value} style={{ width: '16px', height: '16px' }} />
                <span>{opt.value}</span>
              </span>
            </button>
          ))}
          
          {filteredCryptos.length === 0 && !showCustomOption && (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '12px', fontSize: '0.75rem' }}>
              NO ASSETS MATCHED
            </div>
          )}
        </div>
      </div>

      {/* Interactive Chart Workspace */}
      <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Header containing Ticker name, timeframe picker */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '1.6rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>
                {selectedTicker}
              </span>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.8rem',
                fontFamily: 'JetBrains Mono, monospace',
                fontWeight: 700,
                color: stats.changePct >= 0 ? 'var(--success)' : 'var(--danger)'
              }}>
                {stats.changePct >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                {stats.changePct >= 0 ? '+' : ''}{stats.changePct.toFixed(2)}% ({timeframe})
              </span>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '2px', fontFamily: 'JetBrains Mono, monospace', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CoinIcon symbol={selectedTicker} style={{ width: '16px', height: '16px' }} />
              <span>{getCryptoLabel(selectedTicker)} Historical Spot Index</span>
            </p>
          </div>

          {/* Timeframe Controller */}
          <div style={{ display: 'flex', background: 'var(--bg-color)', padding: '2px', border: '1px solid var(--panel-border)' }}>
            {(['1D', '1W', '1M', '1Y'] as const).map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                style={{
                  padding: '6px 12px',
                  border: 'none',
                  fontWeight: 700,
                  fontSize: '0.75rem',
                  fontFamily: 'JetBrains Mono, monospace',
                  cursor: 'pointer',
                  background: timeframe === tf ? 'var(--text-primary)' : 'transparent',
                  color: timeframe === tf ? 'var(--bg-color)' : 'var(--text-secondary)'
                }}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>

        {/* Dynamic Analytics Info Boxes */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: '12px',
          borderBottom: '1px solid var(--panel-border)',
          borderTop: '1px solid var(--panel-border)',
          padding: '12px 0'
        }}>
          <div>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'block', fontFamily: 'JetBrains Mono, monospace' }}>INDEX VALUE</span>
            <span style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-primary)' }}>
              ${stats.current.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 5 })}
            </span>
          </div>
          <div>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'block', fontFamily: 'JetBrains Mono, monospace' }}>PERIOD HIGH</span>
            <span style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: 'var(--success)' }}>
              ${stats.high.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 5 })}
            </span>
          </div>
          <div>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'block', fontFamily: 'JetBrains Mono, monospace' }}>PERIOD LOW</span>
            <span style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: 'var(--danger)' }}>
              ${stats.low.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 5 })}
            </span>
          </div>
          <div>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'block', fontFamily: 'JetBrains Mono, monospace' }}>VOLATILITY CLASS</span>
            <span style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-secondary)' }}>
              {(selectedTicker.includes('BTC') || selectedTicker.includes('ETH')) ? 'STABLE CORE' : 'ALT HIGH-BETA'}
            </span>
          </div>
        </div>

        {/* Historical Price Chart Line */}
        <div style={{ width: '100%', height: '300px', position: 'relative' }}>
          {isLoading && (
            <div style={{
              position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
              justifyContent: 'center', background: 'var(--panel-bg)', zIndex: 10
            }}>
              <Loader2 size={24} className="spin" style={{ color: 'var(--text-muted)' }} />
            </div>
          )}
          {error && !isLoading && (
            <div style={{
              height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexDirection: 'column', gap: '8px', color: 'var(--danger)',
              fontFamily: 'JetBrains Mono, monospace', fontSize: '0.8rem'
            }}>
              <span>{error}</span>
            </div>
          )}
          {!error && (
            <ResponsiveContainer>
              <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={10} tickLine={false} style={{ fontFamily: 'JetBrains Mono, monospace' }} />
                <YAxis stroke="var(--text-muted)" fontSize={10} tickLine={false} domain={['auto', 'auto']} style={{ fontFamily: 'JetBrains Mono, monospace' }} />
                <Tooltip
                  contentStyle={{ background: 'var(--panel-bg)', borderColor: 'var(--panel-border)', color: 'var(--text-primary)', fontSize: '11px', fontFamily: 'JetBrains Mono, monospace' }}
                  cursor={{ stroke: 'var(--panel-border)' }}
                />
                <Line type="monotone" dataKey="Price" stroke="var(--text-primary)" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Ticker System Logs */}
        <div style={{
          border: '1px solid var(--panel-border)',
          background: 'var(--bg-color)',
          padding: '10px 14px',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '0.72rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <div style={{ display: 'flex', gap: '8px', color: 'var(--text-muted)' }}>
            <Calendar size={12} style={{ marginTop: '1px' }} />
            <span>[DATA STREAM] Binance klines candle feed resolved: {chartData.length} candles for {selectedTicker} ({TIMEFRAME_MAP[timeframe].interval} resolution).</span>
          </div>
          <div style={{ display: 'flex', gap: '8px', color: 'var(--text-muted)' }}>
            <BarChart2 size={12} style={{ marginTop: '1px' }} />
            <span>[PRICE] Live Binance market data. Current: ${stats.current.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })} | Change: {stats.changePct >= 0 ? '+' : ''}{stats.changePct.toFixed(2)}% ({timeframe}).</span>
          </div>
        </div>

      </div>

    </div>
  );
};
