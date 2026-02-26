import api from './client';
import type { Design, DesignListItem, DesignCreate, DesignUpdate, DesignVersion, DesignChat, RevisionCreate } from '../types/api';

export interface DesignFilters {
  brand_name?: string;
  customer_name?: string;
  approval_status?: string;
  shared_with_team?: boolean;
  created_by_id?: string;
  start_date?: string;
  end_date?: string;
  skip?: number;
  limit?: number;
}

export const designsApi = {
  list: async (filters?: DesignFilters): Promise<DesignListItem[]> => {
    const response = await api.get('/designs', { params: filters });
    return response.data;
  },

  get: async (id: string): Promise<Design> => {
    const response = await api.get(`/designs/${id}`);
    return response.data;
  },

  create: async (data: DesignCreate): Promise<Design> => {
    const response = await api.post('/designs', data);
    return response.data;
  },

  update: async (id: string, data: DesignUpdate): Promise<Design> => {
    const response = await api.patch(`/designs/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/designs/${id}`);
  },

  getVersions: async (designId: string): Promise<DesignVersion[]> => {
    const response = await api.get(`/designs/${designId}/versions`);
    return response.data;
  },

  createRevision: async (designId: string, data: RevisionCreate): Promise<DesignVersion> => {
    const response = await api.post(`/designs/${designId}/versions`, data);
    return response.data;
  },

  getChat: async (designId: string): Promise<DesignChat[]> => {
    const response = await api.get(`/designs/${designId}/chat`);
    return response.data;
  },

  addChat: async (designId: string, message: string): Promise<DesignChat> => {
    const response = await api.post(`/designs/${designId}/chat`, { message });
    return response.data;
  },

  regenerate: async (designId: string): Promise<DesignVersion[]> => {
    const response = await api.post(`/designs/${designId}/regenerate`);
    return response.data;
  },

  selectVersion: async (designId: string, versionId: string): Promise<void> => {
    await api.post(`/designs/${designId}/versions/${versionId}/select`);
  },

  duplicate: async (designId: string): Promise<Design> => {
    const response = await api.post(`/designs/${designId}/duplicate`);
    return response.data;
  },
};
