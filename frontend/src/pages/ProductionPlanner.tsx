import { useState } from 'react';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/Button';
import {
  CalendarDays, ArrowLeft, Copy, Check, List, Calendar,
  Palette, FileText, Camera, PlaneTakeoff, Warehouse, Package,
  Zap, Info, Truck, Globe, Home,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Link } from 'react-router-dom';

type ProductionType = 'overseas' | 'domestic';

const DOMESTIC_PRODUCTION_SPEEDS: { label: string; days: number; fee: string }[] = [
  { label: 'Standard (5-7 Production Days)', days: 7, fee: 'No charge' },
  { label: 'Rush (4 Production Days)', days: 4, fee: '+$2.00/piece' },
  { label: 'Rush (3 Production Days)', days: 3, fee: '+$2.50/piece' },
  { label: 'Rush (2 Production Days)', days: 2, fee: '+$3.00/piece' },
];

const DOMESTIC_SHIPPING_METHODS: { label: string; days: number }[] = [
  { label: 'Ground (5 days)', days: 5 },
  { label: 'Express (3 days)', days: 3 },
  { label: 'Priority (2 days)', days: 2 },
  { label: 'Overnight (1 day)', days: 1 },
];

interface Milestone {
  label: string;
  date: Date;
  description: string;
  color: string;
  dotColor: string;
  labelColor: string;
  dateColor: string;
  icon: LucideIcon;
}

// Quick Turn eligible decoration methods
const QUICK_TURN_METHODS = [
  'Flat Embroidery',
  '3D Embroidery',
  'Sublimated Patch',
  'Sublimated Label',
];

// Standard production decoration methods (35 days)
const STANDARD_ONLY_METHODS = [
  'Woven Patch',
  'Embroidered Patch',
  'Leather Patch',
  'Suede Patch',
  'Mesh Patch',
  'Distressed Patch',
  'PVC Patch',
  'High Density Print',
  'Heat Transfer',
  'TPU Heat Transfer',
  'Metallic Heat Transfer',
  'Flocking Heat Transfer',
  'AI Embroidery',
  '3D + Flat Embroidery',
  'Faux Leather Laser Patch',
];

function toWeekday(date: Date): Date {
  const result = new Date(date);
  const dow = result.getDay();
  if (dow === 0) result.setDate(result.getDate() + 1); // Sunday → Monday
  if (dow === 6) result.setDate(result.getDate() + 2); // Saturday → Monday
  return result;
}

function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function daysFromNow(date: Date): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(date);
  target.setHours(0, 0, 0, 0);
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

function calculateMilestones(inHandsDate: Date, shipDirect: boolean, quickTurn: boolean): Milestone[] {
  const exitFactoryDays = shipDirect ? -7 : -14;
  const exitFactory = toWeekday(addDays(inHandsDate, exitFactoryDays));
  const productionDays = quickTurn ? 21 : 35;
  const samplesDue = toWeekday(addDays(exitFactory, -productionDays));
  const productionFilesLocked = toWeekday(addDays(samplesDue, -18));
  const artworkLocked = toWeekday(addDays(productionFilesLocked, -7));

  const milestones: Milestone[] = [
    {
      label: 'Artwork Due',
      date: artworkLocked,
      description: 'All artwork and design files finalized and approved by customer',
      color: 'from-blue-500 to-cyan-500',
      dotColor: 'bg-blue-500',
      labelColor: 'text-blue-300',
      dateColor: 'text-blue-400',
      icon: Palette,
    },
    {
      label: 'Production Files Due',
      date: productionFilesLocked,
      description: 'Final production-ready files (DST, vectors) submitted to factory',
      color: 'from-purple-500 to-indigo-500',
      dotColor: 'bg-purple-500',
      labelColor: 'text-purple-300',
      dateColor: 'text-purple-400',
      icon: FileText,
    },
    {
      label: 'Sample Picture Expected',
      date: samplesDue,
      description: 'Pre-production sample received for approval',
      color: 'from-amber-500 to-orange-500',
      dotColor: 'bg-amber-500',
      labelColor: 'text-amber-300',
      dateColor: 'text-amber-400',
      icon: Camera,
    },
    {
      label: 'Order Shipped from Factory',
      date: exitFactory,
      description: shipDirect ? 'Finished product ships direct to customer' : 'Finished product ships from factory to King Cap',
      color: 'from-emerald-500 to-green-500',
      dotColor: 'bg-emerald-500',
      labelColor: 'text-emerald-300',
      dateColor: 'text-emerald-400',
      icon: PlaneTakeoff,
    },
  ];

  if (!shipDirect) {
    milestones.push({
      label: 'Delivered to King Cap',
      date: toWeekday(addDays(exitFactory, 7)),
      description: 'Product arrives at King Cap for QC and fulfillment',
      color: 'from-sky-500 to-blue-500',
      dotColor: 'bg-sky-500',
      labelColor: 'text-sky-300',
      dateColor: 'text-sky-400',
      icon: Warehouse,
    });
  }

  milestones.push({
    label: 'Order Delivered',
    date: inHandsDate,
    description: shipDirect ? 'Product delivered to customer from factory' : 'Product shipped from King Cap and delivered to customer',
    color: 'from-rose-500 to-pink-500',
    dotColor: 'bg-rose-500',
    labelColor: 'text-rose-300',
    dateColor: 'text-rose-400',
    icon: Package,
  });

  return milestones;
}

function subtractBusinessDays(date: Date, days: number): Date {
  const result = new Date(date);
  let remaining = days;
  while (remaining > 0) {
    result.setDate(result.getDate() - 1);
    if (result.getDay() !== 0 && result.getDay() !== 6) remaining--;
  }
  return result;
}

function calculateDomesticMilestones(inHandsDate: Date, shippingDays: number, productionDays: number): Milestone[] {
  // Work backwards from in-hands date:
  // delivery date = in-hands date
  // production complete = shippingDays business days before delivery
  const productionComplete = subtractBusinessDays(inHandsDate, shippingDays);
  // sample picture = productionDays business days before production complete
  const samplePicture = subtractBusinessDays(productionComplete, productionDays);
  // artwork submitted = 3 business days before sample picture
  const artworkSubmitted = subtractBusinessDays(samplePicture, 3);

  return [
    {
      label: 'Artwork Submitted',
      date: artworkSubmitted,
      description: 'Artwork files submitted to production',
      color: 'from-blue-500 to-cyan-500',
      dotColor: 'bg-blue-500',
      labelColor: 'text-blue-300',
      dateColor: 'text-blue-400',
      icon: Palette,
    },
    {
      label: 'Sample Picture Expected',
      date: samplePicture,
      description: '3 business days after artwork submission',
      color: 'from-amber-500 to-orange-500',
      dotColor: 'bg-amber-500',
      labelColor: 'text-amber-300',
      dateColor: 'text-amber-400',
      icon: Camera,
    },
    {
      label: 'Production Complete',
      date: productionComplete,
      description: `${productionDays} business day${productionDays > 1 ? 's' : ''} after sample picture`,
      color: 'from-emerald-500 to-green-500',
      dotColor: 'bg-emerald-500',
      labelColor: 'text-emerald-300',
      dateColor: 'text-emerald-400',
      icon: Package,
    },
    {
      label: 'Order Delivered',
      date: inHandsDate,
      description: `${shippingDays} business day${shippingDays > 1 ? 's' : ''} after production complete`,
      color: 'from-rose-500 to-pink-500',
      dotColor: 'bg-rose-500',
      labelColor: 'text-rose-300',
      dateColor: 'text-rose-400',
      icon: Truck,
    },
  ];
}

// --- Calendar View ---

function getCalendarDays(milestones: Milestone[]): { year: number; month: number }[] {
  const months: { year: number; month: number }[] = [];
  const start = new Date(milestones[0].date);
  const end = new Date(milestones[milestones.length - 1].date);
  start.setDate(1);

  while (start <= end) {
    months.push({ year: start.getFullYear(), month: start.getMonth() });
    start.setMonth(start.getMonth() + 1);
  }
  return months;
}

const MILESTONE_RING_COLORS: Record<string, string> = {
  'bg-blue-500': 'ring-blue-500 bg-blue-500/20 text-blue-300',
  'bg-purple-500': 'ring-purple-500 bg-purple-500/20 text-purple-300',
  'bg-amber-500': 'ring-amber-500 bg-amber-500/20 text-amber-300',
  'bg-emerald-500': 'ring-emerald-500 bg-emerald-500/20 text-emerald-300',
  'bg-sky-500': 'ring-sky-500 bg-sky-500/20 text-sky-300',
  'bg-rose-500': 'ring-rose-500 bg-rose-500/20 text-rose-300',
};

function CalendarMonth({ year, month, milestones }: { year: number; month: number; milestones: Milestone[] }) {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startDow = firstDay.getDay();
  const daysInMonth = lastDay.getDate();
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const monthName = firstDay.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  const milestoneDays: Record<number, Milestone> = {};
  for (const m of milestones) {
    if (m.date.getFullYear() === year && m.date.getMonth() === month) {
      milestoneDays[m.date.getDate()] = m;
    }
  }

  const cells: (number | null)[] = [];
  for (let i = 0; i < startDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  return (
    <div className="card">
      <h3 className="text-white font-semibold mb-3 text-center">{monthName}</h3>
      <div className="grid grid-cols-7 gap-1 text-center text-xs">
        {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map((d) => (
          <div key={d} className="text-gray-500 font-medium py-1">{d}</div>
        ))}
        {cells.map((day, i) => {
          if (day === null) return <div key={`empty-${i}`} />;
          const milestone = milestoneDays[day];
          const cellDate = new Date(year, month, day);
          cellDate.setHours(0, 0, 0, 0);
          const isToday = cellDate.getTime() === today.getTime();
          const ringStyle = milestone ? MILESTONE_RING_COLORS[milestone.dotColor] || '' : '';

          return (
            <div
              key={day}
              className={`relative flex items-center justify-center w-8 h-8 mx-auto rounded-full text-sm ${
                milestone
                  ? `ring-2 ${ringStyle} font-bold`
                  : isToday
                  ? 'text-teal-400 font-medium ring-1 ring-teal-500/50'
                  : 'text-gray-400'
              }`}
              title={milestone ? `${milestone.label}: ${formatDate(milestone.date)}` : undefined}
            >
              {day}
            </div>
          );
        })}
      </div>
      {Object.keys(milestoneDays).length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-800 space-y-2">
          {Object.entries(milestoneDays).map(([day, m]) => {
            const ringStyle = MILESTONE_RING_COLORS[m.dotColor] || '';
            const Icon = m.icon;
            return (
              <div key={day} className="flex items-center gap-2.5 text-xs">
                <div className={`w-6 h-6 rounded-full ring-2 ${ringStyle} flex items-center justify-center text-[10px] font-bold flex-shrink-0`}>
                  {Number(day)}
                </div>
                <Icon className={`w-3.5 h-3.5 ${m.labelColor} flex-shrink-0`} />
                <span className="text-gray-200 font-medium">{m.label}</span>
                <span className="text-gray-500 ml-auto">{formatDate(m.date)}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// --- Main Component ---

export function ProductionPlanner() {
  const [inHandsDate, setInHandsDate] = useState('');
  const [productionType, setProductionType] = useState<ProductionType>('overseas');
  const [shipDirect, setShipDirect] = useState(false);
  const [quickTurn, setQuickTurn] = useState(false);
  const [domesticProductionDays, setDomesticProductionDays] = useState(7);
  const [domesticShippingDays, setDomesticShippingDays] = useState(5);
  const [milestones, setMilestones] = useState<Milestone[] | null>(null);
  const [copied, setCopied] = useState(false);
  const [view, setView] = useState<'timeline' | 'calendar'>('timeline');

  const recalculate = (date?: string, pt?: ProductionType, sd?: boolean, qt?: boolean, dpd?: number, dsd?: number) => {
    const d = date ?? inHandsDate;
    if (!d) return;
    const type = pt ?? productionType;
    if (type === 'domestic') {
      setMilestones(calculateDomesticMilestones(new Date(d + 'T00:00:00'), dsd ?? domesticShippingDays, dpd ?? domesticProductionDays));
    } else {
      setMilestones(calculateMilestones(new Date(d + 'T00:00:00'), sd ?? shipDirect, qt ?? quickTurn));
    }
  };

  const handleCalculate = () => recalculate();

  const handleCopyTimeline = () => {
    if (!milestones) return;
    const lines = milestones.map((m) => `${m.label}: ${formatDate(m.date)}`);
    if (productionType === 'overseas') {
      if (quickTurn) lines.unshift('** Quick Turn Production (21 days) **');
      if (shipDirect) lines.unshift('** Ship Direct **');
      lines.unshift('** Overseas Production **');
    } else {
      const prodSpeed = DOMESTIC_PRODUCTION_SPEEDS.find((s) => s.days === domesticProductionDays);
      lines.unshift(`** Domestic Production — ${prodSpeed?.label || domesticProductionDays + ' days'} | ${domesticShippingDays}-day shipping **`);
    }
    navigator.clipboard.writeText(lines.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleCalculate();
  };

  const handleProductionTypeChange = (type: ProductionType) => {
    setProductionType(type);
    recalculate(undefined, type);
  };

  const handleShipDirectChange = (checked: boolean) => {
    setShipDirect(checked);
    recalculate(undefined, undefined, checked, undefined);
  };

  const handleQuickTurnChange = (checked: boolean) => {
    setQuickTurn(checked);
    recalculate(undefined, undefined, undefined, checked);
  };

  const handleDomesticProductionChange = (days: number) => {
    setDomesticProductionDays(days);
    recalculate(undefined, undefined, undefined, undefined, days);
  };

  const handleDomesticShippingChange = (days: number) => {
    setDomesticShippingDays(days);
    recalculate(undefined, undefined, undefined, undefined, undefined, days);
  };

  return (
    <div className="min-h-screen bg-black">
      <Header />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link to="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-teal-500 to-emerald-500 flex items-center justify-center">
              <CalendarDays className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-100">Production Planner</h1>
              <p className="text-gray-400 text-sm">Calculate production milestones from an in-hands date</p>
            </div>
          </div>
        </div>

        {/* Input */}
        <div className="card mb-8">
          {/* Production Type Toggle */}
          <div className="flex items-center bg-gray-800 rounded-lg p-1 mb-5">
            <button
              onClick={() => handleProductionTypeChange('overseas')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                productionType === 'overseas' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-gray-300'
              }`}
            >
              <Globe className="w-4 h-4" />
              Overseas
            </button>
            <button
              onClick={() => handleProductionTypeChange('domestic')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                productionType === 'domestic' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-gray-300'
              }`}
            >
              <Home className="w-4 h-4" />
              Domestic
            </button>
          </div>

          <label className="block text-sm font-medium text-gray-300 mb-2">
            In-Hands Date (when the customer needs the product)
          </label>
          <div className="flex gap-3 mb-5">
            <input
              type="date"
              value={inHandsDate}
              min={new Date().toISOString().split('T')[0]}
              onChange={(e) => setInHandsDate(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none [color-scheme:dark]"
            />
            <Button onClick={handleCalculate} disabled={!inHandsDate}>
              Calculate
            </Button>
          </div>

          {/* Overseas Options */}
          {productionType === 'overseas' && (
            <div className="space-y-4">
              {/* Quick Turn toggle */}
              <div className="flex items-start gap-3">
                <label className="flex items-center gap-3 cursor-pointer flex-shrink-0">
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={quickTurn}
                      onChange={(e) => handleQuickTurnChange(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-10 h-5 bg-gray-700 rounded-full peer-checked:bg-amber-500 transition-colors" />
                    <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
                  </div>
                  <div>
                    <span className="text-sm text-gray-300 font-medium flex items-center gap-1.5">
                      <Zap className="w-3.5 h-3.5 text-amber-400" />
                      Quick Turn
                    </span>
                    <span className="text-xs text-gray-500 block">21-day production instead of 35</span>
                  </div>
                </label>
              </div>

              {/* Quick Turn decoration info */}
              {quickTurn && (
                <div className="ml-[52px] p-3 bg-amber-900/15 border border-amber-800/30 rounded-lg">
                  <div className="flex items-start gap-2">
                    <Info className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-xs font-medium text-amber-300 mb-2">Quick Turn eligible decoration methods:</p>
                      <div className="flex flex-wrap gap-1.5 mb-2">
                        {QUICK_TURN_METHODS.map((m) => (
                          <span key={m} className="px-2 py-0.5 bg-amber-800/30 text-amber-300 text-xs rounded-full">{m}</span>
                        ))}
                      </div>
                      <p className="text-xs text-gray-500 mt-2">The following methods require standard 35-day production:</p>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {STANDARD_ONLY_METHODS.map((m) => (
                          <span key={m} className="px-2 py-0.5 bg-gray-800 text-gray-400 text-xs rounded-full">{m}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Ship Direct toggle */}
              <label className="flex items-center gap-3 cursor-pointer">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={shipDirect}
                    onChange={(e) => handleShipDirectChange(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-gray-700 rounded-full peer-checked:bg-teal-500 transition-colors" />
                  <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
                </div>
                <div>
                  <span className="text-sm text-gray-300 font-medium">Ship Direct</span>
                  <span className="text-xs text-gray-500 block">Factory ships directly to customer — 7 days transit instead of 14</span>
                </div>
              </label>
            </div>
          )}

          {/* Domestic Options */}
          {productionType === 'domestic' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Production Speed</label>
                <select
                  value={domesticProductionDays}
                  onChange={(e) => handleDomesticProductionChange(Number(e.target.value))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm text-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none [color-scheme:dark]"
                >
                  {DOMESTIC_PRODUCTION_SPEEDS.map((speed) => (
                    <option key={speed.days} value={speed.days}>
                      {speed.label} — {speed.fee}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Shipping Method</label>
                <select
                  value={domesticShippingDays}
                  onChange={(e) => handleDomesticShippingChange(Number(e.target.value))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm text-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none [color-scheme:dark]"
                >
                  {DOMESTIC_SHIPPING_METHODS.map((method) => (
                    <option key={method.days} value={method.days}>
                      {method.label}
                    </option>
                  ))}
                </select>
              </div>
              {domesticProductionDays < 7 && (
                <div className="p-3 bg-amber-900/15 border border-amber-800/30 rounded-lg">
                  <p className="text-xs text-amber-300 flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5 flex-shrink-0" />
                    Rush fee: {DOMESTIC_PRODUCTION_SPEEDS.find((s) => s.days === domesticProductionDays)?.fee || ''} per piece
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Results */}
        {milestones && (
          <div className="space-y-4">
            {/* Summary card — above timeline */}
            <div className="card bg-gray-900/50 border border-gray-800">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-gray-400">Timeline Summary</h3>
                <Button variant="outline" size="sm" onClick={handleCopyTimeline}>
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 mr-1.5" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5 mr-1.5" />
                      Copy
                    </>
                  )}
                </Button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Total lead time</p>
                  <p className="text-white font-semibold">
                    {Math.abs(daysFromNow(milestones[0].date) - daysFromNow(milestones[milestones.length - 1].date))} days
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">Days until delivery</p>
                  <p className="text-white font-semibold">{daysFromNow(milestones[milestones.length - 1].date)} days</p>
                </div>
                <div>
                  <p className="text-gray-500">Production</p>
                  <p className="text-white font-semibold flex items-center gap-1.5">
                    {productionType === 'overseas' ? (
                      <>
                        {quickTurn && <Zap className="w-3.5 h-3.5 text-amber-400" />}
                        {quickTurn ? 'Quick Turn (21 days)' : 'Standard (35 days)'}
                      </>
                    ) : (
                      <>
                        <Home className="w-3.5 h-3.5 text-teal-400" />
                        {domesticProductionDays < 7 ? `Rush (${domesticProductionDays} biz days)` : `Standard (${domesticProductionDays} biz days)`}
                      </>
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">Shipping</p>
                  <p className="text-white font-semibold">
                    {productionType === 'overseas'
                      ? (shipDirect ? 'Direct (7 days)' : 'Standard (14 days)')
                      : `${domesticShippingDays} day${domesticShippingDays > 1 ? 's' : ''}`
                    }
                  </p>
                </div>
              </div>
            </div>

            {/* View toggle header */}
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-100">Production Timeline</h2>
              <div className="flex items-center bg-gray-800 rounded-lg p-0.5">
                <button
                  onClick={() => setView('timeline')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                    view === 'timeline' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-gray-300'
                  }`}
                >
                  <List className="w-3.5 h-3.5" />
                  List
                </button>
                <button
                  onClick={() => setView('calendar')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                    view === 'calendar' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-gray-300'
                  }`}
                >
                  <Calendar className="w-3.5 h-3.5" />
                  Calendar
                </button>
              </div>
            </div>

            {/* Timeline (List) View */}
            {view === 'timeline' && (() => {
              const today = new Date();
              today.setHours(0, 0, 0, 0);

              let todayAfterIndex = -1;
              for (let i = 0; i < milestones.length; i++) {
                const mDate = new Date(milestones[i].date);
                mDate.setHours(0, 0, 0, 0);
                if (today.getTime() >= mDate.getTime()) {
                  todayAfterIndex = i;
                }
              }
              const todayOnMilestone = milestones.some((m) => {
                const mDate = new Date(m.date);
                mDate.setHours(0, 0, 0, 0);
                return today.getTime() === mDate.getTime();
              });

              const formatGap = (d: number) => {
                if (d % 7 === 0 && d >= 14) return `${d / 7} weeks`;
                if (d === 7) return '1 week';
                return `${d} days`;
              };

              const TodayMarker = () => (
                <div className="relative flex items-center gap-4 py-3">
                  <div className="relative z-10 w-4 flex-shrink-0 flex justify-center">
                    <div className="w-2.5 h-2.5 rounded-full bg-teal-400 ring-4 ring-teal-400/20" />
                  </div>
                  <div className="flex-1 flex items-center gap-3">
                    <div className="h-px flex-1 bg-teal-500/30" />
                    <span className="text-xs font-semibold text-teal-400 uppercase tracking-wider whitespace-nowrap">Today — {formatDate(today)}</span>
                    <div className="h-px flex-1 bg-teal-500/30" />
                  </div>
                </div>
              );

              return (
                <div className="relative">
                  <div className="absolute left-[7px] top-8 bottom-8 w-0.5 bg-gray-700" />

                  <div className="space-y-0">
                    {!todayOnMilestone && todayAfterIndex === -1 && <TodayMarker />}

                    {milestones.map((milestone, index) => {
                      const days = daysFromNow(milestone.date);
                      const isPast = days < 0;
                      const isToday = days === 0;
                      const isUrgent = days > 0 && days <= 7;
                      const Icon = milestone.icon;

                      let gapDays: number | null = null;
                      if (index < milestones.length - 1) {
                        const nextDate = milestones[index + 1].date;
                        const thisDate = milestone.date;
                        gapDays = Math.round((nextDate.getTime() - thisDate.getTime()) / (1000 * 60 * 60 * 24));
                      }

                      const showTodayAfter = !todayOnMilestone && todayAfterIndex === index && index < milestones.length - 1;

                      return (
                        <div key={milestone.label}>
                          <div className="relative flex items-start gap-4 py-4">
                            {/* Icon dot */}
                            <div className={`relative z-10 w-8 h-8 rounded-full bg-gradient-to-br ${milestone.color} flex items-center justify-center shadow-lg flex-shrink-0`}>
                              <Icon className="w-4 h-4 text-white" />
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-3 flex-wrap">
                                <h3 className={`font-semibold ${milestone.labelColor}`}>{milestone.label}</h3>
                                {isToday && (
                                  <span className="px-2 py-0.5 bg-teal-900/40 text-teal-400 text-xs rounded-full font-medium">Today</span>
                                )}
                                {isPast && !isToday && (
                                  <span className="px-2 py-0.5 bg-red-900/40 text-red-400 text-xs rounded-full font-medium">{Math.abs(days)} days ago</span>
                                )}
                                {isUrgent && (
                                  <span className="px-2 py-0.5 bg-orange-900/40 text-orange-400 text-xs rounded-full font-medium">{days} days away</span>
                                )}
                                {!isPast && !isToday && !isUrgent && (
                                  <span className="px-2 py-0.5 bg-gray-800 text-gray-400 text-xs rounded-full font-medium">{days} days away</span>
                                )}
                              </div>
                              <p className={`font-medium mt-0.5 ${milestone.dateColor}`}>{formatDate(milestone.date)}</p>
                              <p className="text-gray-500 text-sm mt-0.5">{milestone.description}</p>
                            </div>
                          </div>

                          {/* Gap indicator */}
                          {gapDays !== null && (
                            <div className="relative flex items-center gap-4 py-1 ml-[12px]">
                              <div className="w-4 flex justify-center flex-shrink-0" />
                              <div className="relative z-10 px-2 py-0.5 bg-gray-900 border border-gray-700 rounded-full">
                                <span className="text-[11px] text-gray-400 font-medium whitespace-nowrap">{formatGap(gapDays)}</span>
                              </div>
                            </div>
                          )}

                          {showTodayAfter && <TodayMarker />}
                        </div>
                      );
                    })}

                    {!todayOnMilestone && todayAfterIndex === milestones.length - 1 && <TodayMarker />}
                  </div>
                </div>
              );
            })()}

            {/* Calendar View */}
            {view === 'calendar' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {getCalendarDays(milestones).map(({ year, month }) => (
                  <CalendarMonth
                    key={`${year}-${month}`}
                    year={year}
                    month={month}
                    milestones={milestones}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
