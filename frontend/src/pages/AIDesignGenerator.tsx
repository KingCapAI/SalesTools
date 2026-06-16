import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { MultiLogoUpload } from '../components/design-generator/MultiLogoUpload';
import { BrandGuidelines } from '../components/design-generator/BrandGuidelines';
import { StyleSelector } from '../components/design-generator/StyleSelector';
import { HatStyleSelector } from '../components/design-generator/HatStyleSelector';
import { MaterialSelector } from '../components/design-generator/MaterialSelector';
import { ReferenceHatUpload } from '../components/custom-design/ReferenceHatUpload';
import { useCreateDesign } from '../hooks/useDesigns';
import { ArrowLeft, Sparkles } from 'lucide-react';
import { clsx } from 'clsx';
import type { HatStyle, Material, StyleDirection, BrandScrapedData, HatStructure, ClosureType, DesignLogoCreate, ReferenceMatchMode } from '../types/api';

interface UploadedAsset {
  id: string;
  type: string;
  file_name: string;
  file_path: string;
}

interface PrefillData {
  customerName?: string;
  brandName?: string;
  designName?: string;
  hatStyle?: string;
  material?: string;
  structure?: string;
  closure?: string;
  styleDirections?: string[];
  customDescription?: string;
  logos?: DesignLogoCreate[];
  referenceImagePath?: string | null;
  referenceMatchMode?: ReferenceMatchMode;
  remixedFromDesignId?: string;
}

export function AIDesignGenerator() {
  const navigate = useNavigate();
  const location = useLocation();
  const createDesign = useCreateDesign();

  // Check for pre-filled data from "Copy & Edit"
  const prefill: PrefillData | undefined = (location.state as any)?.prefill;

  // Form state — initialized from prefill if available
  const [customerName, setCustomerName] = useState(prefill?.customerName || '');
  const [brandName, setBrandName] = useState(prefill?.brandName || '');
  const [designName, setDesignName] = useState(prefill?.designName || '');
  const [logos, setLogos] = useState<DesignLogoCreate[]>(prefill?.logos || []);
  const [uploadedAssets, setUploadedAssets] = useState<UploadedAsset[]>([]);
  const [scrapedData, setScrapedData] = useState<BrandScrapedData | null>(null);
  const [hatStyle, setHatStyle] = useState<HatStyle>((prefill?.hatStyle as HatStyle) || '6-panel-hat');
  const [material, setMaterial] = useState<Material>((prefill?.material as Material) || 'cotton-twill');
  const [styleDirections, setStyleDirections] = useState<StyleDirection[]>(
    (prefill?.styleDirections as StyleDirection[]) || ['modern']
  );
  const [customDescription, setCustomDescription] = useState(prefill?.customDescription || '');
  const [manualGuidelines, setManualGuidelines] = useState('');
  const [structure, setStructure] = useState<HatStructure | ''>((prefill?.structure as HatStructure) || '');
  const [closure, setClosure] = useState<ClosureType | ''>((prefill?.closure as ClosureType) || '');
  const [referenceImagePath, setReferenceImagePath] = useState<string | null>(prefill?.referenceImagePath || null);
  const [referenceMatchMode, setReferenceMatchMode] = useState<ReferenceMatchMode>(prefill?.referenceMatchMode || 'inspiration');

  const handleAssetUpload = (asset: UploadedAsset) => {
    setUploadedAssets((prev) => [...prev, asset]);
  };

  const handleAssetRemove = (id: string) => {
    setUploadedAssets((prev) => prev.filter((a) => a.id !== id));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!customerName.trim()) {
      alert('Please enter a customer name');
      return;
    }

    if (!brandName.trim()) {
      alert('Please enter a brand name');
      return;
    }

    if (logos.length === 0) {
      alert('Please upload at least one brand logo');
      return;
    }

    if (styleDirections.length === 0) {
      alert('Please select at least one style direction');
      return;
    }

    if (styleDirections.includes('describe-below') && !customDescription.trim()) {
      alert('Please describe the style in the description box');
      return;
    }

    try {
      const design = await createDesign.mutateAsync({
        customer_name: customerName.trim(),
        brand_name: brandName.trim(),
        design_name: designName.trim() || undefined,
        hat_style: hatStyle,
        material: material,
        structure: structure || undefined,
        closure: closure || undefined,
        style_directions: styleDirections,
        custom_description: customDescription.trim() || undefined,
        logos: logos,
        reference_image_path: referenceImagePath || undefined,
        reference_match_mode: referenceImagePath ? referenceMatchMode : undefined,
      });

      // Navigate to design detail page
      navigate(`/ai-design-generator/design/${design.id}`);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to create design');
    }
  };

  return (
    <div className="min-h-screen bg-black">
      <Header />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/ai-design-generator">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-100">
                {prefill ? 'Edit & Resubmit Design' : 'Create New Design'}
              </h1>
              <p className="text-gray-400">
                {prefill
                  ? 'Modify any inputs below and generate a new design'
                  : 'Generate a custom hat design using AI'}
              </p>
            </div>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Customer & Brand Section */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">Customer & Brand Information</h2>
            <div className="space-y-6">
              <Input
                label="Customer Name"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="e.g., Acme Corporation"
                required
              />

              <Input
                label="Brand Name"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                placeholder="e.g., Acme Golf, Acme Sports"
                required
              />

              <Input
                label="Design Name (Optional)"
                value={designName}
                onChange={(e) => setDesignName(e.target.value)}
                placeholder="e.g., Summer Collection Cap, Golf Event Hat"
              />
            </div>
          </div>

          {/* Brand Assets Section */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">Brand Assets</h2>
            <div className="space-y-6">
              <MultiLogoUpload
                logos={logos}
                onChange={setLogos}
              />

              <BrandGuidelines
                brandName={brandName}
                uploadedAssets={uploadedAssets}
                onAssetUpload={handleAssetUpload}
                onAssetRemove={handleAssetRemove}
                scrapedData={scrapedData}
                onScrape={setScrapedData}
                manualGuidelines={manualGuidelines}
                onManualGuidelinesChange={setManualGuidelines}
              />
            </div>
          </div>

          {/* Reference Image Section (optional) */}
          <div className="card">
            <ReferenceHatUpload
              value={referenceImagePath}
              onChange={setReferenceImagePath}
              title="Reference Image (Optional)"
              description="Upload an existing hat, design, or image you want to riff on. The AI will use it as a starting point."
            />

            {referenceImagePath && (
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  How should the AI use this reference?
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setReferenceMatchMode('inspiration')}
                    className={clsx(
                      'p-4 rounded-lg border text-left transition-all',
                      referenceMatchMode === 'inspiration'
                        ? 'border-primary-500 bg-primary-900/30 ring-2 ring-primary-500'
                        : 'border-gray-700 hover:border-gray-600 bg-gray-800'
                    )}
                  >
                    <div className="font-medium text-gray-100">Use as inspiration</div>
                    <div className="text-xs text-gray-400 mt-1">
                      Borrow mood, palette, and vibe — fresh composition
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setReferenceMatchMode('close')}
                    className={clsx(
                      'p-4 rounded-lg border text-left transition-all',
                      referenceMatchMode === 'close'
                        ? 'border-primary-500 bg-primary-900/30 ring-2 ring-primary-500'
                        : 'border-gray-700 hover:border-gray-600 bg-gray-800'
                    )}
                  >
                    <div className="font-medium text-gray-100">Match closely</div>
                    <div className="text-xs text-gray-400 mt-1">
                      Reproduce silhouette + placements; swap in the brand's logos
                    </div>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Design Options Section */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">Design Options</h2>
            <div className="space-y-6">
              <StyleSelector
                value={styleDirections}
                onChange={setStyleDirections}
                customDescription={customDescription}
                onCustomDescriptionChange={setCustomDescription}
              />

              <HatStyleSelector value={hatStyle} onChange={setHatStyle} />

              <MaterialSelector value={material} onChange={setMaterial} />

              {/* Optional Structure & Closure */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Structure (Optional)</label>
                  <select
                    value={structure}
                    onChange={(e) => setStructure(e.target.value as HatStructure | '')}
                    className="input w-full"
                  >
                    <option value="">Let AI decide</option>
                    <option value="structured">Structured (stiff front panels)</option>
                    <option value="unstructured">Unstructured (soft, relaxed crown)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Closure (Optional)</label>
                  <select
                    value={closure}
                    onChange={(e) => setClosure(e.target.value as ClosureType | '')}
                    className="input w-full"
                  >
                    <option value="">Let AI decide</option>
                    <option value="snapback">Snapback</option>
                    <option value="metal_slider_buckle">Metal Slider Buckle</option>
                    <option value="velcro_strap">Velcro Strap</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex justify-end">
            <Button
              type="submit"
              size="lg"
              isLoading={createDesign.isPending}
              disabled={!customerName.trim() || !brandName.trim() || logos.length === 0 || styleDirections.length === 0}
            >
              <Sparkles className="w-5 h-5 mr-2" />
              Generate Design
            </Button>
          </div>
        </form>
      </main>
    </div>
  );
}
