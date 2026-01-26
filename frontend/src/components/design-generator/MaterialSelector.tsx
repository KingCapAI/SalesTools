import { clsx } from 'clsx';
import type { Material } from '../../types/api';

interface MaterialSelectorProps {
  value: Material;
  onChange: (value: Material) => void;
}

const materials: { value: Material; label: string; description: string }[] = [
  { value: 'cotton-twill', label: 'Cotton Twill', description: 'Classic durable fabric' },
  { value: 'performance-polyester', label: 'Performance Polyester', description: 'Moisture-wicking athletic' },
  { value: 'nylon', label: 'Nylon', description: 'Lightweight and quick-dry' },
  { value: 'canvas', label: 'Canvas', description: 'Heavy-duty structured' },
];

export function MaterialSelector({ value, onChange }: MaterialSelectorProps) {
  return (
    <div>
      <label className="label">Material</label>
      <div className="grid grid-cols-2 gap-3">
        {materials.map((material) => (
          <button
            key={material.value}
            type="button"
            onClick={() => onChange(material.value)}
            className={clsx(
              'p-4 rounded-lg border text-left transition-all',
              value === material.value
                ? 'border-primary-500 bg-primary-900/30 ring-2 ring-primary-500'
                : 'border-gray-700 hover:border-gray-600 bg-gray-800'
            )}
          >
            <div className="font-medium text-gray-100">{material.label}</div>
            <div className="text-xs text-gray-400">{material.description}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
