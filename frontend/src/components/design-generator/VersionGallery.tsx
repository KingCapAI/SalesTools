import { useState } from 'react';
import { clsx } from 'clsx';
import { AlertCircle, CheckCircle2, Loader, X, ZoomIn } from 'lucide-react';
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
  const [lightboxOpen, setLightboxOpen] = useState(false);

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

  // Group versions by batch number, sorted newest first
  const batchMap = new Map<number, DesignVersion[]>();
  for (const v of versions) {
    const batch = v.batch_number || 0;
    if (!batchMap.has(batch)) batchMap.set(batch, []);
    batchMap.get(batch)!.push(v);
  }
  const batches = Array.from(batchMap.entries()).sort((a, b) => b[0] - a[0]);

  const selectedVersion = selectedVersionId
    ? versions.find((v) => v.id === selectedVersionId)
    : null;

  const selectedImageUrl = selectedVersion?.image_path
    ? uploadsApi.getFileUrl(selectedVersion.image_path)
    : selectedVersion?.image_url || null;

  return (
    <div className="space-y-4">
      {/* Selected version — large preview at top */}
      {selectedVersion && selectedVersion.generation_status === 'completed' && selectedImageUrl ? (
        <div className="relative group">
          <div className="mb-2 flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-100 text-sm">
                Design #{designNumber} — Option {selectedVersion.version_number}
              </h3>
              <p className="text-xs text-gray-500">
                {new Date(selectedVersion.created_at).toLocaleString()}
              </p>
            </div>
            <span className="text-xs bg-primary-900/50 text-primary-400 px-2 py-1 rounded-full">
              Selected
            </span>
          </div>
          <button
            onClick={() => setLightboxOpen(true)}
            className="w-full rounded-lg overflow-hidden relative cursor-zoom-in"
          >
            <img
              src={selectedImageUrl}
              alt={`Design #${designNumber} Option ${selectedVersion.version_number}`}
              className="w-full rounded-lg"
            />
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
              <div className="opacity-0 group-hover:opacity-100 transition-opacity bg-black/60 rounded-full p-3">
                <ZoomIn className="w-6 h-6 text-white" />
              </div>
            </div>
          </button>
        </div>
      ) : !selectedVersionId ? (
        <div className="bg-primary-900/20 border border-primary-700/50 rounded-lg px-4 py-3 text-sm text-primary-300">
          Select one of the designs below to continue with revisions.
        </div>
      ) : null}

      {/* Version thumbnails */}
      {batches.map(([batchNumber, batchVersions], batchIndex) => (
        <div key={batchNumber}>
          {batches.length > 1 && (
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              {batchIndex === 0 ? 'Latest Generation' : `Generation ${batchNumber}`}
            </h4>
          )}
          <div className="grid grid-cols-3 gap-2 sm:gap-3">
            {batchVersions.map((version) => {
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
                    'relative rounded-lg border-2 overflow-hidden transition-all text-left',
                    isSelected
                      ? 'border-primary-500 ring-2 ring-primary-500/50 shadow-lg shadow-primary-500/20'
                      : isCompleted
                      ? 'border-gray-700 hover:border-gray-500 cursor-pointer'
                      : 'border-gray-800 opacity-75 cursor-not-allowed'
                  )}
                >
                  <div className="aspect-square bg-gray-900 relative">
                    {isCompleted && imageUrl ? (
                      <img
                        src={imageUrl}
                        alt={`Option ${version.version_number}`}
                        className="w-full h-full object-cover"
                      />
                    ) : isFailed ? (
                      <div className="w-full h-full flex flex-col items-center justify-center p-2">
                        <AlertCircle className="w-5 h-5 text-red-500 mb-1" />
                        <p className="text-[10px] text-red-400 text-center line-clamp-2">Failed</p>
                      </div>
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Loader className="w-5 h-5 text-primary-500 animate-spin" />
                      </div>
                    )}

                    {isSelected && (
                      <div className="absolute top-1 right-1 bg-primary-500 rounded-full p-0.5">
                        <CheckCircle2 className="w-3 h-3 text-white" />
                      </div>
                    )}
                  </div>

                  <div className="px-2 py-1.5 bg-gray-800/80">
                    <p className="text-xs font-medium text-gray-300">
                      Option {version.version_number}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
          {batchIndex < batches.length - 1 && (
            <div className="border-t border-gray-800 mt-4" />
          )}
        </div>
      ))}

      {/* Lightbox */}
      {lightboxOpen && selectedImageUrl && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4 sm:p-8"
          onClick={() => setLightboxOpen(false)}
        >
          <button
            onClick={() => setLightboxOpen(false)}
            className="absolute top-4 right-4 p-2 bg-gray-800/80 hover:bg-gray-700 rounded-full text-gray-300 hover:text-white transition-colors z-10"
          >
            <X className="w-6 h-6" />
          </button>
          <img
            src={selectedImageUrl}
            alt={`Design #${designNumber} full view`}
            className="max-w-full max-h-full object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}
