import { clsx } from 'clsx';
import { Check } from 'lucide-react';
import type { StyleDirection } from '../../types/api';

interface StyleSelectorProps {
  value: StyleDirection[];
  onChange: (value: StyleDirection[]) => void;
  customDescription: string;
  onCustomDescriptionChange: (value: string) => void;
}

const styles: { value: StyleDirection; label: string; description: string }[] = [
  { value: 'simple', label: 'Simple', description: 'Clean and minimal' },
  { value: 'modern', label: 'Modern', description: 'Contemporary and sleek' },
  { value: 'luxurious', label: 'Luxurious', description: 'Premium and elegant' },
  { value: 'sporty', label: 'Sporty', description: 'Athletic and dynamic' },
  { value: 'rugged', label: 'Rugged', description: 'Tough and outdoor' },
  { value: 'retro', label: 'Retro', description: 'Vintage and nostalgic' },
  { value: 'collegiate', label: 'Collegiate', description: 'Academic and classic' },
];

const MAX_SELECTIONS = 3;
const DESCRIBE_BELOW: StyleDirection = 'describe-below';

export function StyleSelector({
  value,
  onChange,
  customDescription,
  onCustomDescriptionChange,
}: StyleSelectorProps) {
  const describeBelowSelected = value.includes(DESCRIBE_BELOW);

  const handleToggle = (styleValue: StyleDirection) => {
    if (styleValue === DESCRIBE_BELOW) {
      // Mutually exclusive with all presets.
      onChange(describeBelowSelected ? [] : [DESCRIBE_BELOW]);
      return;
    }

    // Picking any preset direction clears the describe-below sentinel.
    const cleaned = value.filter((v) => v !== DESCRIBE_BELOW);
    if (cleaned.includes(styleValue)) {
      onChange(cleaned.filter((v) => v !== styleValue));
    } else if (cleaned.length < MAX_SELECTIONS) {
      onChange([...cleaned, styleValue]);
    }
  };

  const isSelected = (styleValue: StyleDirection) => value.includes(styleValue);
  const isDisabled = (styleValue: StyleDirection) =>
    !isSelected(styleValue) &&
    (describeBelowSelected || value.length >= MAX_SELECTIONS);

  return (
    <div>
      <label className="label">Design Direction</label>
      <p className="text-sm text-gray-400 mb-3">
        Select up to {MAX_SELECTIONS} style directions to guide the design
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
        {styles.map((style) => (
          <button
            key={style.value}
            type="button"
            onClick={() => handleToggle(style.value)}
            disabled={isDisabled(style.value)}
            className={clsx(
              'px-4 py-3 rounded-lg border text-left transition-all relative',
              isSelected(style.value)
                ? 'border-primary-500 bg-primary-900/30 ring-2 ring-primary-500'
                : isDisabled(style.value)
                ? 'border-gray-700 bg-gray-800 opacity-50 cursor-not-allowed'
                : 'border-gray-700 hover:border-gray-600 bg-gray-800'
            )}
          >
            {isSelected(style.value) && (
              <div className="absolute top-2 right-2 w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center">
                <Check className="w-3 h-3 text-white" />
              </div>
            )}
            <div className="font-medium text-gray-100">{style.label}</div>
            <div className="text-xs text-gray-400">{style.description}</div>
          </button>
        ))}
      </div>

      <button
        type="button"
        onClick={() => handleToggle(DESCRIBE_BELOW)}
        className={clsx(
          'w-full px-4 py-3 rounded-lg border text-left transition-all relative mb-4',
          describeBelowSelected
            ? 'border-primary-500 bg-primary-900/30 ring-2 ring-primary-500'
            : 'border-gray-700 hover:border-gray-600 bg-gray-800'
        )}
      >
        {describeBelowSelected && (
          <div className="absolute top-2 right-2 w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center">
            <Check className="w-3 h-3 text-white" />
          </div>
        )}
        <div className="font-medium text-gray-100">Describe Below</div>
        <div className="text-xs text-gray-400">
          Skip the presets and use only the description text below
        </div>
      </button>

      {value.length > 0 && !describeBelowSelected && (
        <div className="mb-4 flex flex-wrap gap-2">
          <span className="text-sm text-gray-400">Selected:</span>
          {value.map((v) => (
            <span
              key={v}
              className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary-900/50 text-primary-400"
            >
              {styles.find((s) => s.value === v)?.label}
            </span>
          ))}
        </div>
      )}

      <div>
        <label className="label">
          {describeBelowSelected
            ? 'Description (Required)'
            : 'Additional Description (Optional)'}
        </label>
        <textarea
          className="input min-h-[80px]"
          placeholder={
            describeBelowSelected
              ? 'Describe the style direction in your own words...'
              : 'Describe any additional style preferences or specific requirements...'
          }
          value={customDescription}
          onChange={(e) => onCustomDescriptionChange(e.target.value)}
        />
      </div>
    </div>
  );
}
