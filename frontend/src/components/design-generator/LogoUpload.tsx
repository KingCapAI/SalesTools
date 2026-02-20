import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, Image } from 'lucide-react';
import { uploadsApi } from '../../api/uploads';

interface LogoUploadProps {
  logoPath?: string;
  onUpload: (path: string) => void;
  disabled?: boolean;
}

export function LogoUpload({ logoPath, onUpload, disabled }: LogoUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      setIsUploading(true);
      setError(null);

      try {
        const response = await uploadsApi.uploadDesignLogo(file);
        onUpload(response.file_path);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to upload logo');
      } finally {
        setIsUploading(false);
      }
    },
    [onUpload]
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

  const logoUrl = logoPath ? uploadsApi.getFileUrl(logoPath) : null;

  return (
    <div>
      <label className="label">Brand Logo <span className="text-red-400">*</span></label>
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
        ) : logoUrl ? (
          <div className="relative inline-block">
            <img
              src={logoUrl}
              alt="Logo preview"
              className="max-h-24 max-w-full mx-auto rounded"
            />
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onUpload('');
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
              <Image className="w-8 h-8 text-primary-500 mb-2" />
            ) : (
              <Upload className="w-8 h-8 text-gray-500 mb-2" />
            )}
            <p className="text-sm text-gray-400">
              {isDragActive
                ? 'Drop the logo here'
                : 'Drag and drop a logo, or click to select'}
            </p>
            <p className="text-xs text-gray-500 mt-1">PNG, JPG, WEBP up to 10MB</p>
          </div>
        )}
      </div>

      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
    </div>
  );
}
