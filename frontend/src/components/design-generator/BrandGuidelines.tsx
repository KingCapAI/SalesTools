import { useCallback, useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Sparkles, X, FileText, Image as ImageIcon, Plus, RotateCcw } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { uploadsApi } from '../../api/uploads';
import { aiApi } from '../../api/ai';
import type { BrandScrapedData } from '../../types/api';

interface UploadedAsset {
  id: string;
  type: string;
  file_name: string;
  file_path: string;
}

interface BrandGuidelinesProps {
  brandName: string;
  uploadedAssets: UploadedAsset[];
  onAssetUpload: (asset: UploadedAsset) => void;
  onAssetRemove: (id: string) => void;
  scrapedData: BrandScrapedData | null;
  onScrape: (data: BrandScrapedData) => void;
  manualGuidelines: string;
  onManualGuidelinesChange: (value: string) => void;
  brandColors: string[];
  onBrandColorsChange: (colors: string[]) => void;
  firstLogoPath?: string;
  disabled?: boolean;
}

type Mode = 'upload' | 'scrape';

const HEX_RE = /^#?[0-9a-fA-F]{6}$/;

function normalizeHex(value: string): string {
  const trimmed = (value || '').trim();
  if (!trimmed) return '';
  const withHash = trimmed.startsWith('#') ? trimmed : `#${trimmed}`;
  return withHash.toUpperCase();
}

function isValidHex(value: string): boolean {
  return HEX_RE.test((value || '').trim());
}

export function BrandGuidelines({
  brandName,
  uploadedAssets,
  onAssetUpload,
  onAssetRemove,
  scrapedData,
  onScrape,
  manualGuidelines,
  onManualGuidelinesChange,
  brandColors,
  onBrandColorsChange,
  firstLogoPath,
  disabled,
}: BrandGuidelinesProps) {
  const [mode, setMode] = useState<Mode>('scrape');
  const [isUploading, setIsUploading] = useState(false);
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeUrl, setScrapeUrl] = useState('');
  const [error, setError] = useState<string | null>(null);

  // When the AI returns colors, seed the editable palette — but never overwrite
  // user edits made after the initial seed.
  const [aiSuggestedColors, setAiSuggestedColors] = useState<string[]>([]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setIsUploading(true);
      setError(null);

      for (const file of acceptedFiles) {
        try {
          const response = await uploadsApi.uploadDesignAsset(file);
          onAssetUpload({
            id: crypto.randomUUID(),
            type: response.asset_type || 'image',
            file_name: file.name,
            file_path: response.file_path,
          });
        } catch (err: any) {
          setError(err.response?.data?.detail || 'Failed to upload file');
        }
      }

      setIsUploading(false);
    },
    [onAssetUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'application/pdf': ['.pdf'],
    },
    disabled: disabled || isUploading,
  });

  const handleScrape = async () => {
    if (!brandName && !scrapeUrl) {
      setError('Please enter a brand name or website URL');
      return;
    }

    setIsScraping(true);
    setError(null);

    try {
      const response = await aiApi.scrapeBrand({
        brand_name: brandName || undefined,
        brand_url: scrapeUrl || undefined,
        logo_path: firstLogoPath || undefined,
      });

      if (response.success) {
        onScrape(response.data);
        // Seed editable palette from AI output (primaries first, then secondaries).
        const merged = [
          ...(response.data.primary_colors || []),
          ...(response.data.secondary_colors || []),
        ]
          .map(normalizeHex)
          .filter(isValidHex)
          .filter((v, i, arr) => arr.indexOf(v) === i)
          .slice(0, 6);
        setAiSuggestedColors(merged);
        onBrandColorsChange(merged);
      } else {
        setError(response.message || 'Failed to analyze brand');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to scrape brand information');
    } finally {
      setIsScraping(false);
    }
  };

  // Local hex input editing — held separately so partial typing doesn't fail
  // validation mid-keystroke.
  const [hexDrafts, setHexDrafts] = useState<string[]>([]);
  useEffect(() => {
    setHexDrafts(brandColors);
  }, [brandColors.join('|')]);

  const updateColorAt = (idx: number, raw: string) => {
    const drafts = [...hexDrafts];
    drafts[idx] = raw;
    setHexDrafts(drafts);
    if (isValidHex(raw)) {
      const next = [...brandColors];
      next[idx] = normalizeHex(raw);
      onBrandColorsChange(next);
    }
  };

  const removeColorAt = (idx: number) => {
    const next = brandColors.filter((_, i) => i !== idx);
    onBrandColorsChange(next);
  };

  const addColor = () => {
    if (brandColors.length >= 6) return;
    onBrandColorsChange([...brandColors, '#000000']);
  };

  const resetToAI = () => {
    onBrandColorsChange(aiSuggestedColors);
  };

  const sourceFor = (hex: string): string | undefined => {
    const map = scrapedData?.color_sources;
    if (!map) return undefined;
    return map[hex.toUpperCase()];
  };

  return (
    <div>
      <label className="label">Brand Guidelines (Optional)</label>

      {/* Mode Toggle */}
      <div className="flex gap-2 mb-4">
        <button
          type="button"
          className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === 'scrape'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
          onClick={() => setMode('scrape')}
        >
          <Sparkles className="w-4 h-4 inline-block mr-2" />
          AI Scrape
        </button>
        <button
          type="button"
          className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === 'upload'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
          onClick={() => setMode('upload')}
        >
          <Upload className="w-4 h-4 inline-block mr-2" />
          Upload Files
        </button>
      </div>

      {mode === 'scrape' ? (
        <div className="space-y-4">
          <p className="text-sm text-gray-400">
            Let AI analyze the brand to extract colors, style, and design recommendations.
            For best accuracy: upload the brand&apos;s logo above first (becomes the source of
            truth for primary colors), then add the homepage URL.
          </p>
          <Input
            label="Brand Website URL (Optional)"
            value={scrapeUrl}
            onChange={(e) => setScrapeUrl(e.target.value)}
            placeholder="https://example.com"
          />
          <Button
            type="button"
            onClick={handleScrape}
            isLoading={isScraping}
            disabled={disabled || (!scrapeUrl && !brandName)}
            className="w-full"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Analyze Brand with AI
          </Button>

          {/* Editable color swatches — always visible so users can hand-enter colors
              without running the AI analysis at all. */}
          <div className="mt-4 p-4 bg-gray-800 rounded-lg border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-gray-100 text-sm">Brand Colors</h4>
              {aiSuggestedColors.length > 0 && (
                <button
                  type="button"
                  onClick={resetToAI}
                  className="text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1"
                  title="Reset to AI suggestions"
                >
                  <RotateCcw className="w-3 h-3" />
                  Reset to AI
                </button>
              )}
            </div>
            <p className="text-xs text-gray-500 mb-3">
              These colors are sent to the AI image generator. Edit, add, or remove to correct
              what the AI got wrong.
            </p>
            {brandColors.length === 0 ? (
              <p className="text-xs text-gray-500 italic mb-3">
                No colors yet. Click &quot;Analyze Brand with AI&quot; above, or add hex codes manually.
              </p>
            ) : (
              <div className="space-y-2 mb-3">
                {brandColors.map((hex, idx) => {
                  const draft = hexDrafts[idx] ?? hex;
                  const valid = isValidHex(draft);
                  const source = sourceFor(hex);
                  return (
                    <div key={idx} className="flex items-center gap-2">
                      <input
                        type="color"
                        value={valid ? normalizeHex(draft) : '#000000'}
                        onChange={(e) => updateColorAt(idx, e.target.value)}
                        className="w-10 h-10 rounded border border-gray-600 bg-transparent cursor-pointer"
                        aria-label={`Color ${idx + 1} picker`}
                      />
                      <input
                        type="text"
                        value={draft}
                        onChange={(e) => updateColorAt(idx, e.target.value)}
                        placeholder="#000000"
                        className={`flex-1 px-3 py-2 rounded-lg bg-gray-900 border text-sm text-gray-100 font-mono ${
                          valid ? 'border-gray-700' : 'border-red-500/60'
                        }`}
                        spellCheck={false}
                      />
                      {source && (
                        <span
                          className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded ${
                            source === 'logo'
                              ? 'bg-green-900/50 text-green-300'
                              : source === 'website'
                              ? 'bg-blue-900/50 text-blue-300'
                              : 'bg-gray-700 text-gray-400'
                          }`}
                          title={
                            source === 'logo'
                              ? 'Sampled from logo pixels'
                              : source === 'website'
                              ? 'Inferred from website'
                              : 'AI knowledge guess'
                          }
                        >
                          {source}
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={() => removeColorAt(idx)}
                        className="p-2 text-gray-500 hover:text-red-400"
                        aria-label={`Remove color ${idx + 1}`}
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
            <button
              type="button"
              onClick={addColor}
              disabled={brandColors.length >= 6}
              className="text-sm text-primary-400 hover:text-primary-300 disabled:text-gray-600 disabled:cursor-not-allowed flex items-center gap-1"
            >
              <Plus className="w-4 h-4" />
              Add color
              {brandColors.length >= 6 && <span className="ml-1 text-xs">(max 6)</span>}
            </button>
          </div>

          {/* Scraped Data: extras beyond the colors (style, recommendations, etc.) */}
          {scrapedData && (
            <div className="mt-4 p-4 bg-gray-800 rounded-lg border border-gray-700">
              <h4 className="font-medium text-gray-100 mb-3 text-sm">Brand Analysis</h4>
              <div className="space-y-2 text-sm">
                {scrapedData.brand_style && (
                  <div>
                    <span className="text-gray-400">Style: </span>
                    <span className="text-gray-100">{scrapedData.brand_style}</span>
                  </div>
                )}
                {scrapedData.design_aesthetic && (
                  <div>
                    <span className="text-gray-400">Aesthetic: </span>
                    <span className="text-gray-100">{scrapedData.design_aesthetic}</span>
                  </div>
                )}
                {scrapedData.recommendations && (
                  <div>
                    <span className="text-gray-400">Recommendations: </span>
                    <span className="text-gray-100">{scrapedData.recommendations}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div>
          <p className="text-sm text-gray-400 mb-4">
            Upload brand guidelines PDFs or images to help inform the design.
          </p>
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
              isDragActive
                ? 'border-primary-500 bg-primary-900/50'
                : 'border-gray-600 hover:border-gray-500 bg-gray-800/50'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <input {...getInputProps()} />

            {isUploading ? (
              <div className="flex flex-col items-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mb-2"></div>
                <p className="text-sm text-gray-400">Uploading...</p>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <Upload className="w-8 h-8 text-gray-500 mb-2" />
                <p className="text-sm text-gray-400">
                  Drag and drop brand guidelines, or click to select
                </p>
                <p className="text-xs text-gray-500 mt-1">PDF or images up to 25MB</p>
              </div>
            )}
          </div>

          {/* Uploaded Files */}
          {uploadedAssets.length > 0 && (
            <div className="mt-4 space-y-2">
              {uploadedAssets.map((asset) => (
                <div
                  key={asset.id}
                  className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg border border-gray-700"
                >
                  {asset.type === 'pdf' ? (
                    <FileText className="w-5 h-5 text-red-400" />
                  ) : (
                    <ImageIcon className="w-5 h-5 text-blue-400" />
                  )}
                  <span className="flex-1 text-sm text-gray-300 truncate">
                    {asset.file_name}
                  </span>
                  <button
                    type="button"
                    onClick={() => onAssetRemove(asset.id)}
                    className="text-gray-500 hover:text-red-400"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Manual Guidelines */}
      <div className="mt-4">
        <label className="label">Additional Brand Information (Optional)</label>
        <textarea
          className="input min-h-[80px]"
          placeholder="Enter brand PMS codes, design direction, do's and don'ts, or anything else the AI should know..."
          value={manualGuidelines}
          onChange={(e) => onManualGuidelinesChange(e.target.value)}
          disabled={disabled}
        />
      </div>

      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
    </div>
  );
}
