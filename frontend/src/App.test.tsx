import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';
import { useAuth } from './contexts/AuthContext';

jest.mock('./contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="auth-provider">{children}</div>,
  useAuth: jest.fn()
}));

jest.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Routes: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Route: ({ element }: { element: React.ReactNode }) => <div>{element}</div>,
  Navigate: ({ to, replace }: { to: string; replace?: boolean }) => (
    <div data-testid="navigate" data-to={to} data-replace={String(Boolean(replace))}>
      Navigate to {to}
    </div>
  )
}));

jest.mock('./components/Login', () => () => <div>Login Component</div>);
jest.mock('./components/Dashboard', () => () => <div>Dashboard Component</div>);
jest.mock('./components/CameraManagement', () => () => <div>Camera Management Component</div>);
jest.mock('./components/StreamManagement', () => () => <div>Stream Management Component</div>);
jest.mock('./components/PresetManagement', () => () => <div>Preset Management Component</div>);
jest.mock('./components/Settings', () => () => <div>Settings Component</div>);
jest.mock('./components/Layout', () => ({ children }: { children: React.ReactNode }) => (
  <div data-testid="layout">{children}</div>
));

const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

describe('App routing with authentication', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('redirects to the login route when unauthenticated', () => {
    mockedUseAuth.mockReturnValue({
      user: null,
      loading: false,
      login: jest.fn(),
      logout: jest.fn()
    });

    render(<App />);

    const navigateElements = screen.getAllByTestId('navigate');
    expect(navigateElements[0]).toHaveAttribute('data-to', '/login');
  });

  it('renders protected content when authenticated', () => {
    mockedUseAuth.mockReturnValue({
      user: { id: 1, username: 'tester', is_active: true, created_at: 'today' },
      loading: false,
      login: jest.fn(),
      logout: jest.fn()
    });

    render(<App />);

    expect(screen.getAllByTestId('layout').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Dashboard Component').length).toBeGreaterThan(0);
  });
});
