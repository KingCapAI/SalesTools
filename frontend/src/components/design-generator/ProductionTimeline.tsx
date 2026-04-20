import { useState } from 'react';
import { CalendarDays, ChevronDown, ChevronUp } from 'lucide-react';

interface Milestone {
  label: string;
  date: Date;
  color: string;
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

function calculateMilestones(inHandsDate: Date, shipDirect: boolean): Milestone[] {
  const exitFactory = addDays(inHandsDate, shipDirect ? -7 : -14);
  const samplesDue = addDays(exitFactory, -35);
  const productionFiles = addDays(samplesDue, -18);
  const artworkLocked = addDays(productionFiles, -7);

  const milestones: Milestone[] = [
    { label: 'Artwork Due', date: artworkLocked, color: 'bg-blue-500' },
    { label: 'Production Files Due', date: productionFiles, color: 'bg-purple-500' },
    { label: 'Sample Picture Expected', date: samplesDue, color: 'bg-amber-500' },
    { label: 'Order Shipped', date: exitFactory, color: 'bg-emerald-500' },
  ];

  if (!shipDirect) {
    milestones.push({ label: 'Delivered to King Cap', date: addDays(exitFactory, 7), color: 'bg-sky-500' });
  }

  milestones.push({ label: 'Order Delivered', date: inHandsDate, color: 'bg-rose-500' });

  return milestones;
}

interface ProductionTimelineProps {
  /** If provided, shows the timeline immediately */
  initialDate?: string;
}

export function ProductionTimeline({ initialDate }: ProductionTimelineProps) {
  const [inHandsDate, setInHandsDate] = useState(initialDate || '');
  const [shipDirect, setShipDirect] = useState(false);
  const [expanded, setExpanded] = useState(!!initialDate);
  const [milestones, setMilestones] = useState<Milestone[] | null>(() => {
    if (initialDate) {
      return calculateMilestones(new Date(initialDate + 'T00:00:00'), false);
    }
    return null;
  });

  const handleCalculate = () => {
    if (!inHandsDate) return;
    const date = new Date(inHandsDate + 'T00:00:00');
    setMilestones(calculateMilestones(date, shipDirect));
    setExpanded(true);
  };

  const handleShipDirectChange = (checked: boolean) => {
    setShipDirect(checked);
    if (inHandsDate) {
      setMilestones(calculateMilestones(new Date(inHandsDate + 'T00:00:00'), checked));
    }
  };

  return (
    <div>
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

      {expanded && (
        <div className="mt-4 space-y-3">
          {/* Date input */}
          <div className="flex gap-2">
            <input
              type="date"
              value={inHandsDate}
              onChange={(e) => setInHandsDate(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCalculate()}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none"
              placeholder="In-hands date"
            />
            <button
              onClick={handleCalculate}
              disabled={!inHandsDate}
              className="px-3 py-2 bg-teal-600 hover:bg-teal-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm rounded-lg transition-colors"
            >
              Go
            </button>
          </div>

          {/* Ship direct toggle */}
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
            <span className="text-xs text-gray-400">Ship Direct</span>
          </label>

          {/* Milestones */}
          {milestones && (
            <div className="space-y-2 pt-1">
              {milestones.map((m) => {
                const days = daysFromNow(m.date);
                const isPast = days < 0;

                return (
                  <div key={m.label} className="flex items-center gap-2.5">
                    <div className={`w-2 h-2 rounded-full ${m.color} flex-shrink-0`} />
                    <span className="text-xs text-gray-300 font-medium w-28 flex-shrink-0">{m.label}</span>
                    <span className={`text-xs ${isPast ? 'text-red-400' : 'text-gray-400'}`}>
                      {formatDate(m.date)}
                    </span>
                    <span className={`text-xs ml-auto ${isPast ? 'text-red-400' : days <= 7 ? 'text-orange-400' : 'text-gray-500'}`}>
                      {isPast ? `${Math.abs(days)}d ago` : days === 0 ? 'Today' : `${days}d`}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
