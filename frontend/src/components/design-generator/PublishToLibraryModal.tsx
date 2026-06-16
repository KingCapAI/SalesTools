import { useEffect, useState } from 'react';
import { clsx } from 'clsx';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { usePublishToLibrary } from '../../hooks/useLibrary';
import { useUpdateDesign } from '../../hooks/useDesigns';
import { useUpdateCustomDesign } from '../../hooks/useCustomDesigns';
import { INDUSTRY_OPTIONS } from '../../types/api';
import type { Industry } from '../../types/api';

interface PublishToLibraryModalProps {
  designId: string;
  designKind: 'ai' | 'custom';
  initialCustomerName: string;
  initialBrandName: string;
  initialDesignName: string;
  isOpen: boolean;
  onClose: () => void;
  onPublished: () => void;
}

export function PublishToLibraryModal({
  designId,
  designKind,
  initialCustomerName,
  initialBrandName,
  initialDesignName,
  isOpen,
  onClose,
  onPublished,
}: PublishToLibraryModalProps) {
  const [customerName, setCustomerName] = useState(initialCustomerName);
  const [brandName, setBrandName] = useState(initialBrandName);
  const [designName, setDesignName] = useState(initialDesignName);
  const [selected, setSelected] = useState<Industry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const publish = usePublishToLibrary();
  const updateAi = useUpdateDesign();
  const updateCustom = useUpdateCustomDesign();

  // Reset form whenever the modal is opened for a different design or with
  // refreshed values from the parent.
  useEffect(() => {
    if (isOpen) {
      setCustomerName(initialCustomerName);
      setBrandName(initialBrandName);
      setDesignName(initialDesignName);
      setSelected([]);
      setError(null);
    }
  }, [isOpen, initialCustomerName, initialBrandName, initialDesignName]);

  const toggleIndustry = (value: Industry) => {
    setSelected((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : prev.length >= 5 ? prev : [...prev, value]
    );
  };

  if (!isOpen) return null;

  const isUpdating = designKind === 'ai' ? updateAi.isPending : updateCustom.isPending;
  const isPublishing = publish.isPending;

  const handlePublish = async () => {
    if (!brandName.trim()) {
      setError('Brand name is required.');
      return;
    }
    if (selected.length === 0) {
      setError('Pick at least one industry.');
      return;
    }
    setError(null);

    try {
      // Only call update if at least one field actually changed.
      const updates: { design_name?: string; customer_name?: string; brand_name?: string } = {};
      if (customerName !== initialCustomerName) updates.customer_name = customerName.trim();
      if (brandName !== initialBrandName) updates.brand_name = brandName.trim();
      if (designName !== initialDesignName) updates.design_name = designName.trim();

      if (Object.keys(updates).length > 0) {
        if (designKind === 'ai') {
          await updateAi.mutateAsync({ id: designId, data: updates });
        } else {
          await updateCustom.mutateAsync({ id: designId, data: updates });
        }
      }

      await publish.mutateAsync({ designId, industries: selected });
      onPublished();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to publish design');
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="card max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-semibold text-gray-100 mb-2">
          Publish to Design Library
        </h2>
        <p className="text-sm text-gray-400 mb-5">
          This design becomes visible to all teammates. Confirm the details below and pick an industry tag.
        </p>

        <div className="space-y-3 mb-5">
          <Input
            label="Customer Name"
            value={customerName}
            onChange={(e) => setCustomerName(e.target.value)}
            placeholder="e.g., Acme Corporation"
          />
          <Input
            label="Brand Name"
            value={brandName}
            onChange={(e) => setBrandName(e.target.value)}
            placeholder="e.g., Acme Golf"
            required
          />
          <Input
            label="Design Name (Optional)"
            value={designName}
            onChange={(e) => setDesignName(e.target.value)}
            placeholder="e.g., Summer Collection Cap"
          />
        </div>

        <label className="block text-sm font-medium text-gray-300 mb-1">
          Industries
        </label>
        <p className="text-xs text-gray-500 mb-2">
          Pick up to 5 categories. ({selected.length}/5 selected)
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4 max-h-72 overflow-y-auto pr-1">
          {INDUSTRY_OPTIONS.map((opt) => {
            const isSelected = selected.includes(opt.value);
            const isFull = selected.length >= 5 && !isSelected;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => toggleIndustry(opt.value)}
                disabled={isFull}
                className={clsx(
                  'px-3 py-2 rounded-lg border text-sm transition-all text-left leading-tight',
                  isSelected
                    ? 'border-primary-500 bg-primary-900/30 ring-2 ring-primary-500 text-gray-100'
                    : isFull
                    ? 'border-gray-800 bg-gray-900 text-gray-600 cursor-not-allowed'
                    : 'border-gray-700 hover:border-gray-600 bg-gray-800 text-gray-300'
                )}
              >
                {opt.label}
              </button>
            );
          })}
        </div>

        {error && <p className="text-sm text-red-400 mb-3">{error}</p>}

        <div className="flex gap-2 justify-end">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={handlePublish} isLoading={isUpdating || isPublishing}>
            Publish
          </Button>
        </div>
      </div>
    </div>
  );
}
