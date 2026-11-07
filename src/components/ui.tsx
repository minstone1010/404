import type { ButtonHTMLAttributes, ReactNode } from 'react';
import type { ChipTone } from '../types';
import './ui.css';

/** VOC/Button/primary · secondary (Figma 63:84, 63:86) */
export function Button({
  variant = 'primary',
  fill = false,
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary'; fill?: boolean }) {
  return (
    <button
      type="button"
      className={`btn btn--${variant} ${fill ? 'btn--fill' : ''} ${className}`}
      {...props}
    />
  );
}

/** v3/Chip (Figma 82:84 warn · 82:86 ok · 82:88 info · 82:90 bad) */
export function Chip({ tone = 'warn', children }: { tone?: ChipTone; children: ReactNode }) {
  return <span className={`chip chip--${tone}`}>{children}</span>;
}

export function PageHeader({ title, desc, aside }: { title: ReactNode; desc: ReactNode; aside?: ReactNode }) {
  return (
    <header className="page-header">
      <div className="page-header__text">
        <h1 className="page-header__title" style={{ margin: 0 }}>
          {title}
        </h1>
        <p className="page-header__desc">{desc}</p>
      </div>
      {aside ?? <span className="demo-badge">화면 시안 · 가상 민원</span>}
    </header>
  );
}

/** 선택 상자: Figma 모양 그대로 그리고, 위에 투명한 네이티브 select를 겹쳐요 */
export function Select<T extends string>({
  value,
  options,
  onChange,
  flagged = false,
  fill = false,
  label,
}: {
  value: T;
  options: readonly T[];
  onChange: (value: T) => void;
  flagged?: boolean;
  fill?: boolean;
  label: string;
}) {
  return (
    <span className={`select ${fill ? 'select--fill' : ''}`} onClick={(e) => e.stopPropagation()}>
      <select
        className="select__native"
        aria-label={label}
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
      <span className={`select__face ${flagged ? 'is-flagged' : ''}`}>
        <span className="select__value">{value}</span>
        <span className="select__caret" aria-hidden>
          ▾
        </span>
      </span>
    </span>
  );
}

export function ProgressBar({
  percent,
  height,
  color = 'var(--accent)',
}: {
  percent: number;
  height: number;
  color?: string;
}) {
  return (
    <div
      className="bar"
      style={{ height, borderRadius: height / 2 }}
      role="progressbar"
      aria-valuenow={Math.round(percent)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="bar__fill" style={{ width: `${percent}%`, background: color, borderRadius: height / 2 }} />
    </div>
  );
}

export const fmt = (n: number) => n.toLocaleString('ko-KR');
