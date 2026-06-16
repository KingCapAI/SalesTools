import { useEffect, useState } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { useUpdateDesign } from '../../hooks/useDesigns';
import { useUpdateCustomDesign } from '../../hooks/useCustomDesigns';

interface RenameDesignModalProps {
  designId: string;
  designKind: 'ai' | 'custom';
  initialName: string;
  fallbackLabel: string;  // shown when initialName is empty (e.g. "Design #12")
  isOpen: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

export function RenameDesignModal({
  designId,
  designKind,
  initialName,
  fallbackLabel,
  isOpen,
  onClose,
  onSaved,
}: RenameDesignModalProps) {
  const [name, setName] = useState(initialName);
  const [error, setError] = useState<string | null>(null);
  const updateAi = useUpdateDesign();
  const updateCustom = useUpdateCustomDesign();

  useEffect(() => {
    if (isOpen) {
      setName(initialName);
      setError(null);
    }
  }, [isOpen, initialName]);

  if (!isOpen) return null;

  const isSaving = designKind === 'ai' ? updateAi.isPending : updateCustom.isPending;

  const handleSave = async () => {
    setError(null);
    const trimmed = name.trim();
    try {
      if (designKind === 'ai') {
        await updateAi.mutateAsync({ id: designId, data: { design_name: trimmed } });
      } else {
        await updateCustom.mutateAsync({ id: designId, data: { design_name: trimmed } });
      }
      onSaved?.();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to rename design');
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="card max-w-md w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-gray-100 mb-1">Rename Design</h2>
        <p className="text-sm text-gray-400 mb-4">
          Current: <span className="text-gray-300">{initialName || fallbackLabel}</span>
        </p>

        <Input
          label="Design Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={fallbackLabel}
          autoFocus
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSave();
          }}
        />

        {error && <p className="text-sm text-red-400 mt-3">{error}</p>}

        <div className="flex gap-2 justify-end mt-5">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} isLoading={isSaving}>Save</Button>
        </div>
      </div>
    </div>
  );
}
