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
}

export const authService = {
  async login(username: string, password: string): Promise<LoginResponse> {
    console.log('AuthService: Starting login for username:', username);
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    console.log('AuthService: Making API call to /auth/login');
    try {
      const response = await api.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });
      console.log('AuthService: Login successful, response:', response.data);
      return response.data;
    } catch (error) {
      console.error('AuthService: Login failed with error:', error);
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
};
