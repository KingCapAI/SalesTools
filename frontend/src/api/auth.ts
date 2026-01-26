import api from './client';
import type { User } from '../types/api';

export const authApi = {
  getMe: async (): Promise<User> => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
    localStorage.removeItem('token');
  },

  getMicrosoftAuthUrl: () => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    return `${apiUrl}/auth/microsoft`;
  },
};
