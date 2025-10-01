import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import CameraManagement from './components/CameraManagement';
import StreamManagement from './components/StreamManagement';
import PresetManagement from './components/PresetManagement';
import TimelineEditor from './components/TimelineEditor';
import Settings from './components/Settings';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={
              <ProtectedRoute>
                <Layout>
                  <Routes>
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/cameras" element={<CameraManagement />} />
                    <Route path="/streams" element={<StreamManagement />} />
                    <Route path="/timelines" element={<TimelineEditor />} />
                    <Route path="/presets" element={<PresetManagement />} />
                    <Route path="/settings" element={<Settings />} />
                  </Routes>
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Layout>
                  <Dashboard />
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/cameras" element={
              <ProtectedRoute>
                <Layout>
                  <CameraManagement />
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/streams" element={
              <ProtectedRoute>
                <Layout>
                  <StreamManagement />
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/presets" element={
              <ProtectedRoute>
                <Layout>
                  <PresetManagement />
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/timelines" element={
              <ProtectedRoute>
                <Layout>
                  <TimelineEditor />
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/settings" element={
              <ProtectedRoute>
                <Layout>
                  <Settings />
                </Layout>
              </ProtectedRoute>
            } />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;