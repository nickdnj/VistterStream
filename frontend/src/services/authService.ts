import { api } from './api';

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  username: string;
  is_active: boolean;
  created_at: string;
  recovery_email?: string | null;
}

export const authService = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
      const response = await api.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });
      console.log('AuthService: Login successful');
      return response.data;
    } catch (error) {
      console.error('AuthService: Login failed');
      throw error;
    }
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get('/auth/me');
    return response.data;
  },

  async register(username: string, password: string): Promise<User> {
    const response = await api.post('/auth/register', {
      username,
      password,
    });
    return response.data;
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },

  async setRecoveryEmail(recoveryEmail: string | null): Promise<User> {
    const response = await api.post('/auth/recovery-email', {
      recovery_email: recoveryEmail,
    });
    return response.data;
  },

  async forgotPassword(username: string): Promise<{ message: string }> {
    const response = await api.post('/auth/forgot-password', { username });
    return response.data;
  },

  async resetPassword(username: string, code: string, newPassword: string): Promise<void> {
    await api.post('/auth/reset-password', {
      username,
      code,
      new_password: newPassword,
    });
  },
};
