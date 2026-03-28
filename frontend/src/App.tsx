import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import TimelineEditor from './components/TimelineEditor';
import StreamingDestinations from './components/StreamingDestinations';
import Settings from './components/Settings';
import ReelForge from './components/ReelForge';
import AssetStudio from './components/AssetStudio';
import CanvasEditorPage from './components/canvas/CanvasEditorPage';
import SpikeCanvasRoute from './components/spike/SpikeCanvasRoute';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/*" element={
              <ProtectedRoute>
                <Layout>
                  <Routes>
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/cameras" element={<Navigate to="/settings" state={{ tab: 'cameras' }} replace />} />
                    <Route path="/streams" element={<Navigate to="/timelines" replace />} />
                    <Route path="/timelines" element={<TimelineEditor />} />
                    <Route path="/reelforge" element={<ReelForge />} />
                    <Route path="/destinations" element={<StreamingDestinations />} />
                    <Route path="/presets" element={<Navigate to="/settings" state={{ tab: 'cameras' }} replace />} />
                    <Route path="/scheduler" element={<Navigate to="/settings" replace />} />
                    <Route path="/settings" element={<Settings />} />
                    <Route path="/assets" element={<AssetStudio />} />
                    <Route path="/assets/templates" element={<AssetStudio />} />
                    <Route path="/assets/editor" element={<AssetStudio />} />
                    <Route path="/assets/editor/new" element={<CanvasEditorPage />} />
                    <Route path="/assets/editor/:id" element={<CanvasEditorPage />} />
                    <Route path="/assets/analytics" element={<AssetStudio />} />
                    <Route path="/spike-canvas" element={<SpikeCanvasRoute />} />
                  </Routes>
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