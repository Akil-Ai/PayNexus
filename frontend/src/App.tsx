import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { Layout } from './components/Layout';
import { PageTransition } from './components/PageTransition';
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

// AnimatedRoutes handles route change detection and executes AnimatePresence mode="wait"
const AnimatedRoutes: React.FC<{ onReplayIntro: () => void }> = ({ onReplayIntro }) => {
  const location = useLocation();

  // Scroll to top on navigation while preserving browser history
  React.useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior });
  }, [location.pathname]);

  return (
    <AnimatePresence mode="wait" initial={false}>
      <Routes location={location} key={location.pathname}>
        <Route path="/login" element={<Login onReplayIntro={onReplayIntro} />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <PageTransition>
                <Dashboard />
              </PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/payments"
          element={
            <ProtectedRoute>
              <PageTransition>
                <Payments />
              </PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/payments/new"
          element={
            <ProtectedRoute>
              <PageTransition>
                <NewPayment />
              </PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/messages"
          element={
            <ProtectedRoute>
              <PageTransition>
                <Translator />
              </PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/compliance"
          element={
            <ProtectedRoute>
              <PageTransition>
                <Compliance />
              </PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/reconciliation"
          element={
            <ProtectedRoute>
              <PageTransition>
                <Reconciliation />
              </PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/exceptions"
          element={
            <ProtectedRoute>
              <PageTransition>
                <Exceptions />
              </PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/rails"
          element={
            <ProtectedRoute>
              <PageTransition>
                <RailsChaos />
              </PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/audit"
          element={
            <ProtectedRoute>
              <PageTransition>
                <AuditExplorer />
              </PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <PageTransition>
                <Admin />
              </PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/demo"
          element={
            <ProtectedRoute>
              <PageTransition>
                <DemoRunner />
              </PageTransition>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
};

export const App: React.FC = () => {
  const [showIntro, setShowIntro] = React.useState<boolean>(() => {
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
      <AnimatedRoutes onReplayIntro={() => setShowIntro(true)} />
    </BrowserRouter>
  );
};

export default App;
