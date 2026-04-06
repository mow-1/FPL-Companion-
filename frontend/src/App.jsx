import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Players from './pages/Players'
import Predictions from './pages/Predictions'
import Fixtures from './pages/Fixtures'
import MyTeam from './pages/MyTeam'
import Profile from './pages/Profile'
import Advice from './pages/Advice'

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 1000 * 60 * 2, retry: 1 } } })

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0A0D14] flex items-center justify-center">
      <div className="text-slate-400 animate-pulse text-xl">Loading...</div>
    </div>
  )
  return user ? <Layout>{children}</Layout> : <Navigate to="/login" replace />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
      <Route path="/players" element={<PrivateRoute><Players /></PrivateRoute>} />
      <Route path="/predictions" element={<PrivateRoute><Predictions /></PrivateRoute>} />
      <Route path="/fixtures" element={<PrivateRoute><Fixtures /></PrivateRoute>} />
      <Route path="/my-team" element={<PrivateRoute><MyTeam /></PrivateRoute>} />
      <Route path="/advice" element={<PrivateRoute><Advice /></PrivateRoute>} />
      <Route path="/profile" element={<PrivateRoute><Profile /></PrivateRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={qc}>
        <AuthProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  )
}
