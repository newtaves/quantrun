import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Search, TrendingUp, TrendingDown, Calendar, BarChart2 } from 'lucide-react';
import { CoinIcon } from './CoinIcon';
import { getPrices } from '../api/api';

interface ChartPoint {
  date: string;
  Price: number;
}

const CRYPTO_OPTIONS = [
  { value: 'BTCUSDT', label: 'Bitcoin (BTC)' },
  { value: 'ETHUSDT', label: 'Ethereum (ETH)' },
  { value: 'SOLUSDT', label: 'Solana (SOL)' },
  { value: 'ADAUSDT', label: 'Cardano (ADA)' },
  { value: 'DOTUSDT', label: 'Polkadot (DOT)' },
  { value: 'LTCUSDT', label: 'Litecoin (LTC)' },
  { value: 'XRPUSDT', label: 'Ripple (XRP)' },
  { value: 'DOGEUSDT', label: 'Dogecoin (DOGE)' },
  { value: 'BNBUSDT', label: 'BNB Coin (BNB)' },
  { value: 'AVAXUSDT', label: 'Avalanche (AVAX)' },
  { value: 'LINKUSDT', label: 'Chainlink (LINK)' },
  { value: 'NEARUSDT', label: 'Near Protocol (NEAR)' },
  { value: 'ATOMUSDT', label: 'Cosmos (ATOM)' },
  { value: 'TRXUSDT', label: 'TRON (TRX)' },
  { value: 'SHIBUSDT', label: 'Shiba Inu (SHIB)' },
  { value: 'MATICUSDT', label: 'Polygon (MATIC)' },
  { value: 'ETCUSDT', label: 'Ethereum Classic (ETC)' },
  { value: 'FILUSDT', label: 'Filecoin (FIL)' },
  { value: 'LDOUSDT', label: 'Lido DAO (LDO)' },
  { value: 'APTUSDT', label: 'Aptos (APT)' },
  { value: 'OPUSDT', label: 'Optimism (OP)' },
  { value: 'ARBUSDT', label: 'Arbitrum (ARB)' },
  { value: 'RENDERUSDT', label: 'Render (RENDER)' },
  { value: 'INJUSDT', label: 'Injective (INJ)' },
  { value: 'SUIUSDT', label: 'Sui Network (SUI)' },
  { value: 'TIAUSDT', label: 'Celestia (TIA)' },
  { value: 'SEIUSDT', label: 'Sei Network (SEI)' },
  { value: 'ICPUSDT', label: 'Internet Computer (ICP)' },
  { value: 'STXUSDT', label: 'Stacks (STX)' },
  { value: 'GRTUSDT', label: 'The Graph (GRT)' },
  { value: 'GALAUSDT', label: 'Gala Games (GALA)' },
  { value: 'IMXUSDT', label: 'Immutable X (IMX)' },
  { value: 'FTMUSDT', label: 'Fantom (FTM)' },
  { value: 'VETUSDT', label: 'VeChain (VET)' }
];

export const ChartBrowser: React.FC = () => {
  const [selectedTicker, setSelectedTicker] = useState<string>('BTCUSDT');
  const [timeframe, setTimeframe] = useState<'1D' | '1W' | '1M' | '1Y'>('1Y');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [chartData, setChartData] = useState<ChartPoint[]>([]);
  const [stats, setStats] = useState({ high: 0, low: 0, current: 0, changePct: 0 });
  const [livePrices, setLivePrices] = useState<Record<string, number>>({});

  useEffect(() => {
    getPrices().then(data => setLivePrices(data.prices || {})).catch(() => {});
    const iv = setInterval(() => {
      getPrices().then(data => setLivePrices(data.prices || {})).catch(() => {});
    }, 3000);
    return () => clearInterval(iv);
  }, []);

  const generateMarketHistory = (ticker: string, tf: '1D' | '1W' | '1M' | '1Y') => {
    const basePrices: Record<string, number> = {
      BTCUSDT: 50000, ETHUSDT: 3000, SOLUSDT: 140, ADAUSDT: 0.45, DOTUSDT: 6.20,
      LTCUSDT: 82, DOGEUSDT: 0.15, XRPUSDT: 0.50, BNBUSDT: 580, AVAXUSDT: 34,
      LINKUSDT: 15, NEARUSDT: 6.80, ATOMUSDT: 8.50, TRXUSDT: 0.12, SHIBUSDT: 0.000022,
      MATICUSDT: 0.68, ETCUSDT: 28, FILUSDT: 5.40, LDOUSDT: 1.95, APTUSDT: 8.20,
      OPUSDT: 2.45, ARBUSDT: 0.95, RENDERUSDT: 8.10, INJUSDT: 24.50, SUIUSDT: 1.05,
      TIAUSDT: 4.80, SEIUSDT: 0.52, ICPUSDT: 11.20, STXUSDT: 1.85, GRTUSDT: 0.22,
      GALAUSDT: 0.042, IMXUSDT: 1.50, FTMUSDT: 0.72, VETUSDT: 0.035
    };
    let initialPrice = basePrices[ticker] || 50;

    const pointsMap = { '1D': 24, '1W': 7, '1M': 30, '1Y': 365 };
    const points = pointsMap[tf];

    const data: ChartPoint[] = [];
    const seed = ticker.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) + (tf.charCodeAt(0) * 10);
    let rng = seed;
    const nextRandom = () => { rng = (rng * 9301 + 49297) % 233280; return rng / 233280; };

    const startDate = new Date();
    if (tf === '1D') startDate.setHours(startDate.getHours() - 24);
    else startDate.setDate(startDate.getDate() - points);

    let price = initialPrice * (0.8 + nextRandom() * 0.4);
    let highest = price, lowest = price;
    const startPrice = price;

    for (let i = 0; i < points; i++) {
      const currentDate = new Date(startDate);
      let dateLabel = '';
      if (tf === '1D') {
        currentDate.setHours(currentDate.getHours() + i);
        dateLabel = currentDate.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false });
      } else {
        currentDate.setDate(currentDate.getDate() + i);
        dateLabel = currentDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      }

      let volatility = 0.02;
      if (ticker.includes('SOL') || ticker.includes('DOGE') || ticker.includes('SHIB')) volatility = 0.05;
      price = price * (1 + (nextRandom() - 0.485) * volatility);
      if (price > highest) highest = price;
      if (price < lowest) lowest = price;
      data.push({ date: dateLabel, Price: parseFloat(price.toFixed(price < 1 ? 5 : 2)) });
    }

    setChartData(data);
    setStats({ high: highest, low: lowest, current: price, changePct: ((price - startPrice) / startPrice) * 100 });
  };

  useEffect(() => {
    generateMarketHistory(selectedTicker, timeframe);
  }, [selectedTicker, timeframe]);

  const filteredCryptos = CRYPTO_OPTIONS.filter(opt =>
    opt.value.toUpperCase().includes(searchQuery.toUpperCase()) ||
    opt.label.toUpperCase().includes(searchQuery.toUpperCase())
  );

  const typedQuery = searchQuery.trim().toUpperCase();
  const validCustomTicker = typedQuery ? (typedQuery.endsWith('USDT') ? typedQuery : `${typedQuery}USDT`) : '';
  const showCustomOption = validCustomTicker && !CRYPTO_OPTIONS.some(o => o.value === validCustomTicker) && validCustomTicker.length >= 5;

  const getCryptoLabel = (sym: string) => CRYPTO_OPTIONS.find(c => c.value === sym)?.label || `${sym} Index`;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '20px' }}>
      <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px', height: 'fit-content' }}>
        <h3 style={{ fontSize: '0.8rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
          BROWSE MARKETS
        </h3>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <input type="text" className="form-input" style={{ paddingRight: '28px', fontSize: '0.8rem' }}
            placeholder="FILTER ASSETS..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
          <Search size={14} style={{ position: 'absolute', right: '10px', color: 'var(--text-muted)' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '350px', overflowY: 'auto' }}>
          {showCustomOption && (
            <button onClick={() => { setSelectedTicker(validCustomTicker); setSearchQuery(''); }}
              style={{
                display: 'flex', justifyContent: 'space-between', width: '100%', padding: '8px 10px',
                border: '1px dashed var(--text-primary)', background: 'transparent', color: 'var(--text-primary)',
                cursor: 'pointer', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem', fontWeight: 700
              }}>
              <span>+ CHOOSE: {validCustomTicker}</span>
            </button>
          )}
          {filteredCryptos.map((opt) => (
            <button key={opt.value} onClick={() => { setSelectedTicker(opt.value); setSearchQuery(''); }}
              style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', padding: '8px 10px',
                border: '1px solid ' + (selectedTicker === opt.value ? 'var(--text-primary)' : 'transparent'),
                background: selectedTicker === opt.value ? 'var(--panel-hover)' : 'transparent',
                color: selectedTicker === opt.value ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: selectedTicker === opt.value ? 700 : 500, textAlign: 'left', cursor: 'pointer',
                fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem'
              }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <CoinIcon symbol={opt.value} style={{ width: '16px', height: '16px' }} />
                <span>{opt.value}</span>
              </span>
              {livePrices[opt.value] && (
                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                  ${livePrices[opt.value].toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              )}
            </button>
          ))}
          {filteredCryptos.length === 0 && !showCustomOption && (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '12px', fontSize: '0.75rem' }}>
              NO ASSETS MATCHED
            </div>
          )}
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '1.6rem', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>{selectedTicker}</span>
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem',
                fontFamily: 'JetBrains Mono, monospace', fontWeight: 700,
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
          <div style={{ display: 'flex', background: 'var(--bg-color)', padding: '2px', border: '1px solid var(--panel-border)' }}>
            {(['1D', '1W', '1M', '1Y'] as const).map((tf) => (
              <button key={tf} onClick={() => setTimeframe(tf)} style={{
                padding: '6px 12px', border: 'none', fontWeight: 700, fontSize: '0.75rem',
                fontFamily: 'JetBrains Mono, monospace', cursor: 'pointer',
                background: timeframe === tf ? 'var(--text-primary)' : 'transparent',
                color: timeframe === tf ? 'var(--bg-color)' : 'var(--text-secondary)'
              }}>{tf}</button>
            ))}
          </div>
        </div>

        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px',
          borderBottom: '1px solid var(--panel-border)', borderTop: '1px solid var(--panel-border)', padding: '12px 0'
        }}>
          <div>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'block', fontFamily: 'JetBrains Mono, monospace' }}>SIMULATED INDEX</span>
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

        <div style={{ width: '100%', height: '300px' }}>
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
        </div>

        <div style={{
          border: '1px solid var(--panel-border)', background: 'var(--bg-color)',
          padding: '10px 14px', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.72rem',
          display: 'flex', flexDirection: 'column', gap: '4px'
        }}>
          <div style={{ display: 'flex', gap: '8px', color: 'var(--text-muted)' }}>
            <Calendar size={12} style={{ marginTop: '1px' }} />
            <span>[DATA STREAM] Simulated historical candle feed for {selectedTicker}. Seed-based deterministic replay.</span>
          </div>
          <div style={{ display: 'flex', gap: '8px', color: 'var(--text-muted)' }}>
            <BarChart2 size={12} style={{ marginTop: '1px' }} />
            <span>[LIVE] Current price from Binance: {livePrices[selectedTicker] ? `$${livePrices[selectedTicker].toLocaleString()}` : 'fetching...'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
