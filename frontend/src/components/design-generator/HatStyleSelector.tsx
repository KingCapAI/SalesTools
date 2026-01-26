import { clsx } from 'clsx';
import type { HatStyle } from '../../types/api';

interface HatStyleSelectorProps {
  value: HatStyle;
  onChange: (value: HatStyle) => void;
}

const hatStyles: { value: HatStyle; label: string; description: string }[] = [
  { value: '6-panel-hat', label: '6-Panel Hat', description: 'Classic structured cap' },
  { value: '6-panel-trucker', label: '6-Panel Trucker', description: 'Mesh back trucker style' },
  { value: '5-panel-hat', label: '5-Panel Hat', description: 'Casual flat front' },
  { value: '5-panel-trucker', label: '5-Panel Trucker', description: '5-panel with mesh back' },
  { value: 'perforated-6-panel', label: 'Perforated 6-Panel', description: 'Breathable perforated' },
  { value: 'perforated-5-panel', label: 'Perforated 5-Panel', description: 'Perforated casual' },
];

export function HatStyleSelector({ value, onChange }: HatStyleSelectorProps) {
  return (
    <div>
      <label className="label">Hat Style</label>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {hatStyles.map((style) => (
          <button
            key={style.value}
            type="button"
            onClick={() => onChange(style.value)}
            className={clsx(
              'p-4 rounded-lg border text-left transition-all',
              value === style.value
                ? 'border-primary-500 bg-primary-900/30 ring-2 ring-primary-500'
                : 'border-gray-700 hover:border-gray-600 bg-gray-800'
            )}
          >
            <div className="w-12 h-12 bg-gray-700 rounded-lg mb-2 flex items-center justify-center">
              <span className="text-2xl">🧢</span>
            </div>
            <div className="font-medium text-gray-100 text-sm">{style.label}</div>
            <div className="text-xs text-gray-400">{style.description}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
