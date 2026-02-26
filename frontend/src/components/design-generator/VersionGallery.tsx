import { clsx } from 'clsx';
import { AlertCircle, CheckCircle2, Loader } from 'lucide-react';
import { uploadsApi } from '../../api/uploads';
import type { DesignVersion } from '../../types/api';

interface VersionGalleryProps {
  versions: DesignVersion[];
  designNumber: number;
  selectedVersionId: string | null;
  onSelectVersion: (versionId: string) => void;
  isLoading?: boolean;
}

export function VersionGallery({
  versions,
  designNumber,
  selectedVersionId,
  onSelectVersion,
  isLoading,
}: VersionGalleryProps) {
  if (isLoading && versions.length === 0) {
    return (
      <div className="bg-gray-900/50 rounded-xl p-8 flex flex-col items-center justify-center min-h-[300px]">
        <Loader className="w-12 h-12 text-primary-500 animate-spin mb-4" />
        <p className="text-gray-300 font-medium">Generating 3 design options...</p>
        <p className="text-sm text-gray-500 mt-1">This may take a moment</p>
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div className="bg-gray-900/50 rounded-xl p-8 flex flex-col items-center justify-center min-h-[300px]">
        <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mb-4">
          <span className="text-3xl">🧢</span>
        </div>
        <p className="text-gray-400">No versions generated yet</p>
      </div>
    );
  }

  // Get the latest batch of versions
  const maxBatch = Math.max(...versions.map((v) => v.batch_number || 0));
  const latestBatchVersions = versions.filter((v) => (v.batch_number || 0) === maxBatch);

  // Find the selected version (from any batch)
  const selectedVersion = selectedVersionId
    ? versions.find((v) => v.id === selectedVersionId)
    : null;

  return (
    <div className="space-y-6">
      {/* Selection prompt */}
      {!selectedVersionId && (
        <div className="bg-primary-900/30 border border-primary-700 rounded-lg px-4 py-3 text-sm text-primary-300">
          Select one of the designs below to continue with revisions.
        </div>
      )}

      {/* Version grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {latestBatchVersions.map((version) => {
          const imageUrl = version.image_path
            ? uploadsApi.getFileUrl(version.image_path)
            : version.image_url;
          const isSelected = selectedVersionId === version.id;
          const isCompleted = version.generation_status === 'completed';
          const isFailed = version.generation_status === 'failed';

          return (
            <button
              key={version.id}
              onClick={() => isCompleted && onSelectVersion(version.id)}
              disabled={!isCompleted}
              className={clsx(
                'relative rounded-xl border-2 overflow-hidden transition-all text-left',
                isSelected
                  ? 'border-primary-500 ring-2 ring-primary-500/50 shadow-lg shadow-primary-500/20'
                  : isCompleted
                  ? 'border-gray-700 hover:border-gray-500 cursor-pointer'
                  : 'border-gray-800 opacity-75 cursor-not-allowed'
              )}
            >
              {/* Image or status */}
              <div className="aspect-square bg-gray-900 relative">
                {isCompleted && imageUrl ? (
                  <img
                    src={imageUrl}
                    alt={`Option ${version.version_number}`}
                    className="w-full h-full object-cover"
                  />
                ) : isFailed ? (
                  <div className="w-full h-full flex flex-col items-center justify-center p-4">
                    <AlertCircle className="w-8 h-8 text-red-500 mb-2" />
                    <p className="text-xs text-red-400 text-center">
                      {version.error_message || 'Generation failed'}
                    </p>
                  </div>
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center">
                    <Loader className="w-8 h-8 text-primary-500 animate-spin mb-2" />
                    <p className="text-xs text-gray-500">Generating...</p>
                  </div>
                )}

                {/* Selected badge */}
                {isSelected && (
                  <div className="absolute top-2 right-2 bg-primary-500 rounded-full p-1">
                    <CheckCircle2 className="w-4 h-4 text-white" />
                  </div>
                )}
              </div>

              {/* Label */}
              <div className="p-3 bg-gray-800/80">
                <p className="text-sm font-medium text-gray-200">
                  Option {version.version_number}
                </p>
                <p className="text-xs text-gray-500">
                  {isCompleted ? 'Click to select' : isFailed ? 'Failed' : 'Generating...'}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Enlarged selected version */}
      {selectedVersion && selectedVersion.generation_status === 'completed' && (
        <div className="bg-gray-900/50 rounded-xl p-4">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-100">
                Design #{designNumber} — Option {selectedVersion.version_number}
              </h3>
              <p className="text-sm text-gray-500">
                Generated {new Date(selectedVersion.created_at).toLocaleString()}
              </p>
            </div>
            <span className="text-xs bg-primary-900/50 text-primary-400 px-2 py-1 rounded-full">
              Selected
            </span>
          </div>
          {selectedVersion.image_path && (
            <img
              src={uploadsApi.getFileUrl(selectedVersion.image_path)}
              alt={`Design #${designNumber} Option ${selectedVersion.version_number}`}
              className="w-full rounded-lg"
            />
          )}
        </div>
      )}
    </div>
  );
}
