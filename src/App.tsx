import { HashRouter, MemoryRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { AnalysisPage } from './pages/AnalysisPage';
import { DeliveryPage } from './pages/DeliveryPage';
import { HistoryPage } from './pages/HistoryPage';
import { ReviewPage } from './pages/ReviewPage';
import { StatsPage } from './pages/StatsPage';
import { UploadPage } from './pages/UploadPage';
import { StoreProvider, useStore } from './store';
import './pages/pages.css';
// 공유용 한 파일 미리보기(--mode single)는 주소 대신 메모리로 화면을 바꿔요
const Router = import.meta.env.MODE === 'single' ? MemoryRouter : HashRouter;

function Toast() {
  const { toast } = useStore();
  return toast ? (
    <div className="toast" role="status">
      {toast}
    </div>
  ) : null;
}

export default function App() {
  return (
    <StoreProvider>
      {/* HashRouter: 서버 설정 없이 어디에 올려도 새로고침해도 화면이 유지돼요 */}
      <Router>
        <div className="app">
          <Sidebar />
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/analysis" element={<AnalysisPage />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/delivery" element={<DeliveryPage />} />
            <Route path="/stats" element={<StatsPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
        <Toast />
      </Router>
    </StoreProvider>
  );
}
