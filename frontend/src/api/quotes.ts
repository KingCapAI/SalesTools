import { api } from './client';

export interface DomesticQuoteRequest {
  design_number?: string;
  style_number: string;
  quantity: number;
  front_decoration?: string | null;
  left_decoration?: string | null;
  right_decoration?: string | null;
  back_decoration?: string | null;
  shipping_speed?: string;
  include_rope?: boolean;
  num_dst_files?: number;
}

export interface OverseasQuoteRequest {
  design_number?: string;
  hat_type: string;
  quantity: number;
  front_decoration?: string | null;
  left_decoration?: string | null;
  right_decoration?: string | null;
  back_decoration?: string | null;
  visor_decoration?: string | null;
  design_addons?: string[];
  accessories?: string[];
  shipping_method?: string;
}

export interface PriceBreak {
  quantity_break: number;
  blank_price: number | null;
  front_decoration_price: number | null;
  left_decoration_price: number | null;
  right_decoration_price: number | null;
  back_decoration_price: number | null;
  visor_decoration_price?: number | null;
  rush_fee?: number | null;
  rope_price?: number | null;
  addons_price?: number | null;
  accessories_price?: number | null;
  hat_subtotal?: number | null;
  shipping_price?: number | null;
  per_piece_price: number | null;
  digitizing_fee?: number | null;
  subtotal?: number | null;
  total: number | null;
}

export interface DomesticQuoteResponse {
  quote_type: 'domestic';
  style_number: string;
  style_name: string;
  collection: string;
  quantity: number;
  front_decoration: string | null;
  left_decoration: string | null;
  right_decoration: string | null;
  back_decoration: string | null;
  shipping_speed: string;
  include_rope: boolean;
  price_breaks: PriceBreak[];
}

export interface OverseasQuoteResponse {
  quote_type: 'overseas';
  hat_type: string;
  quantity: number;
  front_decoration: string | null;
  left_decoration: string | null;
  right_decoration: string | null;
  back_decoration: string | null;
  visor_decoration: string | null;
  design_addons: string[] | null;
  accessories: string[] | null;
  shipping_method: string;
  price_breaks: PriceBreak[];
}

export interface StyleInfo {
  style_number: string;
  name: string;
  collection: string;
}

export interface QuoteOptions {
  domestic: {
    quantity_breaks: number[];
    styles: StyleInfo[];
    front_decoration_methods: string[];
    additional_decoration_methods: string[];
    shipping_speeds: string[];
  };
  overseas: {
    quantity_breaks: number[];
    hat_types: string[];
    decoration_methods: string[];
    design_addons: string[];
    accessories: string[];
    shipping_methods: string[];
  };
}

export const quotesApi = {
  getOptions: async (): Promise<QuoteOptions> => {
    const response = await api.get<QuoteOptions>('/quotes/options');
    return response.data;
  },

  calculateDomestic: async (request: DomesticQuoteRequest): Promise<DomesticQuoteResponse> => {
    const response = await api.post<DomesticQuoteResponse>('/quotes/domestic', request);
    return response.data;
  },

  calculateOverseas: async (request: OverseasQuoteRequest): Promise<OverseasQuoteResponse> => {
    const response = await api.post<OverseasQuoteResponse>('/quotes/overseas', request);
    return response.data;
  },

  exportDomestic: async (request: DomesticQuoteRequest): Promise<Blob> => {
    const response = await api.post('/quotes/domestic/export', request, {
      responseType: 'blob',
    });
    return response.data;
  },

  exportOverseas: async (request: OverseasQuoteRequest): Promise<Blob> => {
    const response = await api.post('/quotes/overseas/export', request, {
      responseType: 'blob',
    });
    return response.data;
  },

  exportQuoteSheet: async (quotes: Array<{ type: string; design_number: string; request: DomesticQuoteRequest | OverseasQuoteRequest }>): Promise<Blob> => {
    const response = await api.post('/quotes/sheet/export', { quotes }, {
      responseType: 'blob',
    });
    return response.data;
  },
};
