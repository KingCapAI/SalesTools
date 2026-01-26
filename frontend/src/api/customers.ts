import api from './client';
import type { Customer, CustomerList, CustomerCreate } from '../types/api';

export const customersApi = {
  list: async (search?: string): Promise<CustomerList[]> => {
    const params = search ? { search } : {};
    const response = await api.get('/customers', { params });
    return response.data;
  },

  get: async (id: string): Promise<Customer> => {
    const response = await api.get(`/customers/${id}`);
    return response.data;
  },

  create: async (data: CustomerCreate): Promise<Customer> => {
    const response = await api.post('/customers', data);
    return response.data;
  },

  update: async (id: string, data: Partial<CustomerCreate>): Promise<Customer> => {
    const response = await api.put(`/customers/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/customers/${id}`);
  },
};
