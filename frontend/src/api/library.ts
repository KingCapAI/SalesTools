import api from './client';
import type { Industry, LibraryDesignListItem, IndustryCount, LibraryRemixData } from '../types/api';

export const libraryApi = {
  list: async (industry?: string): Promise<LibraryDesignListItem[]> => {
    const response = await api.get('/library/designs', {
      params: industry && industry !== 'all' ? { industry } : undefined,
    });
    return response.data;
  },

  industries: async (): Promise<IndustryCount[]> => {
    const response = await api.get('/library/industries');
    return response.data;
  },

  publish: async (designId: string, industries: Industry[]): Promise<void> => {
    await api.post(`/library/designs/${designId}/publish`, { industries });
  },

  unpublish: async (designId: string): Promise<void> => {
    await api.post(`/library/designs/${designId}/unpublish`);
  },

  remixData: async (designId: string): Promise<LibraryRemixData> => {
    const response = await api.get(`/library/designs/${designId}/remix-data`);
    return response.data;
  },
};
