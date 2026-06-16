import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Wand2, Library as LibraryIcon } from 'lucide-react';
import { clsx } from 'clsx';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/Button';
import { uploadsApi } from '../api/uploads';
import { useLibraryDesigns, useLibraryIndustries, useRemixData } from '../hooks/useLibrary';
import type { ReferenceMatchMode } from '../types/api';

const HAT_STYLE_LABEL: Record<string, string> = {
  '6-panel-hat': '6-Panel',
  '6-panel-trucker': '6-Panel Trucker',
  '5-panel-hat': '5-Panel',
  '5-panel-trucker': '5-Panel Trucker',
  'perforated-6-panel': 'Perforated 6-Panel',
  'perforated-5-panel': 'Perforated 5-Panel',
};

export function Library() {
  const [activeIndustry, setActiveIndustry] = useState<string>('all');
  const [remixDesignId, setRemixDesignId] = useState<string | null>(null);
  const [remixMode, setRemixMode] = useState<ReferenceMatchMode>('close');
  const navigate = useNavigate();

  const { data: designs, isLoading } = useLibraryDesigns(activeIndustry);
  const { data: industries } = useLibraryIndustries();
  const { data: remixData } = useRemixData(remixDesignId);

  const handleRemix = (designId: string) => {
    setRemixDesignId(designId);
  };

  const handleStartRemix = () => {
    if (!remixData) return;
    // Navigate to AI Designer with prefill — the remix data slots into the
    // reference image fields + form spec. User supplies their own logos and
    // customer/brand info on the form.
    navigate('/ai-design-generator/new', {
      state: {
        prefill: {
          hatStyle: remixData.hat_style,
          material: remixData.material,
          structure: remixData.structure || '',
          closure: remixData.closure || '',
          styleDirections: remixData.style_directions.length > 0 ? remixData.style_directions : ['modern'],
          referenceImagePath: remixData.reference_image_path,
          referenceMatchMode: remixMode,
          remixedFromDesignId: remixData.id,
        },
      },
    });
  };

  return (
    <div className="min-h-screen bg-black">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/dashboard">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-100 flex items-center gap-3">
                <LibraryIcon className="w-6 h-6 text-amber-400" />
                Design Library
              </h1>
              <p className="text-gray-400 mt-1 text-sm">
                Browse designs your teammates have published. Remix any one with your own logos.
              </p>
            </div>
          </div>
        </div>

        {/* Industry filter chips */}
        <div className="flex flex-wrap gap-2 mb-6">
          {(industries || []).map((chip) => (
            <button
              key={chip.industry}
              type="button"
              onClick={() => setActiveIndustry(chip.industry)}
              className={clsx(
                'px-3 py-1.5 rounded-full text-sm font-medium transition-colors',
                activeIndustry === chip.industry
                  ? 'bg-primary-500 text-white'
                  : 'bg-fill-tertiary text-gray-300 hover:bg-fill-secondary'
              )}
            >
              {chip.label}
              <span className={clsx(
                'ml-2 text-xs',
                activeIndustry === chip.industry ? 'text-primary-100' : 'text-gray-500'
              )}>
                {chip.count}
              </span>
            </button>
          ))}
          {(!industries || industries.length === 0) && (
            <p className="text-sm text-gray-500">No published designs yet.</p>
          )}
        </div>

        {/* Design grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="aspect-square rounded-xl bg-gray-800 animate-pulse" />
            ))}
          </div>
        ) : !designs || designs.length === 0 ? (
          <div className="text-center py-16 bg-gray-900/40 rounded-xl">
            <p className="text-gray-400">
              {activeIndustry === 'all'
                ? 'No published designs yet. Publish one of your own designs to seed the library.'
                : `No published designs in this industry yet.`}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {designs.map((d) => {
              const imageUrl = d.latest_image_path
                ? uploadsApi.getFileUrl(d.latest_image_path)
                : null;
              return (
                <div
                  key={d.id}
                  className="card overflow-hidden flex flex-col"
                >
                  <div className="aspect-square bg-gray-900 relative">
                    {imageUrl ? (
                      <img
                        src={imageUrl}
                        alt={d.design_name || `Design #${d.design_number}`}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-600">
                        No preview
                      </div>
                    )}
                    <div className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-black/60 text-xs text-white">
                      {industries?.find((c) => c.industry === d.library_industry)?.label || d.library_industry}
                    </div>
                  </div>

                  <div className="p-3 flex flex-col flex-1">
                    <h3 className="text-sm font-semibold text-gray-100 truncate">
                      {d.design_name || d.brand_name}
                    </h3>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {HAT_STYLE_LABEL[d.hat_style] || d.hat_style}
                      {d.published_by_name ? ` · by ${d.published_by_name}` : ''}
                    </p>
                    <Button
                      size="sm"
                      className="mt-3"
                      onClick={() => handleRemix(d.id)}
                    >
                      <Wand2 className="w-3.5 h-3.5 mr-1.5" />
                      Remix
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {/* Remix modal */}
      {remixDesignId && remixData && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="card max-w-md w-full p-6">
            <h2 className="text-lg font-semibold text-gray-100 mb-2">Remix this design</h2>
            <p className="text-sm text-gray-400 mb-5">
              We'll open the AI Designer with this design's spec pre-filled.
              Upload your customer's logos, set their brand info, and generate.
            </p>

            <label className="block text-sm font-medium text-gray-300 mb-2">
              How closely should the AI follow this design?
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
              <button
                type="button"
                onClick={() => setRemixMode('close')}
                className={clsx(
                  'p-3 rounded-lg border text-left transition-all text-sm',
                  remixMode === 'close'
                    ? 'border-primary-500 bg-primary-900/30 ring-2 ring-primary-500'
                    : 'border-gray-700 hover:border-gray-600 bg-gray-800'
                )}
              >
                <div className="font-medium text-gray-100">Match closely</div>
                <div className="text-xs text-gray-400 mt-1">
                  Reproduce silhouette + placements
                </div>
              </button>
              <button
                type="button"
                onClick={() => setRemixMode('inspiration')}
                className={clsx(
                  'p-3 rounded-lg border text-left transition-all text-sm',
                  remixMode === 'inspiration'
                    ? 'border-primary-500 bg-primary-900/30 ring-2 ring-primary-500'
                    : 'border-gray-700 hover:border-gray-600 bg-gray-800'
                )}
              >
                <div className="font-medium text-gray-100">Use as inspiration</div>
                <div className="text-xs text-gray-400 mt-1">
                  Borrow vibe; fresh composition
                </div>
              </button>
            </div>

            <div className="flex gap-2 justify-end">
              <Button variant="ghost" onClick={() => setRemixDesignId(null)}>
                Cancel
              </Button>
              <Button onClick={handleStartRemix}>
                Continue to AI Designer
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
