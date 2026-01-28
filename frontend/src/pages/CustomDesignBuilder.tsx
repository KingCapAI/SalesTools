import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { HatStyleSelector } from '../components/design-generator/HatStyleSelector';
import { MaterialSelector } from '../components/design-generator/MaterialSelector';
import { LocationLogoUpload } from '../components/custom-design/LocationLogoUpload';
import { ReferenceHatUpload } from '../components/custom-design/ReferenceHatUpload';
import { useCreateCustomDesign } from '../hooks/useCustomDesigns';
import { ArrowLeft, Sparkles, Layers } from 'lucide-react';
import type { HatStyle, Material, DecorationLocation, LocationLogoCreate } from '../types/api';

const LOCATIONS: DecorationLocation[] = ['front', 'left', 'right', 'back', 'visor'];

export function CustomDesignBuilder() {
  const navigate = useNavigate();
  const createCustomDesign = useCreateCustomDesign();

  // Form state
  const [customerName, setCustomerName] = useState('');
  const [brandName, setBrandName] = useState('');
  const [designName, setDesignName] = useState('');
  const [hatStyle, setHatStyle] = useState<HatStyle>('6-panel-hat');
  const [material, setMaterial] = useState<Material>('cotton-twill');
  const [referenceHatPath, setReferenceHatPath] = useState<string | null>(null);

  // Location logos state - keyed by location
  const [locationLogos, setLocationLogos] = useState<Record<DecorationLocation, Partial<LocationLogoCreate> | null>>({
    front: null,
    left: null,
    right: null,
    back: null,
    visor: null,
  });

  const handleLocationLogoChange = (location: DecorationLocation, value: Partial<LocationLogoCreate> | null) => {
    setLocationLogos((prev) => ({ ...prev, [location]: value }));
  };

  // Get valid location logos (those with all required fields)
  const getValidLocationLogos = (): LocationLogoCreate[] => {
    return Object.entries(locationLogos)
      .filter(([_, logo]) => logo?.logo_path && logo?.logo_filename && logo?.decoration_method && logo?.size)
      .map(([_, logo]) => logo as LocationLogoCreate);
  };

  const validLogos = getValidLocationLogos();
  const hasAtLeastOneLogo = validLogos.length > 0;

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

    if (!hasAtLeastOneLogo) {
      alert('Please upload at least one logo');
      return;
    }

    try {
      const design = await createCustomDesign.mutateAsync({
        customer_name: customerName.trim(),
        brand_name: brandName.trim(),
        design_name: designName.trim() || undefined,
        hat_style: hatStyle,
        material: material,
        reference_hat_path: referenceHatPath || undefined,
        location_logos: validLogos,
      });

      // Navigate to design detail page
      navigate(`/custom-design-builder/design/${design.id}`);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to create design');
    }
  };

  return (
    <div className="min-h-screen bg-black">
      <Header />

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/custom-design-builder">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <Layers className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-100">Custom Design Builder</h1>
                <p className="text-gray-400">Build a hat design with specific logos and placements</p>
              </div>
            </div>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Customer & Brand Section */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">Customer & Brand Information</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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

              <div className="md:col-span-2">
                <Input
                  label="Design Name (Optional)"
                  value={designName}
                  onChange={(e) => setDesignName(e.target.value)}
                  placeholder="e.g., Summer Collection Cap, Golf Event Hat"
                />
              </div>
            </div>
          </div>

          {/* Hat Style & Material Section */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">Hat Style & Material</h2>
            <div className="space-y-6">
              <HatStyleSelector value={hatStyle} onChange={setHatStyle} />
              <MaterialSelector value={material} onChange={setMaterial} />
            </div>
          </div>

          {/* Reference Hat Section */}
          <div className="card">
            <ReferenceHatUpload
              value={referenceHatPath}
              onChange={setReferenceHatPath}
            />
          </div>

          {/* Decoration Locations Section */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-100 mb-2">Decoration Locations</h2>
            <p className="text-sm text-gray-400 mb-6">
              Upload logos for each location you want decorated. Each location can have its own logo, decoration method, and size.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {LOCATIONS.map((location) => (
                <LocationLogoUpload
                  key={location}
                  location={location}
                  value={locationLogos[location]}
                  onChange={(value) => handleLocationLogoChange(location, value)}
                />
              ))}
            </div>

            {!hasAtLeastOneLogo && (
              <p className="text-sm text-amber-400 mt-4">
                Please upload at least one logo to continue.
              </p>
            )}
          </div>

          {/* Summary & Submit */}
          <div className="card bg-gray-800/50">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium text-white">Ready to Generate</h3>
                <p className="text-sm text-gray-400">
                  {validLogos.length} logo{validLogos.length !== 1 ? 's' : ''} will be placed on the hat
                  {referenceHatPath && ' • Reference hat provided'}
                </p>
              </div>
              <Button
                type="submit"
                size="lg"
                isLoading={createCustomDesign.isPending}
                disabled={!customerName.trim() || !brandName.trim() || !hasAtLeastOneLogo}
              >
                <Sparkles className="w-5 h-5 mr-2" />
                Generate Design
              </Button>
            </div>
          </div>
        </form>
      </main>
    </div>
  );
}
