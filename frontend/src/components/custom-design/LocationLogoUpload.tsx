import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, Image } from 'lucide-react';
import { customDesignsApi } from '../../api/customDesigns';
import { uploadsApi } from '../../api/uploads';
import type { DecorationLocation, DecorationMethod, DecorationSize, LocationLogoCreate } from '../../types/api';

const DECORATION_METHODS: { value: DecorationMethod; label: string }[] = [
  { value: 'embroidery', label: 'Embroidery' },
  { value: 'screen_print', label: 'Screen Print' },
  { value: 'patch', label: 'Patch' },
  { value: '3d_puff', label: '3D Puff' },
  { value: 'laser_cut', label: 'Laser Cut' },
  { value: 'heat_transfer', label: 'Heat Transfer' },
  { value: 'sublimation', label: 'Sublimation' },
];

const SIZES: { value: DecorationSize; label: string }[] = [
  { value: 'small', label: 'Small (~2")' },
  { value: 'medium', label: 'Medium (~3")' },
  { value: 'large', label: 'Large (~4")' },
  { value: 'custom', label: 'Custom' },
];

const LOCATION_LABELS: Record<DecorationLocation, string> = {
  front: 'Front',
  left: 'Left Side',
  right: 'Right Side',
  back: 'Back',
  visor: 'Visor (Underbrim)',
};

interface LocationLogoUploadProps {
  location: DecorationLocation;
  value: Partial<LocationLogoCreate> | null;
  onChange: (value: Partial<LocationLogoCreate> | null) => void;
  disabled?: boolean;
}

export function LocationLogoUpload({
  location,
  value,
  onChange,
  disabled,
}: LocationLogoUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      setIsUploading(true);
      setError(null);

      try {
        const response = await customDesignsApi.uploadLocationLogo(file, location);
        onChange({
          ...value,
          location,
          logo_path: response.logo_path,
          logo_filename: response.logo_filename,
          decoration_method: value?.decoration_method || 'embroidery',
          size: value?.size || 'medium',
        });
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to upload logo');
      } finally {
        setIsUploading(false);
      }
    },
    [location, value, onChange]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/svg+xml': ['.svg'],
      'image/webp': ['.webp'],
    },
    maxFiles: 1,
    disabled: disabled || isUploading,
  });

  const logoUrl = value?.logo_path ? uploadsApi.getFileUrl(value.logo_path) : null;
  const hasLogo = !!value?.logo_path;

  const handleClear = () => {
    onChange(null);
  };

  const handleMethodChange = (method: DecorationMethod) => {
    if (!value) return;
    onChange({ ...value, decoration_method: method });
  };

  const handleSizeChange = (size: DecorationSize) => {
    if (!value) return;
    onChange({ ...value, size, size_details: size === 'custom' ? value.size_details : undefined });
  };

  const handleSizeDetailsChange = (details: string) => {
    if (!value) return;
    onChange({ ...value, size_details: details });
  };

  return (
    <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-white">{LOCATION_LABELS[location]}</h4>
        {hasLogo && (
          <button
            type="button"
            onClick={handleClear}
            className="text-gray-400 hover:text-red-400 transition-colors"
            title="Remove"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Logo Upload Zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors mb-3 ${
          isDragActive
            ? 'border-primary-500 bg-primary-900/50'
            : hasLogo
            ? 'border-green-600 bg-green-900/20'
            : 'border-gray-600 hover:border-gray-500'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />

        {isUploading ? (
          <div className="flex flex-col items-center">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-500 mb-2"></div>
            <p className="text-xs text-gray-400">Uploading...</p>
          </div>
        ) : logoUrl ? (
          <div className="relative">
            <img
              src={logoUrl}
              alt={`${location} logo`}
              className="max-h-16 max-w-full mx-auto rounded"
            />
            <p className="text-xs text-gray-500 mt-1">Click to replace</p>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            {isDragActive ? (
              <Image className="w-6 h-6 text-primary-500 mb-1" />
            ) : (
              <Upload className="w-6 h-6 text-gray-500 mb-1" />
            )}
            <p className="text-xs text-gray-400">
              {isDragActive ? 'Drop logo here' : 'Upload logo'}
            </p>
          </div>
        )}
      </div>

      {error && <p className="text-xs text-red-500 mb-2">{error}</p>}

      {/* Decoration Method & Size (only shown when logo is uploaded) */}
      {hasLogo && (
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Method</label>
            <select
              value={value?.decoration_method || 'embroidery'}
              onChange={(e) => handleMethodChange(e.target.value as DecorationMethod)}
              className="input text-sm py-1.5"
              disabled={disabled}
            >
              {DECORATION_METHODS.map((method) => (
                <option key={method.value} value={method.value}>
                  {method.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">Size</label>
            <select
              value={value?.size || 'medium'}
              onChange={(e) => handleSizeChange(e.target.value as DecorationSize)}
              className="input text-sm py-1.5"
              disabled={disabled}
            >
              {SIZES.map((size) => (
                <option key={size.value} value={size.value}>
                  {size.label}
                </option>
              ))}
            </select>
          </div>

          {value?.size === 'custom' && (
            <div>
              <label className="block text-xs text-gray-400 mb-1">Custom Size</label>
              <input
                type="text"
                value={value?.size_details || ''}
                onChange={(e) => handleSizeDetailsChange(e.target.value)}
                placeholder="e.g., 3x2 inches"
                className="input text-sm py-1.5"
                disabled={disabled}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
