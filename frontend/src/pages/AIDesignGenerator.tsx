import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { MultiLogoUpload } from '../components/design-generator/MultiLogoUpload';
import { BrandGuidelines } from '../components/design-generator/BrandGuidelines';
import { StyleSelector } from '../components/design-generator/StyleSelector';
import { HatStyleSelector } from '../components/design-generator/HatStyleSelector';
import { MaterialSelector } from '../components/design-generator/MaterialSelector';
import { useCreateDesign } from '../hooks/useDesigns';
import { ArrowLeft, Sparkles } from 'lucide-react';
import type { HatStyle, Material, StyleDirection, BrandScrapedData, HatStructure, ClosureType, DesignLogoCreate } from '../types/api';

interface UploadedAsset {
  id: string;
  type: string;
  file_name: string;
  file_path: string;
}

export function AIDesignGenerator() {
  const navigate = useNavigate();
  const createDesign = useCreateDesign();

  // Form state - simplified to text fields
  const [customerName, setCustomerName] = useState('');
  const [brandName, setBrandName] = useState('');
  const [designName, setDesignName] = useState('');
  const [logos, setLogos] = useState<DesignLogoCreate[]>([]);
  const [uploadedAssets, setUploadedAssets] = useState<UploadedAsset[]>([]);
  const [scrapedData, setScrapedData] = useState<BrandScrapedData | null>(null);
  const [hatStyle, setHatStyle] = useState<HatStyle>('6-panel-hat');
  const [material, setMaterial] = useState<Material>('cotton-twill');
  const [styleDirections, setStyleDirections] = useState<StyleDirection[]>(['modern']);
  const [customDescription, setCustomDescription] = useState('');
  const [manualGuidelines, setManualGuidelines] = useState('');
  const [structure, setStructure] = useState<HatStructure | ''>('');
  const [closure, setClosure] = useState<ClosureType | ''>('');

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
              <h1 className="text-2xl font-bold text-gray-100">Create New Design</h1>
              <p className="text-gray-400">Generate a custom hat design using AI</p>
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
