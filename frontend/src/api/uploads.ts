import api from './client';

export interface UploadResponse {
  file_path: string;
  file_url: string;
  mime_type: string;
  file_size: number;
  asset_type?: string;
}

export const uploadsApi = {
  // Upload logo for design generation (not linked to brand entity)
  uploadDesignLogo: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/upload/design-logo', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Upload brand asset for design generation (not linked to brand entity)
  uploadDesignAsset: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/upload/design-asset', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getFileUrl: (path: string): string => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    return `${apiUrl}/uploads/${path}`;
  },
};
