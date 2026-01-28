import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, Image, RefreshCcw } from 'lucide-react';
import { customDesignsApi } from '../../api/customDesigns';
import { uploadsApi } from '../../api/uploads';

interface ReferenceHatUploadProps {
  value: string | null;
  onChange: (path: string | null) => void;
  disabled?: boolean;
}

export function ReferenceHatUpload({
  value,
  onChange,
  disabled,
}: ReferenceHatUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      setIsUploading(true);
      setError(null);

      try {
        const response = await customDesignsApi.uploadReferenceHat(file);
        onChange(response.reference_hat_path);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to upload reference hat');
      } finally {
        setIsUploading(false);
      }
    },
    [onChange]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/webp': ['.webp'],
    },
    maxFiles: 1,
    disabled: disabled || isUploading,
  });

  const imageUrl = value ? uploadsApi.getFileUrl(value) : null;

  return (
    <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
      <div className="flex items-center gap-2 mb-3">
        <RefreshCcw className="w-5 h-5 text-purple-400" />
        <h4 className="font-medium text-white">Reference Hat (Optional)</h4>
      </div>

      <p className="text-sm text-gray-400 mb-4">
        Have a hat you want to recreate? Upload an image and we'll match the style with your customer's logos.
      </p>

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-purple-500 bg-purple-900/30'
            : value
            ? 'border-purple-600 bg-purple-900/20'
            : 'border-gray-600 hover:border-gray-500'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />

        {isUploading ? (
          <div className="flex flex-col items-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500 mb-2"></div>
            <p className="text-sm text-gray-400">Uploading...</p>
          </div>
        ) : imageUrl ? (
          <div className="relative inline-block">
            <img
              src={imageUrl}
              alt="Reference hat"
              className="max-h-32 max-w-full mx-auto rounded"
            />
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onChange(null);
              }}
              className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
            >
              <X className="w-3 h-3" />
            </button>
            <p className="text-xs text-gray-500 mt-2">Click or drag to replace</p>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            {isDragActive ? (
              <Image className="w-10 h-10 text-purple-500 mb-2" />
            ) : (
              <Upload className="w-10 h-10 text-gray-500 mb-2" />
            )}
            <p className="text-sm text-gray-400">
              {isDragActive
                ? 'Drop the reference hat image here'
                : 'Drag and drop a reference hat image, or click to select'}
            </p>
            <p className="text-xs text-gray-500 mt-1">PNG, JPG, WebP up to 10MB</p>
          </div>
        )}
      </div>

      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
    </div>
  );
}
