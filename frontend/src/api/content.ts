import api from './client';

export interface SiteContentResponse<T = unknown> {
  key: string;
  data: T;
  updated_at?: string | null;
  updated_by?: string | null;
  can_edit: boolean;
}

export const contentApi = {
  get: async <T,>(key: string): Promise<SiteContentResponse<T>> => {
    const res = await api.get(`/content/${key}`);
    return res.data;
  },
  update: async <T,>(key: string, data: T): Promise<SiteContentResponse<T>> => {
    const res = await api.put(`/content/${key}`, { data });
    return res.data;
  },
  reset: async <T,>(key: string): Promise<SiteContentResponse<T>> => {
    const res = await api.post(`/content/${key}/reset`);
    return res.data;
  },
};
