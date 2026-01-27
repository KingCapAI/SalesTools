// API Response types

export interface User {
  id: string;
  email: string;
  name: string;
  image?: string;
  team_id?: string;
  team?: Team;
  role: string;
  provider: string;
  created_at: string;
  last_login_at?: string;
}

export interface Team {
  id: string;
  name: string;
  allowed_apps: string[];
}

export interface Customer {
  id: string;
  name: string;
  contact_email?: string;
  contact_phone?: string;
  notes?: string;
  created_by_id?: string;
  created_at: string;
  updated_at: string;
  brands?: Brand[];
}

export interface CustomerList {
  id: string;
  name: string;
  contact_email?: string;
  created_at: string;
}

export interface Brand {
  id: string;
  customer_id: string;
  name: string;
  website?: string;
  created_by_id?: string;
  created_at: string;
  updated_at: string;
  brand_assets?: BrandAsset[];
}

export interface BrandList {
  id: string;
  customer_id: string;
  name: string;
  website?: string;
  created_at: string;
}

export interface BrandAsset {
  id: string;
  type: string;
  file_name?: string;
  file_path?: string;
  mime_type?: string;
  scraped_data?: BrandScrapedData;
  created_at: string;
}

export interface BrandScrapedData {
  primary_colors?: string[];
  secondary_colors?: string[];
  brand_style?: string;
  typography?: string;
  design_aesthetic?: string;
  target_audience?: string;
  industry?: string;
  brand_elements?: string[];
  recommendations?: string;
}

export interface Design {
  id: string;
  customer_name: string;
  brand_name: string;
  design_name?: string;
  design_number: number;
  current_version: number;
  hat_style: string;
  material: string;
  style_directions: string[];
  custom_description?: string;
  status: string;
  approval_status: ApprovalStatus;
  shared_with_team: boolean;
  created_by_id?: string;
  created_at: string;
  updated_at: string;
  versions: DesignVersion[];
  chats: DesignChat[];
}

export interface DesignVersion {
  id: string;
  design_id: string;
  version_number: number;
  prompt: string;
  image_path?: string;
  image_url?: string;
  generation_status: string;
  error_message?: string;
  created_at: string;
}

export interface DesignChat {
  id: string;
  design_id: string;
  version_id?: string;
  message: string;
  is_user: boolean;
  user_id?: string;
  created_at: string;
}

export interface DesignListItem {
  id: string;
  customer_name: string;
  brand_name: string;
  design_name?: string;
  design_number: number;
  current_version: number;
  hat_style: string;
  material: string;
  style_directions: string[];
  status: string;
  approval_status: ApprovalStatus;
  shared_with_team: boolean;
  created_at: string;
  updated_at: string;
  latest_image_path?: string;
}

// Request types
export interface CustomerCreate {
  name: string;
  contact_email?: string;
  contact_phone?: string;
  notes?: string;
}

export interface BrandCreate {
  customer_id: string;
  name: string;
  website?: string;
}

export interface DesignCreate {
  customer_name: string;
  brand_name: string;
  design_name?: string;
  hat_style: HatStyle;
  material: Material;
  style_directions: StyleDirection[];
  custom_description?: string;
  logo_path?: string;
}

export interface DesignUpdate {
  design_name?: string;
  approval_status?: ApprovalStatus;
  shared_with_team?: boolean;
}

export interface RevisionCreate {
  revision_notes: string;
}

// Enums
export type HatStyle =
  | '6-panel-hat'
  | '6-panel-trucker'
  | '5-panel-hat'
  | '5-panel-trucker'
  | 'perforated-6-panel'
  | 'perforated-5-panel';

export type Material =
  | 'cotton-twill'
  | 'performance-polyester'
  | 'nylon'
  | 'canvas';

export type StyleDirection =
  | 'simple'
  | 'modern'
  | 'luxurious'
  | 'sporty'
  | 'rugged'
  | 'retro'
  | 'collegiate';

export type ApprovalStatus = 'pending' | 'approved' | 'rejected';
