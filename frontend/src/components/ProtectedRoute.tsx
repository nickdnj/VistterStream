import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  // TEMPORARILY BYPASS AUTH FOR DEMO
  console.log('ProtectedRoute: Bypassing auth for demo');
  return <>{children}</>;
};

export default ProtectedRoute;
