import React, { useState, useEffect } from 'react';

interface CoinIconProps {
  symbol: string;
  style?: React.CSSProperties;
}

export const getBaseCoinSymbol = (symbol: string): string => {
  if (!symbol) return 'default';
  let base = symbol.toUpperCase();
  // Strip common fiat or quote currency extensions (e.g. BTCUSDT -> BTC)
  if (base.endsWith('USDT')) {
    base = base.slice(0, -4);
  } else if (base.endsWith('USD')) {
    base = base.slice(0, -3);
  }
  base = base.replace(/[^A-Z0-9]/g, '');
  return base.toLowerCase();
};

export const CoinIcon: React.FC<CoinIconProps> = ({ symbol, style }) => {
  const base = getBaseCoinSymbol(symbol);
  const [src, setSrc] = useState(`/icons/${base}.svg`);

  useEffect(() => {
    setSrc(`/icons/${base}.svg`);
  }, [base]);

  const handleError = () => {
    if (src.endsWith('.svg') && src !== '/icons/default.svg') {
      setSrc(`/icons/${base}.png`);
    } else if (src.endsWith('.png')) {
      setSrc('/icons/default.svg');
    }
  };

  return (
    <img
      src={src}
      onError={handleError}
      alt={symbol}
      style={{
        width: '16px',
        height: '16px',
        objectFit: 'contain',
        display: 'inline-block',
        verticalAlign: 'middle',
        ...style
      }}
    />
  );
};
