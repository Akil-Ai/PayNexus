import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Payments } from './pages/Payments';
import { NewPayment } from './pages/NewPayment';
import { Translator } from './pages/Translator';
import { Compliance } from './pages/Compliance';
import { Reconciliation } from './pages/Reconciliation';
import { Exceptions } from './pages/Exceptions';
import { RailsChaos } from './pages/RailsChaos';
import { AuditExplorer } from './pages/AuditExplorer';
import { Admin } from './pages/Admin';
import { DemoRunner } from './pages/DemoRunner';
import { IntroVideo } from './components/IntroVideo';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('paynexus_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <Layout>{children}</Layout>;
};

export const App: React.FC = () => {
  const [showIntro, setShowIntro] = React.useState<boolean>(() => {
    // Check if user has already seen intro in this session or window
    const watched = sessionStorage.getItem('paynexus_intro_watched');
    return watched !== 'true';
  });

  const handleVideoComplete = () => {
    sessionStorage.setItem('paynexus_intro_watched', 'true');
    setShowIntro(false);
  };

  if (showIntro) {
    return <IntroVideo onComplete={handleVideoComplete} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login onReplayIntro={() => setShowIntro(true)} />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/payments"
          element={
            <ProtectedRoute>
              <Payments />
            </ProtectedRoute>
          }
        />
        <Route
          path="/payments/new"
          element={
            <ProtectedRoute>
              <NewPayment />
            </ProtectedRoute>
          }
        />
        <Route
          path="/messages"
          element={
            <ProtectedRoute>
              <Translator />
            </ProtectedRoute>
          }
        />
        <Route
          path="/compliance"
          element={
            <ProtectedRoute>
              <Compliance />
            </ProtectedRoute>
          }
        />
        <Route
          path="/reconciliation"
          element={
            <ProtectedRoute>
              <Reconciliation />
            </ProtectedRoute>
          }
        />
        <Route
          path="/exceptions"
          element={
            <ProtectedRoute>
              <Exceptions />
            </ProtectedRoute>
          }
        />
        <Route
          path="/rails"
          element={
            <ProtectedRoute>
              <RailsChaos />
            </ProtectedRoute>
          }
        />
        <Route
          path="/audit"
          element={
            <ProtectedRoute>
              <AuditExplorer />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <Admin />
            </ProtectedRoute>
          }
        />
        <Route
          path="/demo"
          element={
            <ProtectedRoute>
              <DemoRunner />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
export default App;
