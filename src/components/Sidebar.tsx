import { NavLink, useLocation } from 'react-router-dom';
import { useStore } from '../store';
import { reviewTotals } from '../data/mock';

/** v3/Sidebar (Figma 82:93 · 82:107 · 82:121) */
export function Sidebar() {
  const { complaints, deliveries } = useStore();
  const handled = complaints.filter((c) => c.status !== 'review' && c.source !== 'auto').length;
  const unsent = 8 - Object.keys(deliveries).length;
  const remaining = reviewTotals.needsReview - handled;
  const { pathname } = useLocation();

  const item = ({ isActive }: { isActive: boolean }) => `sidebar__item ${isActive ? 'is-active' : ''}`;

  return (
    <nav className="sidebar" aria-label="주 메뉴">
      <div className="sidebar__brand">
        <span className="sidebar__logo">KORAIL</span>
        <span className="sidebar__product">VOC 업무 자동화</span>
      </div>
      <NavLink to="/" end className={({ isActive }) => item({ isActive: isActive || pathname.startsWith('/analysis') })}>
        새 민원 분석
      </NavLink>
      <NavLink to="/review" className={item}>
        검토함
        {remaining > 0 && <span className="sidebar__count">{remaining}</span>}
      </NavLink>
      <NavLink to="/delivery" className={item}>
        부서별 전달
        {unsent > 0 && <span className="sidebar__count sidebar__count--info">{unsent}곳</span>}
      </NavLink>
      <NavLink to="/stats" className={item}>
        통계·보고서
      </NavLink>
      <NavLink to="/history" className={item}>
        처리 이력
      </NavLink>
    </nav>
  );
}
