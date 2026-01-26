import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { ArrowLeft, Calculator, Download, Globe, Home, Plus, Trash2, FileSpreadsheet } from 'lucide-react';
import { quotesApi } from '../api/quotes';
import type {
  QuoteOptions,
  DomesticQuoteRequest,
  OverseasQuoteRequest,
  DomesticQuoteResponse,
  OverseasQuoteResponse,
} from '../api/quotes';
import clsx from 'clsx';

type QuoteType = 'domestic' | 'overseas';

// Type for saved quotes in the quote sheet
interface SavedQuote {
  id: string;
  type: 'domestic' | 'overseas';
  designNumber: string;
  request: DomesticQuoteRequest | OverseasQuoteRequest;
  result: DomesticQuoteResponse | OverseasQuoteResponse;
}

export function QuoteEstimator() {
  const [quoteType, setQuoteType] = useState<QuoteType>('domestic');
  const [options, setOptions] = useState<QuoteOptions | null>(null);
  const [isLoadingOptions, setIsLoadingOptions] = useState(true);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Domestic form state
  const [domesticForm, setDomesticForm] = useState<DomesticQuoteRequest>({
    design_number: '',
    style_number: '',
    quantity: 144,
    front_decoration: null,
    left_decoration: null,
    right_decoration: null,
    back_decoration: null,
    shipping_speed: 'Standard (5-7 Production Days)',
    include_rope: false,
    num_dst_files: 1,
  });

  // Overseas form state
  const [overseasForm, setOverseasForm] = useState<OverseasQuoteRequest>({
    design_number: '',
    hat_type: 'Classic',
    quantity: 5040,  // Set to max to get all price breaks
    front_decoration: null,
    left_decoration: null,
    right_decoration: null,
    back_decoration: null,
    visor_decoration: null,
    design_addons: [],
    accessories: [],
    shipping_method: 'FOB CA',
  });

  // Quote results
  const [domesticResult, setDomesticResult] = useState<DomesticQuoteResponse | null>(null);
  const [overseasResult, setOverseasResult] = useState<OverseasQuoteResponse | null>(null);

  // Quote sheet state - holds multiple quotes for export
  const [quoteSheet, setQuoteSheet] = useState<SavedQuote[]>([]);
  const [isExportingSheet, setIsExportingSheet] = useState(false);

  useEffect(() => {
    const loadOptions = async () => {
      try {
        const data = await quotesApi.getOptions();
        setOptions(data);
        // Set default values
        if (data.domestic.styles.length > 0) {
          setDomesticForm((prev) => ({ ...prev, style_number: data.domestic.styles[0].style_number }));
        }
      } catch (err) {
        setError('Failed to load quote options');
      } finally {
        setIsLoadingOptions(false);
      }
    };
    loadOptions();
  }, []);

  const handleCalculate = async () => {
    setIsCalculating(true);
    setError(null);

    try {
      if (quoteType === 'domestic') {
        const result = await quotesApi.calculateDomestic(domesticForm);
        setDomesticResult(result);
        setOverseasResult(null);
      } else {
        const result = await quotesApi.calculateOverseas(overseasForm);
        setOverseasResult(result);
        setDomesticResult(null);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to calculate quote');
    } finally {
      setIsCalculating(false);
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

  // Add current quote to the quote sheet
  const addToQuoteSheet = () => {
    const currentForm = quoteType === 'domestic' ? domesticForm : overseasForm;
    const currentResult = quoteType === 'domestic' ? domesticResult : overseasResult;

    if (!currentResult) return;

    const designNum = currentForm.design_number || `Design ${quoteSheet.length + 1}`;

    const newQuote: SavedQuote = {
      id: Date.now().toString(),
      type: quoteType,
      designNumber: designNum,
      request: { ...currentForm },
      result: currentResult,
    };

    setQuoteSheet((prev) => [...prev, newQuote]);

    // Clear the design number for the next quote
    if (quoteType === 'domestic') {
      setDomesticForm((prev) => ({ ...prev, design_number: '' }));
    } else {
      setOverseasForm((prev) => ({ ...prev, design_number: '' }));
    }
  };

  // Remove a quote from the quote sheet
  const removeFromQuoteSheet = (id: string) => {
    setQuoteSheet((prev) => prev.filter((q) => q.id !== id));
  };

  // Export the combined quote sheet
  const exportQuoteSheet = async () => {
    if (quoteSheet.length === 0) return;

    setIsExportingSheet(true);
    try {
      const blob = await quotesApi.exportQuoteSheet(
        quoteSheet.map((q) => ({
          type: q.type,
          design_number: q.designNumber,
          request: q.request,
        }))
      );
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `quote_sheet_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExportingSheet(false);
    }
  };

  if (isLoadingOptions) {
    return (
      <div className="min-h-screen bg-black">
        <Header />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/dashboard">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-100">Quote Estimator</h1>
              <p className="text-gray-400">Calculate pricing for domestic and overseas orders</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Form Section */}
          <div className="space-y-6">
            {/* Quote Type Toggle */}
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-100 mb-4">Quote Type</h2>
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

            {quoteType === 'domestic' ? (
              <DomesticForm
                form={domesticForm}
                setForm={setDomesticForm}
                options={options!.domestic}
              />
            ) : (
              <OverseasForm
                form={overseasForm}
                setForm={setOverseasForm}
                options={options!.overseas}
                toggleDesignAddon={toggleDesignAddon}
                toggleAccessory={toggleAccessory}
              />
            )}

            {error && <p className="text-red-500 text-sm">{error}</p>}

            <Button
              onClick={handleCalculate}
              isLoading={isCalculating}
              className="w-full"
              size="lg"
            >
              <Calculator className="w-5 h-5 mr-2" />
              Calculate Quote
            </Button>
          </div>

          {/* Results Section */}
          <div className="space-y-6">
            {domesticResult && <DomesticResults result={domesticResult} formData={domesticForm} />}
            {overseasResult && <OverseasResults result={overseasResult} formData={overseasForm} />}
            {!domesticResult && !overseasResult && (
              <div className="card text-center py-16">
                <Calculator className="w-12 h-12 mx-auto text-gray-600 mb-4" />
                <p className="text-gray-400">
                  Configure your quote options and click Calculate to see pricing
                </p>
              </div>
            )}

            {/* Save to Quote Sheet Button */}
            {(domesticResult || overseasResult) && (
              <Button
                onClick={addToQuoteSheet}
                variant="secondary"
                className="w-full"
                size="lg"
              >
                <Plus className="w-5 h-5 mr-2" />
                Save to Quote Sheet
              </Button>
            )}

            {/* Quote Sheet Display */}
            {quoteSheet.length > 0 && (
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-100">
                    <FileSpreadsheet className="w-5 h-5 inline-block mr-2" />
                    Quote Sheet ({quoteSheet.length} {quoteSheet.length === 1 ? 'design' : 'designs'})
                  </h2>
                  <Button
                    onClick={exportQuoteSheet}
                    isLoading={isExportingSheet}
                    size="sm"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Export Quote Sheet
                  </Button>
                </div>

                <div className="space-y-3">
                  {quoteSheet.map((quote) => (
                    <div
                      key={quote.id}
                      className="flex items-center justify-between p-3 bg-gray-800 rounded-lg"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-100">{quote.designNumber}</span>
                          <span className={clsx(
                            'text-xs px-2 py-0.5 rounded',
                            quote.type === 'domestic'
                              ? 'bg-blue-900/50 text-blue-300'
                              : 'bg-green-900/50 text-green-300'
                          )}>
                            {quote.type}
                          </span>
                        </div>
                        <div className="text-sm text-gray-400 mt-1">
                          {quote.type === 'domestic'
                            ? `${(quote.result as DomesticQuoteResponse).style_number} - ${(quote.result as DomesticQuoteResponse).quantity.toLocaleString()} pcs`
                            : `${(quote.result as OverseasQuoteResponse).hat_type}`
                          }
                        </div>
                      </div>
                      <button
                        onClick={() => removeFromQuoteSheet(quote.id)}
                        className="p-2 text-gray-400 hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

// Domestic Form Component
interface DomesticFormProps {
  form: DomesticQuoteRequest;
  setForm: React.Dispatch<React.SetStateAction<DomesticQuoteRequest>>;
  options: QuoteOptions['domestic'];
}

function DomesticForm({ form, setForm, options }: DomesticFormProps) {
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
      {/* Design Number */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">Design #</h2>
        <Input
          type="text"
          value={form.design_number || ''}
          onChange={(e) => setForm((prev) => ({ ...prev, design_number: e.target.value }))}
          placeholder="e.g., Design 1, ABC-001"
        />
        <p className="text-xs text-gray-500 mt-2">
          Optional identifier for this design in a multi-design quote sheet
        </p>
      </div>

      {/* Style Selection */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">Hat Style</h2>
        <div className="space-y-4">
          {Object.entries(stylesByCollection).map(([collection, styles]) => (
            <div key={collection}>
              <h3 className="text-sm font-medium text-gray-400 mb-2">{collection}</h3>
              <div className="grid grid-cols-2 gap-2">
                {styles.map((style) => (
                  <button
                    key={style.style_number}
                    type="button"
                    onClick={() => setForm((prev) => ({ ...prev, style_number: style.style_number }))}
                    className={clsx(
                      'p-3 rounded-lg border text-left transition-all',
                      form.style_number === style.style_number
                        ? 'border-primary-500 bg-primary-900/30 ring-2 ring-primary-500'
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
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">Quantity</h2>
        <Input
          type="number"
          value={form.quantity}
          onChange={(e) => setForm((prev) => ({ ...prev, quantity: parseInt(e.target.value) || 24 }))}
          min={24}
          placeholder="Enter quantity (min 24)"
        />
        <p className="text-xs text-gray-500 mt-2">
          Quantity breaks: {options.quantity_breaks.join(', ')}
        </p>
      </div>

      {/* Decoration Methods */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">Decoration Methods</h2>
        <div className="space-y-4">
          <div>
            <label className="label">Front (Primary)</label>
            <select
              value={form.front_decoration || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, front_decoration: e.target.value || null }))}
              className="input"
            >
              <option value="">None</option>
              {options.front_decoration_methods.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Left Side</label>
            <select
              value={form.left_decoration || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, left_decoration: e.target.value || null }))}
              className="input"
            >
              <option value="">None</option>
              {options.additional_decoration_methods.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Right Side</label>
            <select
              value={form.right_decoration || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, right_decoration: e.target.value || null }))}
              className="input"
            >
              <option value="">None</option>
              {options.additional_decoration_methods.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Back</label>
            <select
              value={form.back_decoration || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, back_decoration: e.target.value || null }))}
              className="input"
            >
              <option value="">None</option>
              {options.additional_decoration_methods.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Add-ons & Shipping */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">Add-ons & Shipping</h2>
        <div className="space-y-4">
          <div>
            <label className="label">Shipping Speed</label>
            <select
              value={form.shipping_speed}
              onChange={(e) => setForm((prev) => ({ ...prev, shipping_speed: e.target.value }))}
              className="input"
            >
              {options.shipping_speeds.map((speed) => (
                <option key={speed} value={speed}>
                  {speed}
                </option>
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
            <label className="label"># of DST Files (Digitizing)</label>
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

// Overseas Form Component
interface OverseasFormProps {
  form: OverseasQuoteRequest;
  setForm: React.Dispatch<React.SetStateAction<OverseasQuoteRequest>>;
  options: QuoteOptions['overseas'];
  toggleDesignAddon: (addon: string) => void;
  toggleAccessory: (accessory: string) => void;
}

function OverseasForm({ form, setForm, options, toggleDesignAddon, toggleAccessory }: OverseasFormProps) {
  return (
    <div className="space-y-6">
      {/* Design Number */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">Design #</h2>
        <Input
          type="text"
          value={form.design_number || ''}
          onChange={(e) => setForm((prev) => ({ ...prev, design_number: e.target.value }))}
          placeholder="e.g., Design 1, ABC-001"
        />
        <p className="text-xs text-gray-500 mt-2">
          Optional identifier for this design in a multi-design quote sheet
        </p>
      </div>

      {/* Hat Type */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">Hat Type</h2>
        <div className="grid grid-cols-2 gap-2">
          {options.hat_types.map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => setForm((prev) => ({ ...prev, hat_type: type }))}
              className={clsx(
                'p-4 rounded-lg border text-center transition-all',
                form.hat_type === type
                  ? 'border-primary-500 bg-primary-900/30 ring-2 ring-primary-500'
                  : 'border-gray-700 hover:border-gray-600 bg-gray-800'
              )}
            >
              <div className="font-medium text-gray-100">{type}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Decoration Methods */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">Decoration Methods</h2>
        <div className="space-y-4">
          <div>
            <label className="label">Front</label>
            <select
              value={form.front_decoration || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, front_decoration: e.target.value || null }))}
              className="input"
            >
              <option value="">None</option>
              {options.decoration_methods.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Left Side</label>
            <select
              value={form.left_decoration || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, left_decoration: e.target.value || null }))}
              className="input"
            >
              <option value="">None</option>
              {options.decoration_methods.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Right Side</label>
            <select
              value={form.right_decoration || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, right_decoration: e.target.value || null }))}
              className="input"
            >
              <option value="">None</option>
              {options.decoration_methods.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Back</label>
            <select
              value={form.back_decoration || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, back_decoration: e.target.value || null }))}
              className="input"
            >
              <option value="">None</option>
              {options.decoration_methods.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Visor</label>
            <select
              value={form.visor_decoration || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, visor_decoration: e.target.value || null }))}
              className="input"
            >
              <option value="">None</option>
              {options.decoration_methods.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Design Add-ons */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">Design Add-ons</h2>
        <div className="grid grid-cols-2 gap-2">
          {options.design_addons.map((addon) => (
            <button
              key={addon}
              type="button"
              onClick={() => toggleDesignAddon(addon)}
              className={clsx(
                'p-3 rounded-lg border text-left transition-all text-sm',
                form.design_addons?.includes(addon)
                  ? 'border-primary-500 bg-primary-900/30'
                  : 'border-gray-700 hover:border-gray-600 bg-gray-800'
              )}
            >
              <span className="text-gray-100">{addon}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Accessories */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">Accessories</h2>
        <div className="grid grid-cols-2 gap-2">
          {options.accessories.map((accessory) => (
            <button
              key={accessory}
              type="button"
              onClick={() => toggleAccessory(accessory)}
              className={clsx(
                'p-3 rounded-lg border text-left transition-all text-sm',
                form.accessories?.includes(accessory)
                  ? 'border-primary-500 bg-primary-900/30'
                  : 'border-gray-700 hover:border-gray-600 bg-gray-800'
              )}
            >
              <span className="text-gray-100">{accessory}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Shipping Method */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">Shipping Method</h2>
        <div className="grid grid-cols-2 gap-2">
          {options.shipping_methods.map((method) => (
            <button
              key={method}
              type="button"
              onClick={() => setForm((prev) => ({ ...prev, shipping_method: method }))}
              className={clsx(
                'p-4 rounded-lg border text-center transition-all',
                form.shipping_method === method
                  ? 'border-primary-500 bg-primary-900/30 ring-2 ring-primary-500'
                  : 'border-gray-700 hover:border-gray-600 bg-gray-800'
              )}
            >
              <div className="font-medium text-gray-100">{method}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// Helper function to format currency with commas
function formatCurrency(value: number): string {
  return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Helper to check if a decoration value is valid (not null, empty, or "0")
function isValidDecoration(value: string | null | undefined): boolean {
  return typeof value === 'string' && value.trim().length > 0 && value !== '0';
}

// Domestic Results Component
function DomesticResults({ result, formData }: { result: DomesticQuoteResponse; formData: DomesticQuoteRequest }) {
  const [isExporting, setIsExporting] = useState(false);

  // Get the applicable price break (the last one that applies to the quantity)
  const pb = result.price_breaks[result.price_breaks.length - 1];

  // Check for valid decoration values
  const hasFront = isValidDecoration(result.front_decoration);
  const hasLeft = isValidDecoration(result.left_decoration);
  const hasRight = isValidDecoration(result.right_decoration);
  const hasBack = isValidDecoration(result.back_decoration);
  const hasRushFee = pb?.rush_fee && pb.rush_fee > 0;
  const hasRope = result.include_rope && pb?.rope_price && pb.rope_price > 0;

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const blob = await quotesApi.exportDomestic(formData);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `domestic_quote_${result.style_number}_${result.quantity}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
    }
  };

  if (!pb) return null;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-100">Quote Results - Domestic</h2>
        <Button variant="secondary" size="sm" onClick={handleExport} isLoading={isExporting}>
          <Download className="w-4 h-4 mr-2" />
          Export Excel
        </Button>
      </div>

      <div className="mb-6 p-4 bg-gray-800 rounded-lg">
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
            <tr className="border-b border-gray-700">
              <th className="text-left py-3 px-3 text-gray-400">Line Item</th>
              <th className="text-right py-3 px-3 text-gray-400">Per Piece</th>
              <th className="text-right py-3 px-3 text-gray-400">Qty</th>
              <th className="text-right py-3 px-3 text-gray-400">Total</th>
            </tr>
          </thead>
          <tbody>
            {/* Blank Hat */}
            <tr className="border-b border-gray-800">
              <td className="py-3 px-3 text-gray-100">Blank Hat</td>
              <td className="py-3 px-3 text-right text-gray-100">${formatCurrency(pb.blank_price || 0)}</td>
              <td className="py-3 px-3 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
              <td className="py-3 px-3 text-right text-gray-100">${formatCurrency((pb.blank_price || 0) * result.quantity)}</td>
            </tr>

            {/* Front Decoration */}
            {hasFront && (
              <tr className="border-b border-gray-800">
                <td className="py-3 px-3 text-gray-100">
                  <div>Front Decoration</div>
                  <div className="text-xs text-gray-400">{result.front_decoration}</div>
                </td>
                <td className="py-3 px-3 text-right text-gray-100">${formatCurrency(pb.front_decoration_price || 0)}</td>
                <td className="py-3 px-3 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
                <td className="py-3 px-3 text-right text-gray-100">${formatCurrency((pb.front_decoration_price || 0) * result.quantity)}</td>
              </tr>
            )}

            {/* Left Decoration */}
            {hasLeft && (
              <tr className="border-b border-gray-800">
                <td className="py-3 px-3 text-gray-100">
                  <div>Left Side Decoration</div>
                  <div className="text-xs text-gray-400">{result.left_decoration}</div>
                </td>
                <td className="py-3 px-3 text-right text-gray-100">${formatCurrency(pb.left_decoration_price || 0)}</td>
                <td className="py-3 px-3 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
                <td className="py-3 px-3 text-right text-gray-100">${formatCurrency((pb.left_decoration_price || 0) * result.quantity)}</td>
              </tr>
            )}

            {/* Right Decoration */}
            {hasRight && (
              <tr className="border-b border-gray-800">
                <td className="py-3 px-3 text-gray-100">
                  <div>Right Side Decoration</div>
                  <div className="text-xs text-gray-400">{result.right_decoration}</div>
                </td>
                <td className="py-3 px-3 text-right text-gray-100">${formatCurrency(pb.right_decoration_price || 0)}</td>
                <td className="py-3 px-3 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
                <td className="py-3 px-3 text-right text-gray-100">${formatCurrency((pb.right_decoration_price || 0) * result.quantity)}</td>
              </tr>
            )}

            {/* Back Decoration */}
            {hasBack && (
              <tr className="border-b border-gray-800">
                <td className="py-3 px-3 text-gray-100">
                  <div>Back Decoration</div>
                  <div className="text-xs text-gray-400">{result.back_decoration}</div>
                </td>
                <td className="py-3 px-3 text-right text-gray-100">${formatCurrency(pb.back_decoration_price || 0)}</td>
                <td className="py-3 px-3 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
                <td className="py-3 px-3 text-right text-gray-100">${formatCurrency((pb.back_decoration_price || 0) * result.quantity)}</td>
              </tr>
            )}

            {/* Rush Fee */}
            {hasRushFee && (
              <tr className="border-b border-gray-800">
                <td className="py-3 px-3 text-gray-100">Rush Fee</td>
                <td className="py-3 px-3 text-right text-gray-100">${formatCurrency(pb.rush_fee || 0)}</td>
                <td className="py-3 px-3 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
                <td className="py-3 px-3 text-right text-gray-100">${formatCurrency((pb.rush_fee || 0) * result.quantity)}</td>
              </tr>
            )}

            {/* Rope */}
            {hasRope && (
              <tr className="border-b border-gray-800">
                <td className="py-3 px-3 text-gray-100">Rope</td>
                <td className="py-3 px-3 text-right text-gray-100">${formatCurrency(pb.rope_price || 0)}</td>
                <td className="py-3 px-3 text-right text-gray-100">{result.quantity.toLocaleString()}</td>
                <td className="py-3 px-3 text-right text-gray-100">${formatCurrency((pb.rope_price || 0) * result.quantity)}</td>
              </tr>
            )}

            {/* Digitizing Fee */}
            {(pb.digitizing_fee ?? 0) > 0 && (
              <tr className="border-b border-gray-800">
                <td className="py-3 px-3 text-gray-100">Digitizing Fee</td>
                <td className="py-3 px-3 text-right text-gray-400">-</td>
                <td className="py-3 px-3 text-right text-gray-400">1</td>
                <td className="py-3 px-3 text-right text-gray-100">${formatCurrency(pb.digitizing_fee ?? 0)}</td>
              </tr>
            )}

            {/* Grand Total */}
            <tr className="bg-gray-800/50">
              <td className="py-3 px-3 text-gray-100 font-semibold">Total</td>
              <td className="py-3 px-3 text-right text-gray-100 font-semibold">${formatCurrency(pb.per_piece_price || 0)}</td>
              <td className="py-3 px-3 text-right text-gray-100 font-semibold">{result.quantity.toLocaleString()}</td>
              <td className="py-3 px-3 text-right text-primary-400 font-semibold">${formatCurrency(pb.total || 0)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-4 p-3 bg-gray-800 rounded-lg">
        <p className="text-sm text-gray-400">
          * Pricing based on {pb.quantity_break.toLocaleString()}+ quantity break. Digitizing fee is waived at 144+ quantity.
        </p>
      </div>
    </div>
  );
}

// Overseas Results Component
function OverseasResults({ result, formData }: { result: OverseasQuoteResponse; formData: OverseasQuoteRequest }) {
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const blob = await quotesApi.exportOverseas(formData);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `overseas_quote_${result.hat_type.toLowerCase().replace(' ', '_')}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
    }
  };

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
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-100">Quote Results - Overseas</h2>
        <Button variant="secondary" size="sm" onClick={handleExport} isLoading={isExporting}>
          <Download className="w-4 h-4 mr-2" />
          Export Excel
        </Button>
      </div>

      <div className="mb-6 p-4 bg-gray-800 rounded-lg">
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
            <tr className="border-b border-gray-700">
              <th className="text-left py-3 px-3 text-gray-400">Line Item</th>
              {result.price_breaks.map((pb) => (
                <th key={pb.quantity_break} className="text-right py-3 px-3 text-gray-400">
                  {pb.quantity_break.toLocaleString()}+
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* Hat (all non-shipping costs) */}
            <tr className="border-b border-gray-800">
              <td className="py-3 px-3 text-gray-100">
                <div>Hat</div>
                <div className="text-xs text-gray-400">{hatDetails.join(' | ')}</div>
              </td>
              {result.price_breaks.map((pb) => {
                const hatCost = getHatCost(pb);
                return (
                  <td
                    key={pb.quantity_break}
                    className={`py-3 px-3 text-right ${hatCost === null ? 'text-gray-500 text-xs' : 'text-gray-100'}`}
                  >
                    {formatPriceOrMoq(hatCost)}
                  </td>
                );
              })}
            </tr>

            {/* Shipping */}
            <tr className="border-b border-gray-800">
              <td className="py-3 px-3 text-gray-100">
                <div>Shipping</div>
                <div className="text-xs text-gray-400">{result.shipping_method}</div>
              </td>
              {result.price_breaks.map((pb) => {
                const shippingCost = meetsMoq(pb) ? (pb.shipping_price || 0) : null;
                return (
                  <td
                    key={pb.quantity_break}
                    className={`py-3 px-3 text-right ${shippingCost === null ? 'text-gray-500 text-xs' : 'text-gray-100'}`}
                  >
                    {formatPriceOrMoq(shippingCost)}
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-4 p-3 bg-gray-800 rounded-lg">
        <p className="text-sm text-gray-400">
          * All prices shown are per piece at each quantity break
        </p>
      </div>
    </div>
  );
}
