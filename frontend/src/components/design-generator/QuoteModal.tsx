import { useState, useEffect } from 'react';
import { X, Calculator, Home, Globe, Loader } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { quotesApi } from '../../api/quotes';
import { useCreateDesignQuote, useUpdateDesignQuote } from '../../hooks/useDesignQuotes';
import type { QuoteOptions } from '../../api/quotes';
import type { DesignQuote, DesignQuoteCreate } from '../../api/designQuotes';
import clsx from 'clsx';

interface QuoteModalProps {
  isOpen: boolean;
  onClose: () => void;
  designId: string;
  existingQuote?: DesignQuote | null;
  onSaved?: () => void;
}

// Form type definitions
interface DomesticFormState {
  style_number: string;
  quantity: number;
  front_decoration: string | null;
  left_decoration: string | null;
  right_decoration: string | null;
  back_decoration: string | null;
  shipping_speed: string;
  include_rope: boolean;
  num_dst_files: number;
}

interface OverseasFormState {
  hat_type: string;
  quantity: number;
  front_decoration: string | null;
  left_decoration: string | null;
  right_decoration: string | null;
  back_decoration: string | null;
  visor_decoration: string | null;
  design_addons: string[];
  accessories: string[];
  shipping_method: string;
}

type QuoteType = 'domestic' | 'overseas';

export function QuoteModal({ isOpen, onClose, designId, existingQuote, onSaved }: QuoteModalProps) {
  const [quoteType, setQuoteType] = useState<QuoteType>(existingQuote?.quote_type || 'domestic');
  const [options, setOptions] = useState<QuoteOptions | null>(null);
  const [isLoadingOptions, setIsLoadingOptions] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const createQuote = useCreateDesignQuote();
  const updateQuote = useUpdateDesignQuote();

  // Domestic form state
  const [domesticForm, setDomesticForm] = useState<DomesticFormState>({
    style_number: existingQuote?.style_number || '',
    quantity: existingQuote?.quantity || 144,
    front_decoration: existingQuote?.front_decoration || null,
    left_decoration: existingQuote?.left_decoration || null,
    right_decoration: existingQuote?.right_decoration || null,
    back_decoration: existingQuote?.back_decoration || null,
    shipping_speed: existingQuote?.shipping_speed || 'Standard (5-7 Production Days)',
    include_rope: existingQuote?.include_rope || false,
    num_dst_files: existingQuote?.num_dst_files || 1,
  });

  // Overseas form state
  const [overseasForm, setOverseasForm] = useState<OverseasFormState>({
    hat_type: existingQuote?.hat_type || 'Classic',
    quantity: existingQuote?.quantity || 5040,
    front_decoration: existingQuote?.front_decoration || null,
    left_decoration: existingQuote?.left_decoration || null,
    right_decoration: existingQuote?.right_decoration || null,
    back_decoration: existingQuote?.back_decoration || null,
    visor_decoration: existingQuote?.visor_decoration || null,
    design_addons: existingQuote?.design_addons || [],
    accessories: existingQuote?.accessories || [],
    shipping_method: existingQuote?.shipping_method || 'FOB CA',
  });

  useEffect(() => {
    if (!isOpen) return;

    const loadOptions = async () => {
      try {
        setIsLoadingOptions(true);
        const data = await quotesApi.getOptions();
        setOptions(data);
        // Set default style if not set
        if (!domesticForm.style_number && data.domestic.styles.length > 0) {
          setDomesticForm((prev) => ({ ...prev, style_number: data.domestic.styles[0].style_number }));
        }
      } catch {
        setError('Failed to load quote options');
      } finally {
        setIsLoadingOptions(false);
      }
    };
    loadOptions();
  }, [isOpen]);

  // Reset form when existing quote changes
  useEffect(() => {
    if (existingQuote) {
      setQuoteType(existingQuote.quote_type);
      if (existingQuote.quote_type === 'domestic') {
        setDomesticForm({
          style_number: existingQuote.style_number || '',
          quantity: existingQuote.quantity,
          front_decoration: existingQuote.front_decoration,
          left_decoration: existingQuote.left_decoration,
          right_decoration: existingQuote.right_decoration,
          back_decoration: existingQuote.back_decoration,
          shipping_speed: existingQuote.shipping_speed || 'Standard (5-7 Production Days)',
          include_rope: existingQuote.include_rope || false,
          num_dst_files: existingQuote.num_dst_files || 1,
        });
      } else {
        setOverseasForm({
          hat_type: existingQuote.hat_type || 'Classic',
          quantity: existingQuote.quantity,
          front_decoration: existingQuote.front_decoration,
          left_decoration: existingQuote.left_decoration,
          right_decoration: existingQuote.right_decoration,
          back_decoration: existingQuote.back_decoration,
          visor_decoration: existingQuote.visor_decoration,
          design_addons: existingQuote.design_addons || [],
          accessories: existingQuote.accessories || [],
          shipping_method: existingQuote.shipping_method || 'FOB CA',
        });
      }
    }
  }, [existingQuote]);

  const handleSave = async () => {
    setError(null);

    const data: DesignQuoteCreate = quoteType === 'domestic'
      ? {
          quote_type: 'domestic',
          quantity: domesticForm.quantity,
          style_number: domesticForm.style_number,
          front_decoration: domesticForm.front_decoration,
          left_decoration: domesticForm.left_decoration,
          right_decoration: domesticForm.right_decoration,
          back_decoration: domesticForm.back_decoration,
          shipping_speed: domesticForm.shipping_speed,
          include_rope: domesticForm.include_rope,
          num_dst_files: domesticForm.num_dst_files,
        }
      : {
          quote_type: 'overseas',
          quantity: overseasForm.quantity,
          hat_type: overseasForm.hat_type,
          front_decoration: overseasForm.front_decoration,
          left_decoration: overseasForm.left_decoration,
          right_decoration: overseasForm.right_decoration,
          back_decoration: overseasForm.back_decoration,
          visor_decoration: overseasForm.visor_decoration,
          design_addons: overseasForm.design_addons,
          accessories: overseasForm.accessories,
          shipping_method: overseasForm.shipping_method,
        };

    try {
      await createQuote.mutateAsync({ designId, data });
      onSaved?.();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save quote');
    }
  };

  const toggleDesignAddon = (addon: string) => {
    setOverseasForm((prev) => {
      const current = prev.design_addons || [];
      if (current.includes(addon)) {
        return { ...prev, design_addons: current.filter((a) => a !== addon) };
      } else {
        return { ...prev, design_addons: [...current, addon] };
      }
    });
  };

  const toggleAccessory = (accessory: string) => {
    setOverseasForm((prev) => {
      const current = prev.accessories || [];
      if (current.includes(accessory)) {
        return { ...prev, accessories: current.filter((a) => a !== accessory) };
      } else {
        return { ...prev, accessories: [...current, accessory] };
      }
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60" onClick={onClose} />

      {/* Modal */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-gray-900 shadow-xl overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-100">
              {existingQuote ? 'Edit Quote' : 'Create Quote'}
            </h2>
            <p className="text-sm text-gray-400">Configure quote details</p>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {isLoadingOptions ? (
            <div className="flex items-center justify-center py-16">
              <Loader className="w-8 h-8 animate-spin text-primary-500" />
            </div>
          ) : (
            <>
              {/* Quote Type Toggle */}
              <div>
                <label className="label mb-2">Quote Type</label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    className={clsx(
                      'flex-1 px-4 py-3 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2',
                      quoteType === 'domestic'
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                    )}
                    onClick={() => setQuoteType('domestic')}
                  >
                    <Home className="w-4 h-4" />
                    Domestic
                  </button>
                  <button
                    type="button"
                    className={clsx(
                      'flex-1 px-4 py-3 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2',
                      quoteType === 'overseas'
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                    )}
                    onClick={() => setQuoteType('overseas')}
                  >
                    <Globe className="w-4 h-4" />
                    Overseas
                  </button>
                </div>
              </div>

              {quoteType === 'domestic' && options ? (
                <DomesticFormFields
                  form={domesticForm}
                  setForm={setDomesticForm}
                  options={options.domestic}
                />
              ) : options ? (
                <OverseasFormFields
                  form={overseasForm}
                  setForm={setOverseasForm}
                  options={options.overseas}
                  toggleDesignAddon={toggleDesignAddon}
                  toggleAccessory={toggleAccessory}
                />
              ) : null}

              {error && <p className="text-red-500 text-sm">{error}</p>}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-900 border-t border-gray-800 px-6 py-4 flex gap-3">
          <Button variant="ghost" onClick={onClose} className="flex-1">
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            isLoading={createQuote.isPending || updateQuote.isPending}
            className="flex-1"
          >
            <Calculator className="w-4 h-4 mr-2" />
            {existingQuote ? 'Update Quote' : 'Save Quote'}
          </Button>
        </div>
      </div>
    </div>
  );
}

// Domestic Form Fields
interface DomesticFormFieldsProps {
  form: DomesticFormState;
  setForm: React.Dispatch<React.SetStateAction<DomesticFormState>>;
  options: QuoteOptions['domestic'];
}

function DomesticFormFields({ form, setForm, options }: DomesticFormFieldsProps) {
  // Group styles by collection
  const stylesByCollection = options.styles.reduce((acc, style) => {
    if (!acc[style.collection]) {
      acc[style.collection] = [];
    }
    acc[style.collection].push(style);
    return acc;
  }, {} as Record<string, typeof options.styles>);

  return (
    <div className="space-y-6">
      {/* Style Selection */}
      <div>
        <label className="label mb-2">Hat Style</label>
        <div className="space-y-4">
          {Object.entries(stylesByCollection).map(([collection, styles]) => (
            <div key={collection}>
              <h3 className="text-xs font-medium text-gray-500 mb-2">{collection}</h3>
              <div className="grid grid-cols-2 gap-2">
                {styles.map((style) => (
                  <button
                    key={style.style_number}
                    type="button"
                    onClick={() => setForm((prev) => ({ ...prev, style_number: style.style_number }))}
                    className={clsx(
                      'p-3 rounded-lg border text-left transition-all text-sm',
                      form.style_number === style.style_number
                        ? 'border-primary-500 bg-primary-900/30'
                        : 'border-gray-700 hover:border-gray-600 bg-gray-800'
                    )}
                  >
                    <div className="font-medium text-gray-100">{style.style_number}</div>
                    <div className="text-xs text-gray-400">{style.name}</div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quantity */}
      <div>
        <label className="label mb-2">Quantity</label>
        <Input
          type="number"
          value={form.quantity}
          onChange={(e) => setForm((prev) => ({ ...prev, quantity: parseInt(e.target.value) || 24 }))}
          min={24}
        />
        <p className="text-xs text-gray-500 mt-1">Min: 24</p>
      </div>

      {/* Decorations */}
      <div>
        <label className="label mb-2">Decoration Methods</label>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Front</label>
            <select
              value={form.front_decoration || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, front_decoration: e.target.value || null }))}
              className="input"
            >
              <option value="">None</option>
              {options.front_decoration_methods.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Left</label>
            <select
              value={form.left_decoration || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, left_decoration: e.target.value || null }))}
              className="input"
            >
              <option value="">None</option>
              {options.additional_decoration_methods.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Right</label>
            <select
              value={form.right_decoration || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, right_decoration: e.target.value || null }))}
              className="input"
            >
              <option value="">None</option>
              {options.additional_decoration_methods.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Back</label>
            <select
              value={form.back_decoration || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, back_decoration: e.target.value || null }))}
              className="input"
            >
              <option value="">None</option>
              {options.additional_decoration_methods.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Shipping & Add-ons */}
      <div>
        <label className="label mb-2">Shipping & Add-ons</label>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Shipping Speed</label>
            <select
              value={form.shipping_speed}
              onChange={(e) => setForm((prev) => ({ ...prev, shipping_speed: e.target.value }))}
              className="input"
            >
              {options.shipping_speeds.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="include_rope"
              checked={form.include_rope}
              onChange={(e) => setForm((prev) => ({ ...prev, include_rope: e.target.checked }))}
              className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-primary-500"
            />
            <label htmlFor="include_rope" className="text-sm text-gray-300">
              Include Rope (+$1.00/piece)
            </label>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block"># DST Files</label>
            <Input
              type="number"
              value={form.num_dst_files}
              onChange={(e) => setForm((prev) => ({ ...prev, num_dst_files: parseInt(e.target.value) || 0 }))}
              min={0}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

// Overseas Form Fields
interface OverseasFormFieldsProps {
  form: OverseasFormState;
  setForm: React.Dispatch<React.SetStateAction<OverseasFormState>>;
  options: QuoteOptions['overseas'];
  toggleDesignAddon: (addon: string) => void;
  toggleAccessory: (accessory: string) => void;
}

function OverseasFormFields({ form, setForm, options, toggleDesignAddon, toggleAccessory }: OverseasFormFieldsProps) {
  return (
    <div className="space-y-6">
      {/* Hat Type */}
      <div>
        <label className="label mb-2">Hat Type</label>
        <div className="grid grid-cols-2 gap-2">
          {options.hat_types.map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => setForm((prev) => ({ ...prev, hat_type: type }))}
              className={clsx(
                'p-3 rounded-lg border text-center transition-all',
                form.hat_type === type
                  ? 'border-primary-500 bg-primary-900/30'
                  : 'border-gray-700 hover:border-gray-600 bg-gray-800'
              )}
            >
              <div className="font-medium text-gray-100">{type}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Quantity */}
      <div>
        <label className="label mb-2">Quantity</label>
        <Input
          type="number"
          value={form.quantity}
          onChange={(e) => setForm((prev) => ({ ...prev, quantity: parseInt(e.target.value) || 144 }))}
          min={144}
        />
        <p className="text-xs text-gray-500 mt-1">Min: 144</p>
      </div>

      {/* Decorations */}
      <div>
        <label className="label mb-2">Decoration Methods</label>
        <div className="space-y-3">
          {['front', 'left', 'right', 'back', 'visor'].map((pos) => (
            <div key={pos}>
              <label className="text-xs text-gray-400 mb-1 block capitalize">{pos}</label>
              <select
                value={(form as any)[`${pos}_decoration`] || ''}
                onChange={(e) => setForm((prev) => ({ ...prev, [`${pos}_decoration`]: e.target.value || null }))}
                className="input"
              >
                <option value="">None</option>
                {options.decoration_methods.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      </div>

      {/* Design Add-ons */}
      <div>
        <label className="label mb-2">Design Add-ons</label>
        <div className="grid grid-cols-2 gap-2">
          {options.design_addons.map((addon) => (
            <button
              key={addon}
              type="button"
              onClick={() => toggleDesignAddon(addon)}
              className={clsx(
                'p-2 rounded-lg border text-left transition-all text-sm',
                form.design_addons?.includes(addon)
                  ? 'border-primary-500 bg-primary-900/30'
                  : 'border-gray-700 hover:border-gray-600 bg-gray-800'
              )}
            >
              {addon}
            </button>
          ))}
        </div>
      </div>

      {/* Accessories */}
      <div>
        <label className="label mb-2">Accessories</label>
        <div className="grid grid-cols-2 gap-2">
          {options.accessories.map((acc) => (
            <button
              key={acc}
              type="button"
              onClick={() => toggleAccessory(acc)}
              className={clsx(
                'p-2 rounded-lg border text-left transition-all text-sm',
                form.accessories?.includes(acc)
                  ? 'border-primary-500 bg-primary-900/30'
                  : 'border-gray-700 hover:border-gray-600 bg-gray-800'
              )}
            >
              {acc}
            </button>
          ))}
        </div>
      </div>

      {/* Shipping */}
      <div>
        <label className="label mb-2">Shipping Method</label>
        <div className="grid grid-cols-2 gap-2">
          {options.shipping_methods.map((method) => (
            <button
              key={method}
              type="button"
              onClick={() => setForm((prev) => ({ ...prev, shipping_method: method }))}
              className={clsx(
                'p-3 rounded-lg border text-center transition-all',
                form.shipping_method === method
                  ? 'border-primary-500 bg-primary-900/30'
                  : 'border-gray-700 hover:border-gray-600 bg-gray-800'
              )}
            >
              {method}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
