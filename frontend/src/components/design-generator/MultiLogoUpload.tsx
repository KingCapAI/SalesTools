import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, Image, Plus } from 'lucide-react';
import { Button } from '../ui/Button';
import { uploadsApi } from '../../api/uploads';
import type { DesignLogoCreate } from '../../types/api';

const MAX_LOGOS = 5;

const LOCATION_OPTIONS = [
  { value: '', label: 'Let AI Decide' },
  { value: 'front', label: 'Front' },
  { value: 'left', label: 'Left Side' },
  { value: 'right', label: 'Right Side' },
  { value: 'back', label: 'Back' },
  { value: 'visor', label: 'Visor' },
];

interface LogoEntry {
  id: string;
  name: string;
  logo_path: string;
  logo_filename: string;
  location: string;
  isUploading: boolean;
}

interface MultiLogoUploadProps {
  logos: DesignLogoCreate[];
  onChange: (logos: DesignLogoCreate[]) => void;
  disabled?: boolean;
}

export function MultiLogoUpload({ logos, onChange, disabled }: MultiLogoUploadProps) {
  const [entries, setEntries] = useState<LogoEntry[]>(
    logos.length > 0
      ? logos.map((l, i) => ({
          id: `logo-${i}-${Date.now()}`,
          name: l.name,
          logo_path: l.logo_path,
          logo_filename: l.logo_filename,
          location: l.location || '',
          isUploading: false,
        }))
      : [createEmptyEntry()]
  );

  function createEmptyEntry(): LogoEntry {
    return {
      id: `logo-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: '',
      logo_path: '',
      logo_filename: '',
      location: '',
      isUploading: false,
    };
  }

  function syncToParent(updatedEntries: LogoEntry[]) {
    const validLogos: DesignLogoCreate[] = updatedEntries
      .filter((e) => e.logo_path && e.name.trim())
      .map((e) => ({
        name: e.name.trim(),
        logo_path: e.logo_path,
        logo_filename: e.logo_filename,
        location: e.location || null,
      }));
    onChange(validLogos);
  }

  function updateEntry(id: string, updates: Partial<LogoEntry>) {
    setEntries((prev) => {
      const updated = prev.map((e) => (e.id === id ? { ...e, ...updates } : e));
      syncToParent(updated);
      return updated;
    });
  }

  function removeEntry(id: string) {
    setEntries((prev) => {
      const updated = prev.filter((e) => e.id !== id);
      // Keep at least one entry
      if (updated.length === 0) {
        const empty = createEmptyEntry();
        syncToParent([]);
        return [empty];
      }
      syncToParent(updated);
      return updated;
    });
  }

  function addEntry() {
    if (entries.length >= MAX_LOGOS) return;
    setEntries((prev) => [...prev, createEmptyEntry()]);
  }

  return (
    <div>
      <label className="label">
        Brand Logos <span className="text-red-400">*</span>
      </label>
      <p className="text-xs text-gray-500 mb-3">
        Upload up to {MAX_LOGOS} logos. Give each a name and optionally assign a location on the hat.
      </p>

      <div className="space-y-4">
        {entries.map((entry, index) => (
          <LogoEntryRow
            key={entry.id}
            entry={entry}
            index={index}
            showRemove={entries.length > 1}
            disabled={disabled}
            onUpdate={(updates) => updateEntry(entry.id, updates)}
            onRemove={() => removeEntry(entry.id)}
          />
        ))}
      </div>

      {entries.length < MAX_LOGOS && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={addEntry}
          className="mt-3"
          disabled={disabled}
        >
          <Plus className="w-4 h-4 mr-1" />
          Add Logo ({entries.length}/{MAX_LOGOS})
        </Button>
      )}
    </div>
  );
}

interface LogoEntryRowProps {
  entry: LogoEntry;
  index: number;
  showRemove: boolean;
  disabled?: boolean;
  onUpdate: (updates: Partial<LogoEntry>) => void;
  onRemove: () => void;
}

function LogoEntryRow({ entry, index, showRemove, disabled, onUpdate, onRemove }: LogoEntryRowProps) {
  const [uploadError, setUploadError] = useState<string | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      onUpdate({ isUploading: true });
      setUploadError(null);

      try {
        const response = await uploadsApi.uploadDesignLogo(file);
        onUpdate({
          logo_path: response.file_path,
          logo_filename: file.name,
          isUploading: false,
          // Auto-fill name if empty
          ...(entry.name ? {} : { name: file.name.replace(/\.[^/.]+$/, '') }),
        });
      } catch (err: any) {
        setUploadError(err.response?.data?.detail || 'Failed to upload logo');
        onUpdate({ isUploading: false });
      }
    },
    [onUpdate, entry.name]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/webp': ['.webp'],
    },
    maxFiles: 1,
    disabled: disabled || entry.isUploading,
  });

  const logoUrl = entry.logo_path ? uploadsApi.getFileUrl(entry.logo_path) : null;

  return (
    <div className="border border-gray-700 rounded-lg p-4 bg-gray-800/30">
      <div className="flex items-start gap-4">
        {/* Logo upload dropzone */}
        <div className="flex-shrink-0">
          <div
            {...getRootProps()}
            className={`w-20 h-20 border-2 border-dashed rounded-lg flex items-center justify-center cursor-pointer transition-colors overflow-hidden ${
              isDragActive
                ? 'border-primary-500 bg-primary-900/50'
                : 'border-gray-600 hover:border-gray-500 bg-gray-800/50'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <input {...getInputProps()} />
            {entry.isUploading ? (
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-500" />
            ) : logoUrl ? (
              <img src={logoUrl} alt="Logo" className="w-full h-full object-contain p-1" />
            ) : isDragActive ? (
              <Image className="w-6 h-6 text-primary-500" />
            ) : (
              <Upload className="w-6 h-6 text-gray-500" />
            )}
          </div>
        </div>

        {/* Name and location fields */}
        <div className="flex-1 space-y-2">
          <div className="flex gap-2">
            <input
              type="text"
              value={entry.name}
              onChange={(e) => onUpdate({ name: e.target.value })}
              placeholder={`Logo ${index + 1} name (e.g., "Main Logo")`}
              className="input flex-1 text-sm"
              disabled={disabled}
            />
            <select
              value={entry.location}
              onChange={(e) => onUpdate({ location: e.target.value })}
              className="input w-36 text-sm"
              disabled={disabled}
            >
              {LOCATION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          {entry.logo_filename && (
            <p className="text-xs text-gray-500">{entry.logo_filename}</p>
          )}
          {uploadError && <p className="text-xs text-red-500">{uploadError}</p>}
        </div>

        {/* Remove button */}
        {showRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="flex-shrink-0 p-1 text-gray-500 hover:text-red-400 transition-colors"
            disabled={disabled}
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
