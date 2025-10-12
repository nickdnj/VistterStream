import axios from 'axios';

const resolveApiBaseUrl = (): string => {
  const explicitUrl = process.env.REACT_APP_API_URL;
  if (explicitUrl) {
    return explicitUrl;
  }

  if (typeof window !== 'undefined') {
    const { protocol, hostname } = window.location;
    const port = process.env.REACT_APP_API_PORT || '8000';
    const portSegment = port ? `:${port}` : '';
    return `${protocol}//${hostname}${portSegment}/api`;
  }

  return 'http://localhost:8000/api';
};

const API_BASE_URL = resolveApiBaseUrl();

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
