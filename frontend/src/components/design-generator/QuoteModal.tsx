import { useState, useEffect } from 'react';
import { X, Calculator, Home, Globe, Loader } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { quotesApi } from '../../api/quotes';
import { useCreateDesignQuote, useUpdateDesignQuote } from '../../hooks/useDesignQuotes';
import type { QuoteOptions, DomesticQuoteResponse, OverseasQuoteResponse } from '../../api/quotes';
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

// Helper function to format currency with commas
function formatCurrency(value: number): string {
  return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Helper to check if a decoration value is valid (not null, empty, or "0")
function isValidDecoration(value: string | null | undefined): boolean {
  return typeof value === 'string' && value.trim().length > 0 && value !== '0';
}

export function QuoteModal({ isOpen, onClose, designId, existingQuote, onSaved }: QuoteModalProps) {
  const [quoteType, setQuoteType] = useState<QuoteType>(existingQuote?.quote_type || 'domestic');
  const [options, setOptions] = useState<QuoteOptions | null>(null);
  const [isLoadingOptions, setIsLoadingOptions] = useState(true);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Quote results
  const [domesticResult, setDomesticResult] = useState<DomesticQuoteResponse | null>(null);
  const [overseasResult, setOverseasResult] = useState<OverseasQuoteResponse | null>(null);

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
    quantity: 5040, // Always use max to get all price breaks
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
          quantity: 5040, // Always use max to get all price breaks
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

  // Clear results when switching quote type
  useEffect(() => {
    setDomesticResult(null);
    setOverseasResult(null);
  }, [quoteType]);

  const handleCalculate = async () => {
    setIsCalculating(true);
    setError(null);

    try {
      if (quoteType === 'domestic') {
        const result = await quotesApi.calculateDomestic({
          style_number: domesticForm.style_number,
          quantity: domesticForm.quantity,
          front_decoration: domesticForm.front_decoration,
          left_decoration: domesticForm.left_decoration,
          right_decoration: domesticForm.right_decoration,
          back_decoration: domesticForm.back_decoration,
          shipping_speed: domesticForm.shipping_speed,
          include_rope: domesticForm.include_rope,
          num_dst_files: domesticForm.num_dst_files,
        });
        setDomesticResult(result);
        setOverseasResult(null);
      } else {
        const result = await quotesApi.calculateOverseas({
          hat_type: overseasForm.hat_type,
          quantity: overseasForm.quantity,
          front_decoration: overseasForm.front_decoration,
          left_decoration: overseasForm.left_decoration,
          right_decoration: overseasForm.right_decoration,
          back_decoration: overseasForm.back_decoration,
          visor_decoration: overseasForm.visor_decoration,
          design_addons: overseasForm.design_addons,
          accessories: overseasForm.accessories,
          shipping_method: overseasForm.shipping_method,
        });
        setOverseasResult(result);
        setDomesticResult(null);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to calculate quote');
    } finally {
      setIsCalculating(false);
    }
  };

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

  const hasResults = domesticResult || overseasResult;

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60" onClick={onClose} />

      {/* Modal */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-2xl bg-gray-900 shadow-xl overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="text-lg font-semibold text-gray-100">
              {existingQuote ? 'Edit Quote' : 'Create Quote'}
            </h2>
            <p className="text-sm text-gray-400">Configure quote details and calculate pricing</p>
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

              {/* Calculate Button */}
              <Button
                onClick={handleCalculate}
                isLoading={isCalculating}
                variant="secondary"
                className="w-full"
                size="lg"
              >
                <Calculator className="w-5 h-5 mr-2" />
                Calculate Quote
              </Button>

              {/* Results Display */}
              {domesticResult && <DomesticResults result={domesticResult} />}
              {overseasResult && <OverseasResults result={overseasResult} />}
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
            disabled={!hasResults}
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
        <p className="text-xs text-gray-500 mt-1">Min: 24. Quantity breaks: {options.quantity_breaks.join(', ')}</p>
      </div>

      {/* Decorations */}
      <div>
        <label className="label mb-2">Decoration Methods</label>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Front (Primary)</label>
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
            <label className="text-xs text-gray-400 mb-1 block">Left Side</label>
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
            <label className="text-xs text-gray-400 mb-1 block">Right Side</label>
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
        <label className="label mb-2">Add-ons & Shipping</label>
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
              className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-primary-500 focus:ring-primary-500"
            />
            <label htmlFor="include_rope" className="text-sm text-gray-300">
              Include Rope (+$1.00/piece)
            </label>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block"># of DST Files (Digitizing)</label>
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

      {/* Decorations */}
      <div>
        <label className="label mb-2">Decoration Methods</label>
        <div className="space-y-3">
          {['front', 'left', 'right', 'back', 'visor'].map((pos) => (
            <div key={pos}>
              <label className="text-xs text-gray-400 mb-1 block capitalize">{pos === 'visor' ? 'Visor' : `${pos.charAt(0).toUpperCase() + pos.slice(1)} Side`}</label>
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

// Domestic Results Component - matches QuoteEstimator exactly
function DomesticResults({ result }: { result: DomesticQuoteResponse }) {
  // Get the applicable price break (the last one that applies to the quantity)
  const pb = result.price_breaks[result.price_breaks.length - 1];

  // Check for valid decoration values
  const hasFront = isValidDecoration(result.front_decoration);
  const hasLeft = isValidDecoration(result.left_decoration);
  const hasRight = isValidDecoration(result.right_decoration);
  const hasBack = isValidDecoration(result.back_decoration);
  const hasRushFee = pb?.rush_fee && pb.rush_fee > 0;
  const hasRope = result.include_rope && pb?.rope_price && pb.rope_price > 0;

  if (!pb) return null;

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-lg font-semibold text-gray-100 mb-4">Quote Results - Domestic</h3>

      <div className="mb-4 p-3 bg-gray-700/50 rounded-lg">
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-gray-400">Style:</span>
            <span className="text-gray-100 ml-2">
              {result.style_number} - {result.style_name}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Collection:</span>
            <span className="text-gray-100 ml-2">{result.collection}</span>
          </div>
          <div>
            <span className="text-gray-400">Quantity:</span>
            <span className="text-gray-100 ml-2">{result.quantity.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-gray-400">Shipping:</span>
            <span className="text-gray-100 ml-2">{result.shipping_speed}</span>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-600">
              <th className="text-left py-2 px-2 text-gray-400">Line Item</th>
              <th className="text-right py-2 px-2 text-gray-400">Per Piece</th>
              <th className="text-right py-2 px-2 text-gray-400">Qty</th>
              <th className="text-right py-2 px-2 text-gray-400">Total</th>
            </tr>
          </thead>
          <tbody>
            {/* Blank Hat */}
            <tr className="border-b border-gray-700">
              <td className="py-2 px-2 text-gray-100">Blank Hat</td>
              <td className="py-2 px-2 text-right text-gray-100">${formatCurrency(pb.blank_price || 0)}</td>
              <td className="py-2 px-2 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
              <td className="py-2 px-2 text-right text-gray-100">${formatCurrency((pb.blank_price || 0) * result.quantity)}</td>
            </tr>

            {/* Front Decoration */}
            {hasFront && (
              <tr className="border-b border-gray-700">
                <td className="py-2 px-2 text-gray-100">
                  <div>Front Decoration</div>
                  <div className="text-xs text-gray-400">{result.front_decoration}</div>
                </td>
                <td className="py-2 px-2 text-right text-gray-100">${formatCurrency(pb.front_decoration_price || 0)}</td>
                <td className="py-2 px-2 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
                <td className="py-2 px-2 text-right text-gray-100">${formatCurrency((pb.front_decoration_price || 0) * result.quantity)}</td>
              </tr>
            )}

            {/* Left Decoration */}
            {hasLeft && (
              <tr className="border-b border-gray-700">
                <td className="py-2 px-2 text-gray-100">
                  <div>Left Side Decoration</div>
                  <div className="text-xs text-gray-400">{result.left_decoration}</div>
                </td>
                <td className="py-2 px-2 text-right text-gray-100">${formatCurrency(pb.left_decoration_price || 0)}</td>
                <td className="py-2 px-2 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
                <td className="py-2 px-2 text-right text-gray-100">${formatCurrency((pb.left_decoration_price || 0) * result.quantity)}</td>
              </tr>
            )}

            {/* Right Decoration */}
            {hasRight && (
              <tr className="border-b border-gray-700">
                <td className="py-2 px-2 text-gray-100">
                  <div>Right Side Decoration</div>
                  <div className="text-xs text-gray-400">{result.right_decoration}</div>
                </td>
                <td className="py-2 px-2 text-right text-gray-100">${formatCurrency(pb.right_decoration_price || 0)}</td>
                <td className="py-2 px-2 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
                <td className="py-2 px-2 text-right text-gray-100">${formatCurrency((pb.right_decoration_price || 0) * result.quantity)}</td>
              </tr>
            )}

            {/* Back Decoration */}
            {hasBack && (
              <tr className="border-b border-gray-700">
                <td className="py-2 px-2 text-gray-100">
                  <div>Back Decoration</div>
                  <div className="text-xs text-gray-400">{result.back_decoration}</div>
                </td>
                <td className="py-2 px-2 text-right text-gray-100">${formatCurrency(pb.back_decoration_price || 0)}</td>
                <td className="py-2 px-2 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
                <td className="py-2 px-2 text-right text-gray-100">${formatCurrency((pb.back_decoration_price || 0) * result.quantity)}</td>
              </tr>
            )}

            {/* Rush Fee */}
            {hasRushFee && (
              <tr className="border-b border-gray-700">
                <td className="py-2 px-2 text-gray-100">Rush Fee</td>
                <td className="py-2 px-2 text-right text-gray-100">${formatCurrency(pb.rush_fee || 0)}</td>
                <td className="py-2 px-2 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
                <td className="py-2 px-2 text-right text-gray-100">${formatCurrency((pb.rush_fee || 0) * result.quantity)}</td>
              </tr>
            )}

            {/* Rope */}
            {hasRope && (
              <tr className="border-b border-gray-700">
                <td className="py-2 px-2 text-gray-100">Rope</td>
                <td className="py-2 px-2 text-right text-gray-100">${formatCurrency(pb.rope_price || 0)}</td>
                <td className="py-2 px-2 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
                <td className="py-2 px-2 text-right text-gray-100">${formatCurrency((pb.rope_price || 0) * result.quantity)}</td>
              </tr>
            )}

            {/* Digitizing Fee */}
            {(pb.digitizing_fee ?? 0) > 0 && (
              <tr className="border-b border-gray-700">
                <td className="py-2 px-2 text-gray-100">Digitizing Fee</td>
                <td className="py-2 px-2 text-right text-gray-400">-</td>
                <td className="py-2 px-2 text-right text-gray-400">1</td>
                <td className="py-2 px-2 text-right text-gray-100">${formatCurrency(pb.digitizing_fee ?? 0)}</td>
              </tr>
            )}

            {/* Grand Total */}
            <tr className="bg-gray-700/50">
              <td className="py-2 px-2 text-gray-100 font-semibold">Total</td>
              <td className="py-2 px-2 text-right text-gray-100 font-semibold">${formatCurrency(pb.per_piece_price || 0)}</td>
              <td className="py-2 px-2 text-right text-gray-100 font-semibold">{result.quantity.toLocaleString()}</td>
              <td className="py-2 px-2 text-right text-primary-400 font-semibold">${formatCurrency(pb.total || 0)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-3 p-2 bg-gray-700/30 rounded text-xs text-gray-400">
        * Pricing based on {pb.quantity_break.toLocaleString()}+ quantity break. Digitizing fee is waived at 144+ quantity.
      </div>
    </div>
  );
}

// Overseas Results Component - matches QuoteEstimator exactly
function OverseasResults({ result }: { result: OverseasQuoteResponse }) {
  if (!result.price_breaks || result.price_breaks.length === 0) return null;

  // Build hat details list
  const hatDetails: string[] = [];
  hatDetails.push(result.hat_type);
  if (isValidDecoration(result.front_decoration)) hatDetails.push(`Front: ${result.front_decoration}`);
  if (isValidDecoration(result.left_decoration)) hatDetails.push(`Left: ${result.left_decoration}`);
  if (isValidDecoration(result.right_decoration)) hatDetails.push(`Right: ${result.right_decoration}`);
  if (isValidDecoration(result.back_decoration)) hatDetails.push(`Back: ${result.back_decoration}`);
  if (isValidDecoration(result.visor_decoration)) hatDetails.push(`Visor: ${result.visor_decoration}`);
  if (result.design_addons && result.design_addons.length > 0) {
    hatDetails.push(`Add-ons: ${result.design_addons.join(', ')}`);
  }
  if (result.accessories && result.accessories.length > 0) {
    hatDetails.push(`Accessories: ${result.accessories.join(', ')}`);
  }

  // Check if a price break meets MOQ (per_piece_price is not null)
  const meetsMoq = (pb: typeof result.price_breaks[0]) => pb.per_piece_price !== null;

  // Calculate hat cost per piece for each quantity break
  const getHatCost = (pb: typeof result.price_breaks[0]) => {
    if (!meetsMoq(pb)) return null;
    return (
      (pb.blank_price || 0) +
      (pb.front_decoration_price || 0) +
      (pb.left_decoration_price || 0) +
      (pb.right_decoration_price || 0) +
      (pb.back_decoration_price || 0) +
      (pb.visor_decoration_price || 0) +
      (pb.addons_price || 0) +
      (pb.accessories_price || 0)
    );
  };

  // Format price or show "Does not meet MOQ"
  const formatPriceOrMoq = (value: number | null) => {
    if (value === null) return 'Does not meet MOQ';
    return `$${formatCurrency(value)}`;
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-lg font-semibold text-gray-100 mb-4">Quote Results - Overseas</h3>

      <div className="mb-4 p-3 bg-gray-700/50 rounded-lg">
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-gray-400">Hat Type:</span>
            <span className="text-gray-100 ml-2">{result.hat_type}</span>
          </div>
          <div>
            <span className="text-gray-400">Shipping:</span>
            <span className="text-gray-100 ml-2">{result.shipping_method}</span>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-600">
              <th className="text-left py-2 px-2 text-gray-400">Line Item</th>
              {result.price_breaks.map((pb) => (
                <th key={pb.quantity_break} className="text-right py-2 px-2 text-gray-400">
                  {pb.quantity_break.toLocaleString()}+
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* Hat (all non-shipping costs) */}
            <tr className="border-b border-gray-700">
              <td className="py-2 px-2 text-gray-100">
                <div>Hat</div>
                <div className="text-xs text-gray-400 max-w-[150px] truncate" title={hatDetails.join(' | ')}>
                  {hatDetails.slice(0, 2).join(' | ')}
                  {hatDetails.length > 2 && '...'}
                </div>
              </td>
              {result.price_breaks.map((pb) => {
                const hatCost = getHatCost(pb);
                return (
                  <td
                    key={pb.quantity_break}
                    className={`py-2 px-2 text-right ${hatCost === null ? 'text-gray-500 text-xs' : 'text-gray-100'}`}
                  >
                    {formatPriceOrMoq(hatCost)}
                  </td>
                );
              })}
            </tr>

            {/* Shipping */}
            <tr className="border-b border-gray-700">
              <td className="py-2 px-2 text-gray-100">
                <div>Shipping</div>
                <div className="text-xs text-gray-400">{result.shipping_method}</div>
              </td>
              {result.price_breaks.map((pb) => {
                const shippingCost = meetsMoq(pb) ? (pb.shipping_price || 0) : null;
                return (
                  <td
                    key={pb.quantity_break}
                    className={`py-2 px-2 text-right ${shippingCost === null ? 'text-gray-500 text-xs' : 'text-gray-100'}`}
                  >
                    {formatPriceOrMoq(shippingCost)}
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-3 p-2 bg-gray-700/30 rounded text-xs text-gray-400">
        * All prices shown are per piece at each quantity break
      </div>
    </div>
  );
}
