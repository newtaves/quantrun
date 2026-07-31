<<<<<<< HEAD
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
=======
import React from 'react';

interface CoinIconProps {
  symbol: string;
  size?: number;
  style?: React.CSSProperties;
}

const PNG_ICONS = new Set([
  'apt', 'arb', 'ftm', 'gala', 'imx', 'inj', 'ldo', 'op', 'opu',
  'render', 'sei', 'sui', 'tia',
]);

export const getBaseCoinSymbol = (symbol: string): string => {
  if (!symbol) return 'default';
  let base = symbol.toUpperCase();
  if (base.endsWith('USDT')) base = base.slice(0, -4);
  else if (base.endsWith('USD')) base = base.slice(0, -3);
>>>>>>> remove-django
  base = base.replace(/[^A-Z0-9]/g, '');
  return base.toLowerCase();
};

<<<<<<< HEAD
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
=======
const getIconPath = (base: string): string => {
  const ext = PNG_ICONS.has(base) ? 'png' : 'svg';
  return `/icons/${base}.${ext}`;
};

export const CoinIcon: React.FC<CoinIconProps> = ({ symbol, size = 16, style }) => {
  const base = getBaseCoinSymbol(symbol);
  const [error, setError] = React.useState(false);

  if (error) {
    return (
      <div
        style={{
          width: `${size}px`,
          height: `${size}px`,
          borderRadius: '50%',
          background: '#888',
          flexShrink: 0,
          ...style,
        }}
      />
    );
  }

  return (
    <img
      src={getIconPath(base)}
      alt={base}
      width={size}
      height={size}
      onError={() => setError(true)}
      style={{
        borderRadius: '50%',
        flexShrink: 0,
        objectFit: 'cover',
        ...style,
>>>>>>> remove-django
      }}
    />
  );
};
