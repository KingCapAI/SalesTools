import { clsx } from 'clsx';
import { uploadsApi } from '../../api/uploads';
import type { DesignVersion } from '../../types/api';

interface VersionHistoryProps {
  versions: DesignVersion[];
  designNumber: number;
  selectedVersionId: string | null;
  onSelectVersion: (versionId: string) => void;
}

export function VersionHistory({
  versions,
  designNumber,
  selectedVersionId,
  onSelectVersion,
}: VersionHistoryProps) {
  if (versions.length === 0) {
    return null;
  }

  return (
    <div>
      <h3 className="font-semibold text-white mb-3">Version History</h3>
      <div className="space-y-2">
        {versions.map((version) => {
          const imageUrl = version.image_path
            ? uploadsApi.getFileUrl(version.image_path)
            : null;
          const isSelected = selectedVersionId === version.id;
          const isCompleted = version.generation_status === 'completed';

          return (
            <button
              key={version.id}
              onClick={() => onSelectVersion(version.id)}
              className={clsx(
                'w-full flex items-center gap-3 p-3 rounded-lg border transition-all text-left',
                isSelected
                  ? 'border-primary-500 bg-primary-900/50 ring-2 ring-primary-500'
                  : 'border-gray-700 hover:border-gray-600 bg-gray-800/50'
              )}
            >
              {/* Thumbnail */}
              <div className="w-16 h-16 rounded-lg bg-gray-700 flex-shrink-0 overflow-hidden">
                {imageUrl && isCompleted ? (
                  <img
                    src={imageUrl}
                    alt={`v${version.version_number}`}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    {version.generation_status === 'failed' ? (
                      <span className="text-red-400 text-xs">Failed</span>
                    ) : (
                      <span className="text-gray-400 text-xs">
                        {version.generation_status}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-100">
                  Design #{designNumber}v{version.version_number}
                </div>
                <div className="text-xs text-gray-400">
                  {new Date(version.created_at).toLocaleDateString()}
                </div>
                <div
                  className={clsx(
                    'inline-block mt-1 px-2 py-0.5 text-xs rounded-full',
                    version.generation_status === 'completed'
                      ? 'bg-green-900/50 text-green-400'
                      : version.generation_status === 'failed'
                      ? 'bg-red-900/50 text-red-400'
                      : 'bg-yellow-900/50 text-yellow-400'
                  )}
                >
                  {version.generation_status}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
