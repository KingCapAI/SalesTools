import api from './client';

export interface DesignQuote {
  id: string;
  design_id: string;
  quote_type: 'domestic' | 'overseas';
  quantity: number;

  // Decorations
  front_decoration: string | null;
  left_decoration: string | null;
  right_decoration: string | null;
  back_decoration: string | null;

  // Domestic
  style_number: string | null;
  shipping_speed: string | null;
  include_rope: boolean | null;
  num_dst_files: number | null;

  // Overseas
  hat_type: string | null;
  visor_decoration: string | null;
  design_addons: string[] | null;
  accessories: string[] | null;
  shipping_method: string | null;

  // Cached results
  cached_price_breaks: Array<{
    quantity_break: number;
    per_piece_price: number | null;
    total: number | null;
    [key: string]: unknown;
  }> | null;
  cached_total: number | null;
  cached_per_piece: number | null;

  created_at: string;
  updated_at: string;
}

export interface DesignQuoteCreate {
  quote_type: 'domestic' | 'overseas';
  quantity: number;
  front_decoration?: string | null;
  left_decoration?: string | null;
  right_decoration?: string | null;
  back_decoration?: string | null;

  // Domestic
  style_number?: string;
  shipping_speed?: string;
  include_rope?: boolean;
  num_dst_files?: number;

  // Overseas
  hat_type?: string;
  visor_decoration?: string | null;
  design_addons?: string[];
  accessories?: string[];
  shipping_method?: string;
}

export interface DesignQuoteUpdate {
  quantity?: number;
  front_decoration?: string | null;
  left_decoration?: string | null;
  right_decoration?: string | null;
  back_decoration?: string | null;

  // Domestic
  style_number?: string;
  shipping_speed?: string;
  include_rope?: boolean;
  num_dst_files?: number;

  // Overseas
  hat_type?: string;
  visor_decoration?: string | null;
  design_addons?: string[];
  accessories?: string[];
  shipping_method?: string;
}

export const designQuotesApi = {
  get: async (designId: string): Promise<DesignQuote | null> => {
    const response = await api.get(`/designs/${designId}/quote`);
    return response.data;
  },

  create: async (designId: string, data: DesignQuoteCreate): Promise<DesignQuote> => {
    const response = await api.post(`/designs/${designId}/quote`, data);
    return response.data;
  },

  update: async (designId: string, data: DesignQuoteUpdate): Promise<DesignQuote> => {
    const response = await api.patch(`/designs/${designId}/quote`, data);
    return response.data;
  },

  delete: async (designId: string): Promise<void> => {
    await api.delete(`/designs/${designId}/quote`);
  },

  exportWithDesign: async (designId: string, format: 'xlsx' | 'pdf' = 'xlsx'): Promise<Blob> => {
    const response = await api.get(`/designs/${designId}/quote/export`, {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  },
};
