import axios from 'axios';

const resolveApiBaseUrl = (): string => {
  const explicitUrl = process.env.REACT_APP_API_URL;
  if (explicitUrl) {
    return explicitUrl;
  }

  if (typeof window !== 'undefined') {
    const { protocol, hostname, port } = window.location;
    // For HTTPS (Cloudflare Tunnel), don't add port segment
    // For HTTP, use the current port or default to 8000 for local development
    const portSegment = (protocol === 'https:' || !port || port === '443' || port === '80') 
      ? '' 
      : `:${port}`;
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
