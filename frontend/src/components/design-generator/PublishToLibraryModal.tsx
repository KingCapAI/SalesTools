import { useState } from 'react';
import { clsx } from 'clsx';
import { Button } from '../ui/Button';
import { usePublishToLibrary } from '../../hooks/useLibrary';
import { INDUSTRY_OPTIONS } from '../../types/api';
import type { Industry } from '../../types/api';

interface PublishToLibraryModalProps {
  designId: string;
  isOpen: boolean;
  onClose: () => void;
  onPublished: () => void;
}

export function PublishToLibraryModal({
  designId,
  isOpen,
  onClose,
  onPublished,
}: PublishToLibraryModalProps) {
  const [selected, setSelected] = useState<Industry | null>(null);
  const [error, setError] = useState<string | null>(null);
  const publish = usePublishToLibrary();

  if (!isOpen) return null;

  const handlePublish = async () => {
    if (!selected) {
      setError('Please pick an industry first.');
      return;
    }
    setError(null);
    try {
      await publish.mutateAsync({ designId, industry: selected });
      onPublished();
      onClose();
      setSelected(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to publish design');
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="card max-w-lg w-full p-6">
        <h2 className="text-lg font-semibold text-gray-100 mb-2">
          Publish to Design Library
        </h2>
        <p className="text-sm text-gray-400 mb-5">
          This design becomes visible to all teammates. Pick the industry it fits best so it can be filtered.
        </p>

        <label className="block text-sm font-medium text-gray-300 mb-2">
          Industry
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4 max-h-72 overflow-y-auto pr-1">
          {INDUSTRY_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setSelected(opt.value)}
              className={clsx(
                'px-3 py-2 rounded-lg border text-sm transition-all',
                selected === opt.value
                  ? 'border-primary-500 bg-primary-900/30 ring-2 ring-primary-500 text-gray-100'
                  : 'border-gray-700 hover:border-gray-600 bg-gray-800 text-gray-300'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {error && <p className="text-sm text-red-400 mb-3">{error}</p>}

        <div className="flex gap-2 justify-end">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={handlePublish} isLoading={publish.isPending}>
            Publish
          </Button>
        </div>
      </div>
    </div>
  );
}
