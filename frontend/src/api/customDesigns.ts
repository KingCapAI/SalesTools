import api from './client';
import type {
  CustomDesign,
  CustomDesignListItem,
  CustomDesignCreate,
  CustomDesignUpdate,
  DesignVersion,
  DesignChat,
  RevisionCreate,
  LocationLogoUploadResponse,
  ReferenceHatUploadResponse,
  DecorationLocation,
} from '../types/api';

export interface CustomDesignFilters {
  brand_name?: string;
  customer_name?: string;
  approval_status?: string;
  include_shared?: boolean;
  start_date?: string;
  end_date?: string;
  skip?: number;
  limit?: number;
}

export const customDesignsApi = {
  list: async (filters?: CustomDesignFilters): Promise<CustomDesignListItem[]> => {
    const response = await api.get('/custom-designs', { params: filters });
    return response.data;
  },

  get: async (id: string): Promise<CustomDesign> => {
    const response = await api.get(`/custom-designs/${id}`);
    return response.data;
  },

  create: async (data: CustomDesignCreate): Promise<CustomDesign> => {
    const response = await api.post('/custom-designs', data);
    return response.data;
  },

  update: async (id: string, data: CustomDesignUpdate): Promise<CustomDesign> => {
    const response = await api.patch(`/custom-designs/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/custom-designs/${id}`);
  },

  regenerate: async (id: string): Promise<DesignVersion> => {
    const response = await api.post(`/custom-designs/${id}/generate`);
    return response.data;
  },

  getVersions: async (designId: string): Promise<DesignVersion[]> => {
    const response = await api.get(`/custom-designs/${designId}/versions`);
    return response.data;
  },

  createRevision: async (designId: string, data: RevisionCreate): Promise<DesignVersion> => {
    const response = await api.post(`/custom-designs/${designId}/versions`, data);
    return response.data;
  },

  getChat: async (designId: string): Promise<DesignChat[]> => {
    const response = await api.get(`/custom-designs/${designId}/chat`);
    return response.data;
  },

  addChat: async (designId: string, message: string): Promise<DesignChat> => {
    const response = await api.post(`/custom-designs/${designId}/chat`, { message });
    return response.data;
  },

  // Upload endpoints
  uploadLocationLogo: async (
    file: File,
    location: DecorationLocation
  ): Promise<LocationLogoUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/custom-designs/upload/location-logo', formData, {
      params: { location },
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  uploadReferenceHat: async (file: File): Promise<ReferenceHatUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/custom-designs/upload/reference-hat', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};
