import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders login page when not authenticated', () => {
  render(<App />);
  // The app should show a login form when not authenticated
  const loginElement = screen.getByRole('button', { name: /sign in/i });
  expect(loginElement).toBeInTheDocument();
});
