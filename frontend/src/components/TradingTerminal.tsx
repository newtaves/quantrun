import React, { useState, useRef, useEffect } from 'react';
import { Search } from 'lucide-react';
import { CoinIcon } from './CoinIcon';
import { getPrice, placeOrder } from '../api/api';
import { useToast } from '../hooks/useToast';

interface TradingTerminalProps {
  portfolioId: number;
  prices: Record<string, number>;
  onOrderPlaced: () => void;
}

const CRYPTO_META: Record<string, { symbol: string, label: string }> = {
  'BTCUSDT': { symbol: '₿', label: 'Bitcoin' },
  'ETHUSDT': { symbol: 'Ξ', label: 'Ethereum' },
  'SOLUSDT': { symbol: '◎', label: 'Solana' },
  'ADAUSDT': { symbol: '₳', label: 'Cardano' },
  'DOTUSDT': { symbol: '●', label: 'Polkadot' },
  'LTCUSDT': { symbol: 'Ł', label: 'Litecoin' },
  'XRPUSDT': { symbol: '✕', label: 'Ripple' },
  'DOGEUSDT': { symbol: 'Ð', label: 'Dogecoin' },
  'BNBUSDT': { symbol: '🔶', label: 'BNB Coin' },
  'AVAXUSDT': { symbol: '🔺', label: 'Avalanche' },
  'LINKUSDT': { symbol: '⬡', label: 'Chainlink' },
  'NEARUSDT': { symbol: 'Ⓝ', label: 'Near Protocol' },
  'ATOMUSDT': { symbol: '⚛', label: 'Cosmos' },
  'TRXUSDT': { symbol: '🔴', label: 'TRON' },
  'SHIBUSDT': { symbol: '🐕', label: 'Shiba Inu' },
  'MATICUSDT': { symbol: '🟣', label: 'Polygon' },
  'ETCUSDT': { symbol: '🟢', label: 'Ethereum Classic' },
  'FILUSDT': { symbol: '⨎', label: 'Filecoin' },
  'LDOUSDT': { symbol: '💧', label: 'Lido DAO' },
  'APTUSDT': { symbol: '▲', label: 'Aptos' },
  'OPUSDT': { symbol: '🔴', label: 'Optimism' },
  'ARBUSDT': { symbol: '🔵', label: 'Arbitrum' },
  'RENDERUSDT': { symbol: '⭕', label: 'Render' },
  'INJUSDT': { symbol: '🥷', label: 'Injective' },
  'SUIUSDT': { symbol: '💧', label: 'Sui Network' },
  'TIAUSDT': { symbol: '☄', label: 'Celestia' },
  'SEIUSDT': { symbol: '🌊', label: 'Sei Network' },
  'ICPUSDT': { symbol: '∞', label: 'Internet Computer' },
  'STXUSDT': { symbol: '🪙', label: 'Stacks' },
  'GRTUSDT': { symbol: '📊', label: 'The Graph' },
  'GALAUSDT': { symbol: '🎮', label: 'Gala Games' },
  'IMXUSDT': { symbol: '⚡', label: 'Immutable X' },
  'FTMUSDT': { symbol: '👻', label: 'Fantom' },
  'VETUSDT': { symbol: '🔷', label: 'VeChain' }
};

export const TradingTerminal: React.FC<TradingTerminalProps> = ({ portfolioId, prices, onOrderPlaced }) => {
  const { addToast } = useToast();
  const [symbol, setSymbol] = useState<string>('BTCUSDT');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isDropdownOpen, setIsDropdownOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [quantity, setQuantity] = useState<string>('0.1');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET');
  const [limitPrice, setLimitPrice] = useState<string>('');
  const [stoploss, setStoploss] = useState<string>('');
  const [target, setTarget] = useState<string>('');

  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [orderStatusMsg, setOrderStatusMsg] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectSymbol = (sym: string) => {
    setSymbol(sym);
    setIsDropdownOpen(false);
    setSearchQuery('');
    if (prices[sym]) {
      setLimitPrice(prices[sym].toString());
    } else {
      getPrice(sym).then(data => {
        if (data.price) {
          setLimitPrice(data.price.toString());
        }
      }).catch(() => {});
    }
  };

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setOrderStatusMsg(null);

    const qty = parseFloat(quantity);
    if (isNaN(qty) || qty <= 0) {
      setOrderStatusMsg({ type: 'error', text: 'Please enter a valid positive quantity.' });
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: any = {
        symbol: symbol.toUpperCase(),
        side: side,
        qty: qty,
        limit: orderType === 'LIMIT' && limitPrice ? parseFloat(limitPrice) : undefined,
        target: target ? parseFloat(target) : undefined,
        stoploss: stoploss ? parseFloat(stoploss) : undefined,
      };

      const data = await placeOrder(portfolioId, payload);

      if (data.order && !data.order.error) {
        const msg = `ORDER FILLED: ${side} ${quantity} ${symbol} @ $${data.order.executed_price || prices[symbol] || 'MKT'}`;
        setOrderStatusMsg({ type: 'success', text: msg });
        addToast(msg, 'success');
        setStoploss('');
        setTarget('');
        if (orderType === 'MARKET') setQuantity('0.1');
        onOrderPlaced();
      } else {
        const errMsg = data.order?.error || 'Order execution failed.';
        setOrderStatusMsg({ type: 'error', text: errMsg });
        addToast(errMsg, 'error');
      }
    } catch (err: any) {
      const errMsg = err.message || 'Network error.';
      setOrderStatusMsg({ type: 'error', text: errMsg });
      addToast(errMsg, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const allSymbols = Array.from(new Set([...Object.keys(CRYPTO_META), ...Object.keys(prices)]));
  const filteredSymbols = allSymbols.filter(sym => {
    const meta = CRYPTO_META[sym];
    const q = searchQuery.toUpperCase();
    return sym.includes(q) || (meta && meta.label.toUpperCase().includes(q));
  });

  const typedSymbol = searchQuery.trim().toUpperCase();
  const validCustomTicker = typedSymbol ? (typedSymbol.endsWith('USDT') ? typedSymbol : `${typedSymbol}USDT`) : '';
  const showCustomOption = validCustomTicker && !allSymbols.includes(validCustomTicker) && validCustomTicker.length >= 5;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 style={{ fontSize: '0.85rem', color: 'var(--text-primary)', marginBottom: '14px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
          PLACE MARKET/LIMIT ALGO ORDER
        </h3>

        {orderStatusMsg && (
          <div style={{
            border: `1px solid ${orderStatusMsg.type === 'success' ? 'var(--success)' : 'var(--danger)'}`,
            background: orderStatusMsg.type === 'success' ? 'rgba(0, 255, 0, 0.04)' : 'rgba(255, 56, 56, 0.04)',
            color: orderStatusMsg.type === 'success' ? 'var(--success)' : 'var(--danger)',
            padding: '10px', fontSize: '0.75rem', fontFamily: 'JetBrains Mono, monospace', marginBottom: '14px'
          }}>
            <strong>[{orderStatusMsg.type === 'success' ? 'SUCCESS' : 'EXECUTION_ERROR'}]:</strong> {orderStatusMsg.text}
          </div>
        )}

        <form onSubmit={handlePlaceOrder} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div ref={dropdownRef} style={{ position: 'relative' }}>
              <label className="form-label">TICKER (SEARCHABLE)</label>
              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <input
                  type="text"
                  className="form-input"
                  style={{ fontWeight: 700, textTransform: 'uppercase', paddingRight: '28px' }}
                  placeholder="SEARCH CRYPTO..."
                  value={isDropdownOpen ? searchQuery : symbol}
                  onChange={(e) => { setIsDropdownOpen(true); setSearchQuery(e.target.value); }}
                  onFocus={() => { setIsDropdownOpen(true); setSearchQuery(''); }}
                />
                <Search size={14} style={{ position: 'absolute', right: '10px', color: 'var(--text-muted)' }} />
              </div>

              {isDropdownOpen && (
                <div style={{
                  position: 'absolute', top: '100%', left: 0, width: '100%',
                  maxHeight: '180px', overflowY: 'auto', border: '1px solid var(--text-primary)',
                  background: 'var(--panel-bg)', zIndex: 20, fontSize: '0.8rem',
                  fontFamily: 'JetBrains Mono, monospace'
                }}>
                  {showCustomOption && (
                    <div onClick={() => handleSelectSymbol(validCustomTicker)} style={{
                      padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--panel-border)',
                      background: 'transparent', color: 'var(--text-primary)', fontStyle: 'italic', fontWeight: 700,
                      display: 'flex', justifyContent: 'space-between'
                    }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        <CoinIcon symbol={validCustomTicker} style={{ width: '16px', height: '16px' }} />
                        <span>CHOOSE: {validCustomTicker}</span>
                      </span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>QUERY LIVE INDEX</span>
                    </div>
                  )}
                  {filteredSymbols.map((sym) => (
                    <div key={sym} onClick={() => handleSelectSymbol(sym)} style={{
                      padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--panel-border)',
                      background: symbol === sym ? 'var(--panel-hover)' : 'transparent',
                      color: 'var(--text-primary)', display: 'flex', justifyContent: 'space-between'
                    }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        <CoinIcon symbol={sym} style={{ width: '16px', height: '16px' }} />
                        <span>{sym}</span>
                      </span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                        {prices[sym] ? `$${prices[sym].toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'QUERY INDEX'}
                      </span>
                    </div>
                  ))}
                  {filteredSymbols.length === 0 && !showCustomOption && (
                    <div style={{ padding: '8px', color: 'var(--text-muted)', textAlign: 'center' }}>NO MATCHES</div>
                  )}
                </div>
              )}
            </div>

            <div>
              <label className="form-label">SIDE</label>
              <div style={{ display: 'flex', background: 'var(--bg-color)', padding: '2px', border: '1px solid var(--panel-border)' }}>
                <button type="button" onClick={() => setSide('BUY')} style={{
                  flex: 1, padding: '8px', border: 'none', fontWeight: 700, cursor: 'pointer',
                  fontSize: '0.75rem', fontFamily: 'JetBrains Mono, monospace',
                  background: side === 'BUY' ? 'var(--success)' : 'transparent',
                  color: side === 'BUY' ? '#000000' : 'var(--text-secondary)', transition: 'all 0.1s'
                }}>BUY</button>
                <button type="button" onClick={() => setSide('SELL')} style={{
                  flex: 1, padding: '8px', border: 'none', fontWeight: 700, cursor: 'pointer',
                  fontSize: '0.75rem', fontFamily: 'JetBrains Mono, monospace',
                  background: side === 'SELL' ? 'var(--danger)' : 'transparent',
                  color: side === 'SELL' ? '#ffffff' : 'var(--text-secondary)', transition: 'all 0.1s'
                }}>SELL</button>
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label className="form-label">QUANTITY</label>
              <input type="number" step="any" className="form-input" value={quantity}
                onChange={(e) => setQuantity(e.target.value)} placeholder="0.1" />
            </div>
            <div>
              <label className="form-label">ORDER TYPE</label>
              <select className="form-input" value={orderType}
                onChange={(e) => setOrderType(e.target.value as 'MARKET' | 'LIMIT')}
                style={{ cursor: 'pointer' }}>
                <option value="MARKET">MARKET</option>
                <option value="LIMIT">LIMIT</option>
              </select>
            </div>
          </div>

          {orderType === 'LIMIT' && (
            <div>
              <label className="form-label">LIMIT PRICE ($)</label>
              <input type="number" step="any" className="form-input" value={limitPrice}
                onChange={(e) => setLimitPrice(e.target.value)} placeholder="Limit Price" />
            </div>
          )}

          <div style={{ borderTop: '1px solid var(--panel-border)', paddingTop: '12px', marginTop: '2px' }}>
            <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.05em', display: 'block', marginBottom: '8px', fontFamily: 'JetBrains Mono, monospace' }}>
              ADVANCED RISK CONTROLS (OPTIONAL)
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label className="form-label">STOP LOSS ($)</label>
                <input type="number" step="any" className="form-input" value={stoploss}
                  onChange={(e) => setStoploss(e.target.value)} placeholder="SL TRIGGER" />
              </div>
              <div>
                <label className="form-label">TAKE PROFIT ($)</label>
                <input type="number" step="any" className="form-input" value={target}
                  onChange={(e) => setTarget(e.target.value)} placeholder="TP TARGET" />
              </div>
            </div>
          </div>

          <button type="submit" className="btn" style={{
            padding: '10px', fontWeight: 700, fontSize: '0.8rem', marginTop: '8px',
            background: side === 'BUY' ? 'var(--success)' : 'var(--danger)',
            border: side === 'BUY' ? '1px solid var(--success)' : '1px solid var(--danger)',
            color: side === 'BUY' ? '#000000' : '#ffffff'
          }} disabled={isSubmitting}>
            {isSubmitting ? 'TRANSMITTING...' : `TRANSMIT ${side} ORDER`}
          </button>
        </form>
      </div>
    </div>
  );
};
