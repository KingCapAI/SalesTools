import api from './client';
import type { BrandScrapedData } from '../types/api';

export interface BrandScrapeRequest {
  brand_name?: string;
  brand_url?: string;
  logo_path?: string;
}

export interface BrandScrapeResponse {
  success: boolean;
  data: BrandScrapedData;
  message?: string;
}

export const aiApi = {
  scrapeBrand: async (data: BrandScrapeRequest): Promise<BrandScrapeResponse> => {
    const response = await api.post('/ai/brand-scrape', data);
    return response.data;
  },
};
