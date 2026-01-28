import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';

// Pages
import { Login } from './pages/Login';
import { AuthCallback } from './pages/AuthCallback';
import { AuthError } from './pages/AuthError';
import { Dashboard } from './pages/Dashboard';
import { DesignerDashboard } from './pages/DesignerDashboard';
import { AIDesignGenerator } from './pages/AIDesignGenerator';
import { DesignDetail } from './pages/DesignDetail';
import { DesignHistory } from './pages/DesignHistory';
import { QuoteEstimator } from './pages/QuoteEstimator';
import { MarketingTools } from './pages/MarketingTools';
import { Policies } from './pages/Policies';
import { CustomDesignDashboard } from './pages/CustomDesignDashboard';
import { CustomDesignBuilder } from './pages/CustomDesignBuilder';
import { CustomDesignDetail } from './pages/CustomDesignDetail';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route path="/auth/error" element={<AuthError />} />

            {/* Protected routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            {/* AI Design Generator routes */}
            <Route
              path="/ai-design-generator"
              element={
                <ProtectedRoute>
                  <DesignerDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/ai-design-generator/new"
              element={
                <ProtectedRoute>
                  <AIDesignGenerator />
                </ProtectedRoute>
              }
            />
            <Route
              path="/ai-design-generator/history"
              element={
                <ProtectedRoute>
                  <DesignHistory />
                </ProtectedRoute>
              }
            />
            <Route
              path="/ai-design-generator/design/:designId"
              element={
                <ProtectedRoute>
                  <DesignDetail />
                </ProtectedRoute>
              }
            />
            {/* Custom Design Builder routes */}
            <Route
              path="/custom-design-builder"
              element={
                <ProtectedRoute>
                  <CustomDesignDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/custom-design-builder/new"
              element={
                <ProtectedRoute>
                  <CustomDesignBuilder />
                </ProtectedRoute>
              }
            />
            <Route
              path="/custom-design-builder/design/:designId"
              element={
                <ProtectedRoute>
                  <CustomDesignDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/quote-estimator"
              element={
                <ProtectedRoute>
                  <QuoteEstimator />
                </ProtectedRoute>
              }
            />
            <Route
              path="/marketing-tools"
              element={
                <ProtectedRoute>
                  <MarketingTools />
                </ProtectedRoute>
              }
            />
            <Route
              path="/policies"
              element={
                <ProtectedRoute>
                  <Policies />
                </ProtectedRoute>
              }
            />

            {/* Default redirect */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
