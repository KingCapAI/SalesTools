import api from './client';
import type { Brand, BrandList, BrandCreate } from '../types/api';

export const brandsApi = {
  list: async (customerId?: string, search?: string): Promise<BrandList[]> => {
    const params: Record<string, string> = {};
    if (customerId) params.customer_id = customerId;
    if (search) params.search = search;
    const response = await api.get('/brands', { params });
    return response.data;
  },

  get: async (id: string): Promise<Brand> => {
    const response = await api.get(`/brands/${id}`);
    return response.data;
  },

  create: async (data: BrandCreate): Promise<Brand> => {
    const response = await api.post('/brands', data);
    return response.data;
  },

  update: async (id: string, data: Partial<BrandCreate>): Promise<Brand> => {
    const response = await api.put(`/brands/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/brands/${id}`);
  },
};
