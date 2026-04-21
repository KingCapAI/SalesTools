import { useState, useEffect } from 'react';
import {
  CalendarDays, ChevronDown, ChevronUp, Zap, Info, List, Calendar,
  Palette, FileText, Camera, PlaneTakeoff, Warehouse, Package,
  Globe, Home, Truck, Link2,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { DesignQuote } from '../../api/designQuotes';

type ProductionType = 'overseas' | 'domestic';

const DOMESTIC_PRODUCTION_SPEEDS: { label: string; days: number; fee: string }[] = [
  { label: 'Standard (5-7 days)', days: 7, fee: 'No charge' },
  { label: 'Rush (4 days)', days: 4, fee: '+$2.00/pc' },
  { label: 'Rush (3 days)', days: 3, fee: '+$2.50/pc' },
  { label: 'Rush (2 days)', days: 2, fee: '+$3.00/pc' },
];

const DOMESTIC_SHIPPING_METHODS: { label: string; days: number }[] = [
  { label: 'Ground (5d)', days: 5 },
  { label: 'Express (3d)', days: 3 },
  { label: 'Priority (2d)', days: 2 },
  { label: 'Overnight (1d)', days: 1 },
];

interface Milestone {
  label: string;
  date: Date;
  color: string;
  icon: LucideIcon;
  labelColor: string;
  dateColor: string;
  dotColor: string;
}

const QUICK_TURN_METHODS = [
  'Flat Embroidery',
  '3D Embroidery',
  'Sublimated Patch',
  'Sublimated Label',
];

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
  if (dow === 0) result.setDate(result.getDate() + 1);
  if (dow === 6) result.setDate(result.getDate() + 2);
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
  const exitFactory = toWeekday(addDays(inHandsDate, shipDirect ? -7 : -14));
  const productionDays = quickTurn ? 21 : 35;
  const samplesDue = toWeekday(addDays(exitFactory, -productionDays));
  const productionFiles = toWeekday(addDays(samplesDue, -18));
  const artworkLocked = toWeekday(addDays(productionFiles, -7));

  const milestones: Milestone[] = [
    { label: 'Artwork Due', date: artworkLocked, color: 'bg-blue-500', icon: Palette, labelColor: 'text-blue-300', dateColor: 'text-blue-400', dotColor: 'bg-blue-500' },
    { label: 'Production Files Due', date: productionFiles, color: 'bg-purple-500', icon: FileText, labelColor: 'text-purple-300', dateColor: 'text-purple-400', dotColor: 'bg-purple-500' },
    { label: 'Sample Picture Expected', date: samplesDue, color: 'bg-amber-500', icon: Camera, labelColor: 'text-amber-300', dateColor: 'text-amber-400', dotColor: 'bg-amber-500' },
    { label: 'Order Shipped', date: exitFactory, color: 'bg-emerald-500', icon: PlaneTakeoff, labelColor: 'text-emerald-300', dateColor: 'text-emerald-400', dotColor: 'bg-emerald-500' },
  ];

  if (!shipDirect) {
    milestones.push({ label: 'Delivered to King Cap', date: toWeekday(addDays(exitFactory, 7)), color: 'bg-sky-500', icon: Warehouse, labelColor: 'text-sky-300', dateColor: 'text-sky-400', dotColor: 'bg-sky-500' });
  }

  milestones.push({ label: 'Order Delivered', date: inHandsDate, color: 'bg-rose-500', icon: Package, labelColor: 'text-rose-300', dateColor: 'text-rose-400', dotColor: 'bg-rose-500' });

  return milestones;
}

function addBusinessDays(date: Date, days: number): Date {
  const result = new Date(date);
  let remaining = days;
  while (remaining > 0) {
    result.setDate(result.getDate() + 1);
    if (result.getDay() !== 0 && result.getDay() !== 6) remaining--;
  }
  return result;
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
  // Work backwards: delivery → production complete → sample picture → artwork
  const productionComplete = subtractBusinessDays(inHandsDate, shippingDays);
  const samplePicture = subtractBusinessDays(productionComplete, productionDays);
  const artworkSubmitted = subtractBusinessDays(samplePicture, 3);

  return [
    { label: 'Artwork Submitted', date: artworkSubmitted, color: 'bg-blue-500', icon: Palette, labelColor: 'text-blue-300', dateColor: 'text-blue-400', dotColor: 'bg-blue-500' },
    { label: 'Sample Picture', date: samplePicture, color: 'bg-amber-500', icon: Camera, labelColor: 'text-amber-300', dateColor: 'text-amber-400', dotColor: 'bg-amber-500' },
    { label: 'Production Complete', date: productionComplete, color: 'bg-emerald-500', icon: Package, labelColor: 'text-emerald-300', dateColor: 'text-emerald-400', dotColor: 'bg-emerald-500' },
    { label: 'Order Delivered', date: inHandsDate, color: 'bg-rose-500', icon: Truck, labelColor: 'text-rose-300', dateColor: 'text-rose-400', dotColor: 'bg-rose-500' },
  ];
}

// --- Mini Calendar for sidebar ---

const RING_COLORS: Record<string, string> = {
  'bg-blue-500': 'ring-blue-500 bg-blue-500/20 text-blue-300',
  'bg-purple-500': 'ring-purple-500 bg-purple-500/20 text-purple-300',
  'bg-amber-500': 'ring-amber-500 bg-amber-500/20 text-amber-300',
  'bg-emerald-500': 'ring-emerald-500 bg-emerald-500/20 text-emerald-300',
  'bg-sky-500': 'ring-sky-500 bg-sky-500/20 text-sky-300',
  'bg-rose-500': 'ring-rose-500 bg-rose-500/20 text-rose-300',
};

function MiniCalendarMonth({ year, month, milestones }: { year: number; month: number; milestones: Milestone[] }) {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startDow = firstDay.getDay();
  const daysInMonth = lastDay.getDate();
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const monthName = firstDay.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });

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
    <div>
      <h4 className="text-xs text-gray-400 font-semibold mb-1.5 text-center">{monthName}</h4>
      <div className="grid grid-cols-7 gap-0.5 text-center" style={{ fontSize: '10px' }}>
        {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((d, i) => (
          <div key={`${d}-${i}`} className="text-gray-600 font-medium py-0.5">{d}</div>
        ))}
        {cells.map((day, i) => {
          if (day === null) return <div key={`e-${i}`} />;
          const milestone = milestoneDays[day];
          const cellDate = new Date(year, month, day);
          cellDate.setHours(0, 0, 0, 0);
          const isToday = cellDate.getTime() === today.getTime();
          const ringStyle = milestone ? RING_COLORS[milestone.dotColor] || '' : '';

          return (
            <div
              key={day}
              className={`flex items-center justify-center w-5 h-5 mx-auto rounded-full ${
                milestone
                  ? `ring-1.5 ${ringStyle} font-bold`
                  : isToday
                  ? 'text-teal-400 font-medium ring-1 ring-teal-500/50'
                  : 'text-gray-500'
              }`}
              title={milestone ? `${milestone.label}: ${formatDate(milestone.date)}` : undefined}
            >
              {day}
            </div>
          );
        })}
      </div>
      {Object.keys(milestoneDays).length > 0 && (
        <div className="mt-2 pt-1.5 border-t border-gray-800 space-y-1">
          {Object.entries(milestoneDays).map(([day, m]) => {
            const Icon = m.icon;
            return (
              <div key={day} className="flex items-center gap-1.5" style={{ fontSize: '10px' }}>
                <div className={`w-2 h-2 rounded-full ${m.dotColor} flex-shrink-0`} />
                <Icon className={`w-2.5 h-2.5 ${m.labelColor} flex-shrink-0`} />
                <span className="text-gray-300">{m.label}</span>
                <span className="text-gray-500 ml-auto">{Number(day)}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function getCalendarMonths(milestones: Milestone[]): { year: number; month: number }[] {
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

// --- Main Component ---

interface ProductionTimelineProps {
  initialDate?: string;
  quoteData?: DesignQuote | null;
  alwaysExpanded?: boolean;
}

export function ProductionTimeline({ initialDate, quoteData, alwaysExpanded }: ProductionTimelineProps) {
  const [inHandsDate, setInHandsDate] = useState(initialDate || '');
  const [productionType, setProductionType] = useState<ProductionType>('overseas');
  const [shipDirect, setShipDirect] = useState(false);
  const [quickTurn, setQuickTurn] = useState(false);
  const [domesticProductionDays, setDomesticProductionDays] = useState(7);
  const [domesticShippingDays, setDomesticShippingDays] = useState(5);
  const [expanded, setExpanded] = useState(!!initialDate);
  const [view, setView] = useState<'list' | 'calendar'>('list');
  const [syncedFromQuote, setSyncedFromQuote] = useState(false);
  const [milestones, setMilestones] = useState<Milestone[] | null>(() => {
    if (initialDate) {
      return calculateMilestones(new Date(initialDate + 'T00:00:00'), false, false);
    }
    return null;
  });

  // Auto-sync settings from quote data
  useEffect(() => {
    if (!quoteData) {
      setSyncedFromQuote(false);
      return;
    }

    // Set production type
    const pt: ProductionType = quoteData.quote_type === 'domestic' ? 'domestic' : 'overseas';
    setProductionType(pt);

    if (pt === 'overseas') {
      // Ship direct detection
      const sd = quoteData.shipping_method === 'Direct to Customer';
      setShipDirect(sd);

      // Quick turn eligibility: check if ALL decorations are in quick turn methods
      const decorations = [
        quoteData.front_decoration,
        quoteData.left_decoration,
        quoteData.right_decoration,
        quoteData.back_decoration,
        quoteData.visor_decoration,
      ].filter((d): d is string => !!d && d.trim().length > 0);

      const qt = decorations.length > 0 && decorations.every(
        (d) => QUICK_TURN_METHODS.some((m) => m.toLowerCase() === d.toLowerCase())
      );
      setQuickTurn(qt);
    } else {
      // Parse domestic production speed from shipping_speed field
      const speed = quoteData.shipping_speed || '';
      if (speed.includes('4 Production')) setDomesticProductionDays(4);
      else if (speed.includes('3 Production')) setDomesticProductionDays(3);
      else if (speed.includes('2 Production')) setDomesticProductionDays(2);
      else setDomesticProductionDays(7);
    }

    setSyncedFromQuote(true);
    setExpanded(true);

    // Recalculate if we have a date
    if (inHandsDate) {
      if (pt === 'domestic') {
        const speed = quoteData.shipping_speed || '';
        let dpd = 7;
        if (speed.includes('4 Production')) dpd = 4;
        else if (speed.includes('3 Production')) dpd = 3;
        else if (speed.includes('2 Production')) dpd = 2;
        setMilestones(calculateDomesticMilestones(new Date(inHandsDate + 'T00:00:00'), domesticShippingDays, dpd));
      } else {
        const sd = quoteData.shipping_method === 'Direct to Customer';
        const decorations = [
          quoteData.front_decoration, quoteData.left_decoration,
          quoteData.right_decoration, quoteData.back_decoration,
          quoteData.visor_decoration,
        ].filter((d): d is string => !!d && d.trim().length > 0);
        const qt = decorations.length > 0 && decorations.every(
          (d) => QUICK_TURN_METHODS.some((m) => m.toLowerCase() === d.toLowerCase())
        );
        setMilestones(calculateMilestones(new Date(inHandsDate + 'T00:00:00'), sd, qt));
      }
    }
  }, [quoteData]);

  const recalculate = (date?: string, pt?: ProductionType, sd?: boolean, qt?: boolean, dpd?: number, dsd?: number) => {
    const d = date ?? inHandsDate;
    if (!d) return;
    const type = pt ?? productionType;
    if (type === 'domestic') {
      setMilestones(calculateDomesticMilestones(new Date(d + 'T00:00:00'), dsd ?? domesticShippingDays, dpd ?? domesticProductionDays));
    } else {
      setMilestones(calculateMilestones(new Date(d + 'T00:00:00'), sd ?? shipDirect, qt ?? quickTurn));
    }
    setExpanded(true);
  };

  const handleCalculate = () => recalculate();

  const handleProductionTypeChange = (type: ProductionType) => {
    setProductionType(type);
    recalculate(undefined, type);
  };

  const handleShipDirectChange = (checked: boolean) => {
    setShipDirect(checked);
    recalculate(undefined, undefined, checked);
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

  const formatGap = (d: number) => {
    if (d % 7 === 0 && d >= 14) return `${d / 7}w`;
    if (d === 7) return '1w';
    return `${d}d`;
  };

  const isExpanded = alwaysExpanded || expanded;

  return (
    <div>
      {!alwaysExpanded && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center justify-between w-full text-left"
        >
          <h3 className="font-semibold text-white flex items-center gap-2">
            <CalendarDays className="w-4 h-4 text-teal-400" />
            Production Planner
          </h3>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </button>
      )}

      {isExpanded && (
        <div className="mt-4 space-y-3">
          {/* Synced from quote — show estimated delivery */}
          {syncedFromQuote && !inHandsDate && (
            <div className="p-2.5 bg-teal-900/20 border border-teal-800/30 rounded-lg">
              <div className="flex items-center gap-1.5 mb-2">
                <Link2 className="w-3 h-3 text-teal-400 flex-shrink-0" />
                <p className="text-[10px] text-teal-400 font-semibold uppercase tracking-wide">Estimated from quote</p>
              </div>
              {(() => {
                // Calculate "if we start today" timeline
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                let estimatedMilestones: Milestone[];
                if (productionType === 'domestic') {
                  // Forward: artwork today → sample 3 biz days → production → shipping
                  const sample = addBusinessDays(today, 3);
                  const prodComplete = addBusinessDays(sample, domesticProductionDays);
                  const delivery = addBusinessDays(prodComplete, domesticShippingDays);
                  estimatedMilestones = calculateDomesticMilestones(delivery, domesticShippingDays, domesticProductionDays);
                } else {
                  const prodDays = quickTurn ? 21 : 35;
                  // Forward: artwork today → +7 prod files → +18 sample → +prodDays exit → +shipping delivery
                  const artworkDate = today;
                  const prodFiles = toWeekday(addDays(artworkDate, 7));
                  const sampleDue = toWeekday(addDays(prodFiles, 18));
                  const exitFactory = toWeekday(addDays(sampleDue, prodDays));
                  const delivery = shipDirect ? toWeekday(addDays(exitFactory, 7)) : toWeekday(addDays(exitFactory, 14));
                  estimatedMilestones = calculateMilestones(delivery, shipDirect, quickTurn);
                }
                const deliveryDate = estimatedMilestones[estimatedMilestones.length - 1].date;
                const deliveryDays = daysFromNow(deliveryDate);
                return (
                  <div className="space-y-1.5">
                    <p className="text-xs text-white font-medium">
                      If artwork starts today → delivery by <span className="text-teal-300">{formatDate(deliveryDate)}</span>
                    </p>
                    <p className="text-[10px] text-gray-400">
                      {deliveryDays} days total • {productionType === 'overseas' ? (quickTurn ? 'Quick Turn 21d' : 'Standard 35d') : `${domesticProductionDays} biz days`} production • {productionType === 'overseas' ? (shipDirect ? 'Ship Direct' : 'Via King Cap') : `${domesticShippingDays}d shipping`}
                    </p>
                  </div>
                );
              })()}
            </div>
          )}

          {/* Target date section */}
          {syncedFromQuote && !inHandsDate && (
            <p className="text-[10px] text-gray-500 text-center">— or enter a target in-hands date below —</p>
          )}

          {/* Production Type Toggle */}
          <div className="flex items-center bg-gray-800 rounded-lg p-0.5">
            <button
              onClick={() => handleProductionTypeChange('overseas')}
              className={`flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-md text-xs transition-colors ${
                productionType === 'overseas' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-gray-300'
              }`}
            >
              <Globe className="w-3 h-3" />
              Overseas
            </button>
            <button
              onClick={() => handleProductionTypeChange('domestic')}
              className={`flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-md text-xs transition-colors ${
                productionType === 'domestic' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-gray-300'
              }`}
            >
              <Home className="w-3 h-3" />
              Domestic
            </button>
          </div>

          {/* Date input */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">In-Hands Date</label>
            <div className="flex gap-2">
              <input
                type="date"
                value={inHandsDate}
                min={new Date().toISOString().split('T')[0]}
                onChange={(e) => setInHandsDate(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCalculate()}
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none [color-scheme:dark]"
              />
              <button
                onClick={handleCalculate}
                disabled={!inHandsDate}
                className="px-3 py-2 bg-teal-600 hover:bg-teal-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm rounded-lg transition-colors"
              >
                Go
              </button>
            </div>
          </div>

          {/* Overseas Options */}
          {productionType === 'overseas' && (
            <div className="space-y-2">
              {/* Quick Turn */}
              <label className="flex items-center gap-2 cursor-pointer">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={quickTurn}
                    onChange={(e) => handleQuickTurnChange(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-8 h-4 bg-gray-700 rounded-full peer-checked:bg-amber-500 transition-colors" />
                  <div className="absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform peer-checked:translate-x-4" />
                </div>
                <span className="text-xs text-gray-300 flex items-center gap-1">
                  <Zap className="w-3 h-3 text-amber-400" />
                  Quick Turn (21 days)
                </span>
              </label>

              {/* Quick Turn info */}
              {quickTurn && (
                <div className="p-2 bg-amber-900/15 border border-amber-800/30 rounded-lg">
                  <div className="flex items-start gap-1.5">
                    <Info className="w-3 h-3 text-amber-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-[10px] text-amber-300 font-medium mb-1">Eligible methods:</p>
                      <div className="flex flex-wrap gap-1">
                        {QUICK_TURN_METHODS.map((m) => (
                          <span key={m} className="px-1.5 py-0.5 bg-amber-800/30 text-amber-300 rounded text-[10px]">{m}</span>
                        ))}
                      </div>
                      <p className="text-[10px] text-gray-500 mt-1.5">Standard (35-day) required for:</p>
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {STANDARD_ONLY_METHODS.slice(0, 6).map((m) => (
                          <span key={m} className="px-1.5 py-0.5 bg-gray-800 text-gray-400 rounded text-[10px]">{m}</span>
                        ))}
                        {STANDARD_ONLY_METHODS.length > 6 && (
                          <span className="px-1.5 py-0.5 bg-gray-800 text-gray-500 rounded text-[10px]">+{STANDARD_ONLY_METHODS.length - 6} more</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Ship Direct */}
              <label className="flex items-center gap-2 cursor-pointer">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={shipDirect}
                    onChange={(e) => handleShipDirectChange(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-8 h-4 bg-gray-700 rounded-full peer-checked:bg-teal-500 transition-colors" />
                  <div className="absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform peer-checked:translate-x-4" />
                </div>
                <span className="text-xs text-gray-400">Ship Direct (7 days)</span>
              </label>
            </div>
          )}

          {/* Domestic Options */}
          {productionType === 'domestic' && (
            <div className="space-y-2">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Production Speed</label>
                <select
                  value={domesticProductionDays}
                  onChange={(e) => handleDomesticProductionChange(Number(e.target.value))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none [color-scheme:dark]"
                >
                  {DOMESTIC_PRODUCTION_SPEEDS.map((s) => (
                    <option key={s.days} value={s.days}>{s.label} — {s.fee}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Shipping Method</label>
                <select
                  value={domesticShippingDays}
                  onChange={(e) => handleDomesticShippingChange(Number(e.target.value))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none [color-scheme:dark]"
                >
                  {DOMESTIC_SHIPPING_METHODS.map((m) => (
                    <option key={m.days} value={m.days}>{m.label}</option>
                  ))}
                </select>
              </div>
              {domesticProductionDays < 7 && (
                <p className="text-[10px] text-amber-300 flex items-center gap-1">
                  <Info className="w-3 h-3 flex-shrink-0" />
                  Rush: {DOMESTIC_PRODUCTION_SPEEDS.find((s) => s.days === domesticProductionDays)?.fee}/piece
                </p>
              )}
            </div>
          )}

          {/* Results */}
          {milestones && (
            <>
              {/* View toggle */}
              <div className="flex items-center bg-gray-800 rounded-lg p-0.5">
                <button
                  onClick={() => setView('list')}
                  className={`flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-md text-xs transition-colors ${
                    view === 'list' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-gray-300'
                  }`}
                >
                  <List className="w-3 h-3" />
                  List
                </button>
                <button
                  onClick={() => setView('calendar')}
                  className={`flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-md text-xs transition-colors ${
                    view === 'calendar' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-gray-300'
                  }`}
                >
                  <Calendar className="w-3 h-3" />
                  Calendar
                </button>
              </div>

              {/* List view */}
              {view === 'list' && (
                <div className="space-y-0 pt-1">
                  {milestones.map((m, index) => {
                    const days = daysFromNow(m.date);
                    const isPast = days < 0;
                    const isToday = days === 0;
                    const Icon = m.icon;

                    // Gap to next milestone
                    let gapDays: number | null = null;
                    if (index < milestones.length - 1) {
                      gapDays = Math.round((milestones[index + 1].date.getTime() - m.date.getTime()) / (1000 * 60 * 60 * 24));
                    }

                    return (
                      <div key={m.label}>
                        <div className="flex items-center gap-2 py-1.5">
                          <Icon className={`w-3.5 h-3.5 ${m.labelColor} flex-shrink-0`} />
                          <div className="flex-1 min-w-0">
                            <span className={`text-xs font-medium ${m.labelColor}`}>{m.label}</span>
                          </div>
                          <span className={`text-xs ${m.dateColor} flex-shrink-0`}>{formatDate(m.date)}</span>
                          <span className={`text-[10px] w-8 text-right flex-shrink-0 ${isPast ? 'text-red-400' : isToday ? 'text-teal-400' : days <= 7 ? 'text-orange-400' : 'text-gray-500'}`}>
                            {isPast ? `${Math.abs(days)}d ago` : isToday ? 'Today' : `${days}d`}
                          </span>
                        </div>
                        {gapDays !== null && (
                          <div className="flex justify-center py-0.5">
                            <span className="text-[10px] text-gray-600 px-1.5 py-0.5 bg-gray-800/50 rounded-full">{formatGap(gapDays)}</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Calendar view */}
              {view === 'calendar' && (
                <div className="space-y-4 pt-1">
                  {getCalendarMonths(milestones).map(({ year, month }) => (
                    <MiniCalendarMonth
                      key={`${year}-${month}`}
                      year={year}
                      month={month}
                      milestones={milestones}
                    />
                  ))}
                </div>
              )}

              {/* Warnings and suggestions */}
              {(() => {
                const pastDue = milestones.filter((m) => daysFromNow(m.date) < 0);
                if (pastDue.length === 0) return null;

                const suggestions: string[] = [];
                if (productionType === 'overseas') {
                  if (!shipDirect) suggestions.push('Switch to Ship Direct to save 7 days');
                  if (!quickTurn) {
                    // Check if quote decorations are QT eligible
                    const decorations = quoteData ? [
                      quoteData.front_decoration, quoteData.left_decoration,
                      quoteData.right_decoration, quoteData.back_decoration,
                      quoteData.visor_decoration,
                    ].filter((d): d is string => !!d && d.trim().length > 0) : [];
                    const qtEligible = decorations.length > 0 && decorations.every(
                      (d) => QUICK_TURN_METHODS.some((m) => m.toLowerCase() === d.toLowerCase())
                    );
                    if (qtEligible) suggestions.push('Eligible for Quick Turn — saves 14 days of production');
                  }
                } else {
                  if (domesticProductionDays > 2) suggestions.push('Consider Rush production to save time');
                  if (domesticShippingDays > 1) suggestions.push('Faster shipping available (Overnight)');
                }

                return (
                  <div className="p-2 bg-red-900/20 border border-red-800/30 rounded-lg">
                    <p className="text-[10px] text-red-300 font-medium mb-1">
                      {pastDue.length} milestone{pastDue.length > 1 ? 's' : ''} already past due
                    </p>
                    {suggestions.length > 0 && (
                      <div className="space-y-0.5 mt-1.5">
                        <p className="text-[10px] text-gray-400">Suggestions:</p>
                        {suggestions.map((s) => (
                          <p key={s} className="text-[10px] text-amber-300 flex items-center gap-1">
                            <Zap className="w-2.5 h-2.5 flex-shrink-0" />
                            {s}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Summary */}
              <div className="pt-2 border-t border-gray-800 grid grid-cols-2 gap-2 text-[10px]">
                <div>
                  <p className="text-gray-500">Lead time</p>
                  <p className="text-white font-medium">
                    {Math.abs(daysFromNow(milestones[0].date) - daysFromNow(milestones[milestones.length - 1].date))} days
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">Production</p>
                  <p className="text-white font-medium flex items-center gap-1">
                    {productionType === 'overseas' ? (
                      <>
                        {quickTurn && <Zap className="w-2.5 h-2.5 text-amber-400" />}
                        {quickTurn ? '21 days' : '35 days'}
                      </>
                    ) : (
                      <>{domesticProductionDays} biz days</>
                    )}
                  </p>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
