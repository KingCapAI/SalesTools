import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Sparkles, X, FileText, Image as ImageIcon } from 'lucide-react';
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
  disabled?: boolean;
}

type Mode = 'upload' | 'scrape';

export function BrandGuidelines({
  brandName,
  uploadedAssets,
  onAssetUpload,
  onAssetRemove,
  scrapedData,
  onScrape,
  manualGuidelines,
  onManualGuidelinesChange,
  disabled,
}: BrandGuidelinesProps) {
  const [mode, setMode] = useState<Mode>('scrape');
  const [isUploading, setIsUploading] = useState(false);
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeUrl, setScrapeUrl] = useState('');
  const [error, setError] = useState<string | null>(null);

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
      });

      if (response.success) {
        onScrape(response.data);
      } else {
        setError(response.message || 'Failed to analyze brand');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to scrape brand information');
    } finally {
      setIsScraping(false);
    }
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
            Enter a website URL for more detailed results, or we&apos;ll search based on the brand name.
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

          {/* Scraped Data Display */}
          {scrapedData && (
            <div className="mt-4 p-4 bg-gray-800 rounded-lg border border-gray-700">
              <h4 className="font-medium text-gray-100 mb-3">Brand Analysis</h4>
              <div className="space-y-2 text-sm">
                {scrapedData.primary_colors && scrapedData.primary_colors.length > 0 && (
                  <div>
                    <span className="text-gray-400">Colors: </span>
                    <span className="flex gap-1 mt-1">
                      {scrapedData.primary_colors.map((color, i) => (
                        <span
                          key={i}
                          className="w-6 h-6 rounded border border-gray-600"
                          style={{ backgroundColor: color }}
                          title={color}
                        />
                      ))}
                    </span>
                  </div>
                )}
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
          placeholder="Enter brand PMS colors, brand direction, or any other guidelines to inform the design..."
          value={manualGuidelines}
          onChange={(e) => onManualGuidelinesChange(e.target.value)}
          disabled={disabled}
        />
      </div>

      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
    </div>
  );
}
