import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { authService } from '../services/authService';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';

type Mode = 'login' | 'forgot' | 'reset';

const inputClass =
  'w-full px-3 py-2 border border-gray-600 rounded-md shadow-sm placeholder-gray-400 bg-dark-700 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<Mode>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const { login } = useAuth();

  // Reset-flow fields
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const clearMessages = () => {
    setError('');
    setInfo('');
  };

  const switchMode = (next: Mode) => {
    clearMessages();
    setPassword('');
    setCode('');
    setNewPassword('');
    setConfirmPassword('');
    setMode(next);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    clearMessages();
    try {
      const success = await login(username, password);
      if (!success) {
        setError('Invalid username or password');
      } else {
        const redirectTo =
          (location.state as { from?: { pathname?: string } } | undefined)?.from?.pathname ||
          '/dashboard';
        navigate(redirectTo, { replace: true });
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgot = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    clearMessages();
    try {
      await authService.forgotPassword(username || 'admin');
      setInfo(
        'If a recovery email is configured, a reset code has been sent. ' +
          'Enter the code below to set a new password.'
      );
      setMode('reset');
    } catch (err) {
      console.error('Forgot-password error:', err);
      // Backend returns a generic response; only surface unexpected failures.
      setError('Could not start password reset. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    clearMessages();
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await authService.resetPassword(username || 'admin', code.trim(), newPassword);
      switchMode('login');
      setInfo('Password reset successfully. You can now sign in with your new password.');
    } catch (err: any) {
      console.error('Reset-password error:', err);
      const detail = err?.response?.data?.detail;
      setError(detail || 'Could not reset password. Check the code and try again.');
    } finally {
      setLoading(false);
    }
  };

  const subtitle =
    mode === 'login'
      ? 'Sign in to your streaming appliance'
      : mode === 'forgot'
      ? 'Reset your password'
      : 'Enter your reset code';

  return (
    <div className="min-h-screen bg-gradient-to-br from-dark-900 via-dark-800 to-dark-900 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-primary-600 rounded-full flex items-center justify-center">
            <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <h2 className="mt-6 text-3xl font-bold text-white">VistterStream</h2>
          <p className="mt-2 text-sm text-gray-400">{subtitle}</p>
        </div>

        <div className="mt-8 bg-dark-800 rounded-lg p-8 shadow-xl">
          {info && (
            <div className="mb-4 p-3 bg-green-900/20 border border-green-500/30 rounded-md">
              <p className="text-sm text-green-400">{info}</p>
            </div>
          )}
          {error && (
            <div className="mb-4 p-3 bg-red-900/20 border border-red-500/30 rounded-md">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {mode === 'login' && (
            <form className="space-y-6" onSubmit={handleLogin}>
              <div className="space-y-4">
                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-2">
                    Username
                  </label>
                  <input
                    id="username"
                    name="username"
                    type="text"
                    autoComplete="username"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className={inputClass}
                    placeholder="Enter your username"
                  />
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className={`${inputClass} pr-10`}
                      placeholder="Enter your password"
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 pr-3 flex items-center"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? (
                        <EyeSlashIcon className="h-5 w-5 text-gray-400" />
                      ) : (
                        <EyeIcon className="h-5 w-5 text-gray-400" />
                      )}
                    </button>
                  </div>
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Signing in...' : 'Sign in'}
                </button>
              </div>

              <div className="text-center">
                <button
                  type="button"
                  onClick={() => switchMode('forgot')}
                  className="text-sm text-primary-400 hover:text-primary-300"
                >
                  Forgot password?
                </button>
              </div>
            </form>
          )}

          {mode === 'forgot' && (
            <form className="space-y-6" onSubmit={handleForgot}>
              <p className="text-sm text-gray-400">
                Enter your username. We'll send a one-time reset code to the recovery email on
                file. (If email isn't configured, the code is written to the appliance logs.)
              </p>
              <div>
                <label htmlFor="forgot-username" className="block text-sm font-medium text-gray-300 mb-2">
                  Username
                </label>
                <input
                  id="forgot-username"
                  type="text"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className={inputClass}
                  placeholder="admin"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Sending...' : 'Send reset code'}
              </button>
              <div className="flex justify-between text-sm">
                <button type="button" onClick={() => switchMode('login')} className="text-gray-400 hover:text-gray-300">
                  Back to sign in
                </button>
                <button type="button" onClick={() => switchMode('reset')} className="text-primary-400 hover:text-primary-300">
                  I already have a code
                </button>
              </div>
            </form>
          )}

          {mode === 'reset' && (
            <form className="space-y-6" onSubmit={handleReset}>
              <div>
                <label htmlFor="reset-username" className="block text-sm font-medium text-gray-300 mb-2">
                  Username
                </label>
                <input
                  id="reset-username"
                  type="text"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className={inputClass}
                  placeholder="admin"
                />
              </div>
              <div>
                <label htmlFor="reset-code" className="block text-sm font-medium text-gray-300 mb-2">
                  Reset code
                </label>
                <input
                  id="reset-code"
                  type="text"
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value.toUpperCase())}
                  className={`${inputClass} tracking-widest font-mono uppercase`}
                  placeholder="ABCD2345"
                  autoCapitalize="characters"
                />
              </div>
              <div>
                <label htmlFor="reset-new-password" className="block text-sm font-medium text-gray-300 mb-2">
                  New password
                </label>
                <input
                  id="reset-new-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className={inputClass}
                  placeholder="At least 8 characters, 1 letter + 1 digit"
                />
              </div>
              <div>
                <label htmlFor="reset-confirm-password" className="block text-sm font-medium text-gray-300 mb-2">
                  Confirm new password
                </label>
                <input
                  id="reset-confirm-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className={inputClass}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Resetting...' : 'Set new password'}
              </button>
              <div className="text-center text-sm">
                <button type="button" onClick={() => switchMode('login')} className="text-gray-400 hover:text-gray-300">
                  Back to sign in
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default Login;
