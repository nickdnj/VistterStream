import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import CameraManagement from './components/CameraManagement';
import PresetManagement from './components/PresetManagement';
import TimelineEditor from './components/TimelineEditor';
import StreamingDestinations from './components/StreamingDestinations';
import Settings from './components/Settings';
import Scheduler from './components/Scheduler';
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
                    <Route path="/streams" element={<Navigate to="/timelines" replace />} />
                    <Route path="/timelines" element={<TimelineEditor />} />
                    <Route path="/destinations" element={<StreamingDestinations />} />
                    <Route path="/presets" element={<PresetManagement />} />
                    <Route path="/scheduler" element={<Scheduler />} />
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
            <Route path="/streams" element={<Navigate to="/timelines" replace />} />
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
            <Route path="/destinations" element={
              <ProtectedRoute>
                <Layout>
                  <StreamingDestinations />
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
            <Route path="/scheduler" element={
              <ProtectedRoute>
                <Layout>
                  <Scheduler />
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