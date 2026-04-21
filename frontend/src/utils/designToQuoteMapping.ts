/**
 * Maps design data to quote form defaults.
 * Used to auto-populate the QuoteModal when opened from a design detail page.
 */

import type { Design, CustomDesign, DesignVersion } from '../types/api';

interface DomesticDefaults {
  style_number?: string;
  front_decoration?: string | null;
  left_decoration?: string | null;
  right_decoration?: string | null;
  back_decoration?: string | null;
}

interface OverseasDefaults {
  hat_type?: string;
  front_decoration?: string | null;
  left_decoration?: string | null;
  right_decoration?: string | null;
  back_decoration?: string | null;
  visor_decoration?: string | null;
}

export interface QuoteDefaults {
  domestic: DomesticDefaults;
  overseas: OverseasDefaults;
}

// --- Hat Style Mappings ---

// Design hat_style + material -> best domestic style_number
const DOMESTIC_STYLE_MAP: Record<string, Record<string, string>> = {
  '6-panel-hat': {
    'cotton-twill': '260',
    'performance-polyester': '360',
    'nylon': '460',
    'canvas': '260',
  },
  '6-panel-trucker': {
    'cotton-twill': '260-T',
    'performance-polyester': '360-T',
    'nylon': '260-T',
    'canvas': '260-T',
  },
  '5-panel-hat': {
    'cotton-twill': '100',
    'performance-polyester': '450',
    'nylon': '450',
    'canvas': '100',
  },
  '5-panel-trucker': {
    'cotton-twill': '150-FT',
    'performance-polyester': '150-FT',
    'nylon': '150-FT',
    'canvas': '150-FT',
  },
  'perforated-6-panel': {
    'performance-polyester': '460-P',
    'cotton-twill': '460-P',
    'nylon': '460-P',
    'canvas': '460-P',
  },
  'perforated-5-panel': {
    'performance-polyester': '450-P',
    'cotton-twill': '450-P',
    'nylon': '450-P',
    'canvas': '450-P',
  },
};

// Design hat_style -> overseas hat_type
const OVERSEAS_TYPE_MAP: Record<string, string> = {
  '6-panel-hat': 'Classic',
  '6-panel-trucker': 'Classic',
  '5-panel-hat': 'Basic',
  '5-panel-trucker': 'Basic',
  'perforated-6-panel': 'Sport',
  'perforated-5-panel': 'Sport',
};

// --- Decoration Method Mappings ---

// AI-detected decoration labels -> domestic quote decoration names
const DOMESTIC_DECORATION_MAP: Record<string, string> = {
  'flat embroidery': 'Flat Embroidery',
  '3d embroidery': '3D Embroidery',
  '3d puff embroidery': '3D Embroidery',
  'heat transfer': 'Heat Transfer',
  'faux leather patch': 'Faux Leather Laser Patch',
  'faux leather laser patch': 'Faux Leather Laser Patch',
  'flat embroidery (metallic thread)': 'Flat Embroidery (Metallic Thread)',
  '3d embroidery (metallic thread)': '3D Embroidery (Metallic Thread)',
};

// AI-detected decoration labels -> overseas quote decoration names
const OVERSEAS_DECORATION_MAP: Record<string, string> = {
  'flat embroidery': 'Flat Embroidery',
  '3d embroidery': '3D Embroidery',
  '3d puff embroidery': '3D Embroidery',
  'sublimated patch': 'Sublimated Patch',
  'sublimated print': 'Sublimated Patch',
  'woven patch': 'Woven Patch',
  'embroidered patch': 'Embroidered Patch',
  'leather patch': 'Leather Patch',
  'suede patch': 'Suede Patch',
  'pvc patch': 'PVC Patch',
  'mesh patch': 'Mesh Patch',
  'distressed patch': 'Distressed Patch',
  'heat transfer': 'Heat Transfer',
  'high density print': 'High Density Print',
  'tpu heat transfer': 'TPU Heat Transfer',
  'metallic heat transfer': 'Metallic Heat Transfer',
  'flocking heat transfer': 'Flocking Heat Transfer',
  'ai embroidery': 'AI Embroidery',
  '3d + flat embroidery': '3D + Flat Embroidery',
  'faux leather patch': 'Leather Patch',
  'faux leather laser patch': 'Leather Patch',
};

// CustomDesign decoration_method enum -> domestic decoration name
const CUSTOM_TO_DOMESTIC_MAP: Record<string, string> = {
  embroidery: 'Flat Embroidery',
  '3d_puff': '3D Embroidery',
  heat_transfer: 'Heat Transfer',
  laser_cut: 'Faux Leather Laser Patch',
  patch: 'Faux Leather Laser Patch',
};

// CustomDesign decoration_method enum -> overseas decoration name
const CUSTOM_TO_OVERSEAS_MAP: Record<string, string> = {
  embroidery: 'Flat Embroidery',
  '3d_puff': '3D Embroidery',
  heat_transfer: 'Heat Transfer',
  laser_cut: 'Leather Patch',
  sublimation: 'Sublimated Patch',
  screen_print: 'High Density Print',
  patch: 'Embroidered Patch',
};


function mapDetectedDecorations(
  detected: Record<string, string>,
  decorationMap: Record<string, string>
): {
  front: string | null;
  left: string | null;
  right: string | null;
  back: string | null;
  visor: string | null;
} {
  const result = { front: null as string | null, left: null as string | null, right: null as string | null, back: null as string | null, visor: null as string | null };

  for (const [location, method] of Object.entries(detected)) {
    const key = location.toLowerCase().trim();
    const mapped = decorationMap[method.toLowerCase().trim()] || null;
    if (!mapped) continue;

    if (key === 'front' || key === 'front center' || key === 'front panel') {
      result.front = mapped;
    } else if (key === 'left' || key === 'left side') {
      result.left = mapped;
    } else if (key === 'right' || key === 'right side') {
      result.right = mapped;
    } else if (key === 'back' || key === 'back panel') {
      result.back = mapped;
    } else if (key === 'underbill' || key === 'visor' || key === 'underbrim') {
      result.visor = mapped;
    }
  }

  return result;
}


/**
 * Map an AI Design to quote defaults.
 * Uses detected_decorations from the selected version if available.
 */
export function mapAIDesignToQuote(design: Design, selectedVersion?: DesignVersion | null): QuoteDefaults {
  const hatStyle = design.hat_style || '';
  const material = design.material || '';

  // Hat style mapping
  const domesticStyle = DOMESTIC_STYLE_MAP[hatStyle]?.[material] || DOMESTIC_STYLE_MAP[hatStyle]?.['cotton-twill'] || '';
  const overseasType = OVERSEAS_TYPE_MAP[hatStyle] || 'Classic';

  // Decoration mapping from detected_decorations
  let domesticDecorations = { front: null as string | null, left: null as string | null, right: null as string | null, back: null as string | null, visor: null as string | null };
  let overseasDecorations = { ...domesticDecorations };

  if (selectedVersion?.detected_decorations) {
    try {
      const detected = JSON.parse(selectedVersion.detected_decorations);
      domesticDecorations = mapDetectedDecorations(detected, DOMESTIC_DECORATION_MAP);
      overseasDecorations = mapDetectedDecorations(detected, OVERSEAS_DECORATION_MAP);
    } catch {
      // Ignore parse errors
    }
  }

  return {
    domestic: {
      style_number: domesticStyle,
      front_decoration: domesticDecorations.front,
      left_decoration: domesticDecorations.left,
      right_decoration: domesticDecorations.right,
      back_decoration: domesticDecorations.back,
    },
    overseas: {
      hat_type: overseasType,
      front_decoration: overseasDecorations.front,
      left_decoration: overseasDecorations.left,
      right_decoration: overseasDecorations.right,
      back_decoration: overseasDecorations.back,
      visor_decoration: overseasDecorations.visor,
    },
  };
}


/**
 * Map a Custom Design (Mockup Builder) to quote defaults.
 * Uses the per-location decoration methods directly from location_logos.
 */
export function mapCustomDesignToQuote(design: CustomDesign): QuoteDefaults {
  const hatStyle = design.hat_style || '';
  const material = design.material || '';

  const domesticStyle = DOMESTIC_STYLE_MAP[hatStyle]?.[material] || DOMESTIC_STYLE_MAP[hatStyle]?.['cotton-twill'] || '';
  const overseasType = OVERSEAS_TYPE_MAP[hatStyle] || 'Classic';

  const domestic: DomesticDefaults = { style_number: domesticStyle };
  const overseas: OverseasDefaults = { hat_type: overseasType };

  // Map location_logos decoration methods
  for (const logo of design.location_logos || []) {
    const loc = logo.location;
    const domesticMethod = CUSTOM_TO_DOMESTIC_MAP[logo.decoration_method] || null;
    const overseasMethod = CUSTOM_TO_OVERSEAS_MAP[logo.decoration_method] || null;

    if (loc === 'front') {
      domestic.front_decoration = domesticMethod;
      overseas.front_decoration = overseasMethod;
    } else if (loc === 'left') {
      domestic.left_decoration = domesticMethod;
      overseas.left_decoration = overseasMethod;
    } else if (loc === 'right') {
      domestic.right_decoration = domesticMethod;
      overseas.right_decoration = overseasMethod;
    } else if (loc === 'back') {
      domestic.back_decoration = domesticMethod;
      overseas.back_decoration = overseasMethod;
    } else if (loc === 'visor') {
      overseas.visor_decoration = overseasMethod;
    }
  }

  return { domestic, overseas };
}
