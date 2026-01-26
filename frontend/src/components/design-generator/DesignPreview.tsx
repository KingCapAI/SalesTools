import { Download, AlertCircle, Loader } from 'lucide-react';
import { Button } from '../ui/Button';
import { uploadsApi } from '../../api/uploads';
import type { DesignVersion } from '../../types/api';

interface DesignPreviewProps {
  version: DesignVersion | null;
  designNumber: number;
  isLoading?: boolean;
}

export function DesignPreview({ version, designNumber, isLoading }: DesignPreviewProps) {
  const handleDownload = () => {
    if (!version?.image_path) return;

    const url = uploadsApi.getFileUrl(version.image_path);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Design_${designNumber}_v${version.version_number}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (isLoading) {
    return (
      <div className="bg-gray-50 rounded-xl p-8 flex flex-col items-center justify-center min-h-[400px]">
        <Loader className="w-12 h-12 text-primary-500 animate-spin mb-4" />
        <p className="text-gray-600 font-medium">Generating your design...</p>
        <p className="text-sm text-gray-500 mt-1">This may take a moment</p>
      </div>
    );
  }

  if (!version) {
    return (
      <div className="bg-gray-50 rounded-xl p-8 flex flex-col items-center justify-center min-h-[400px]">
        <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mb-4">
          <span className="text-3xl">🧢</span>
        </div>
        <p className="text-gray-600">No design generated yet</p>
        <p className="text-sm text-gray-500 mt-1">Fill out the form and click Generate</p>
      </div>
    );
  }

  if (version.generation_status === 'failed') {
    return (
      <div className="bg-red-50 rounded-xl p-8 flex flex-col items-center justify-center min-h-[400px]">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <p className="text-red-700 font-medium">Generation Failed</p>
        <p className="text-sm text-red-600 mt-1 text-center max-w-md">
          {version.error_message || 'An error occurred while generating the design'}
        </p>
      </div>
    );
  }

  if (version.generation_status === 'generating' || version.generation_status === 'pending') {
    return (
      <div className="bg-gray-50 rounded-xl p-8 flex flex-col items-center justify-center min-h-[400px]">
        <Loader className="w-12 h-12 text-primary-500 animate-spin mb-4" />
        <p className="text-gray-600 font-medium">Generating your design...</p>
        <p className="text-sm text-gray-500 mt-1">This may take a moment</p>
      </div>
    );
  }

  const imageUrl = version.image_path
    ? uploadsApi.getFileUrl(version.image_path)
    : version.image_url;

  return (
    <div className="bg-gray-50 rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-gray-900">
            Design #{designNumber}v{version.version_number}
          </h3>
          <p className="text-sm text-gray-500">
            Generated {new Date(version.created_at).toLocaleString()}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleDownload}>
          <Download className="w-4 h-4 mr-2" />
          Download
        </Button>
      </div>

      {imageUrl ? (
        <img
          src={imageUrl}
          alt={`Design #${designNumber}v${version.version_number}`}
          className="w-full rounded-lg shadow-sm"
        />
      ) : (
        <div className="h-64 bg-gray-200 rounded-lg flex items-center justify-center">
          <p className="text-gray-500">Image not available</p>
        </div>
      )}
    </div>
  );
}
