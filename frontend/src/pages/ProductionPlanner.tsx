import { useState } from 'react';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/Button';
import { CalendarDays, ArrowLeft, Copy, Check, List, Calendar } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Milestone {
  label: string;
  date: Date;
  description: string;
  color: string;
  dotColor: string;
  labelColor: string;
  dateColor: string;
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

function calculateMilestones(inHandsDate: Date, shipDirect: boolean): Milestone[] {
  // Work backwards from in-hands date:
  // Product leaves factory: 7 days (ship direct) or 14 days (standard) before in-hands
  const exitFactoryDays = shipDirect ? -7 : -14;
  const exitFactory = addDays(inHandsDate, exitFactoryDays);
  // Samples due 35 days before exit factory
  const samplesDue = addDays(exitFactory, -35);
  // Production files locked 2.5 weeks (18 days) before samples
  const productionFilesLocked = addDays(samplesDue, -18);
  // Artwork locked 1 week (7 days) before production files
  const artworkLocked = addDays(productionFilesLocked, -7);

  return [
    {
      label: 'Artwork Locked',
      date: artworkLocked,
      description: 'All artwork and design files finalized and approved by customer',
      color: 'from-blue-500 to-cyan-500',
      dotColor: 'bg-blue-500',
      labelColor: 'text-blue-300',
      dateColor: 'text-blue-400',
    },
    {
      label: 'Production Files Submitted',
      date: productionFilesLocked,
      description: 'Final production-ready files (DST, vectors) submitted to factory',
      color: 'from-purple-500 to-indigo-500',
      dotColor: 'bg-purple-500',
      labelColor: 'text-purple-300',
      dateColor: 'text-purple-400',
    },
    {
      label: 'Sample Expected',
      date: samplesDue,
      description: 'Pre-production sample received for approval',
      color: 'from-amber-500 to-orange-500',
      dotColor: 'bg-amber-500',
      labelColor: 'text-amber-300',
      dateColor: 'text-amber-400',
    },
    {
      label: 'Exit Factory',
      date: exitFactory,
      description: shipDirect ? 'Finished product ships direct to customer from factory' : 'Finished product ships from factory',
      color: 'from-emerald-500 to-green-500',
      dotColor: 'bg-emerald-500',
      labelColor: 'text-emerald-300',
      dateColor: 'text-emerald-400',
    },
    {
      label: 'In-Hands Date',
      date: inHandsDate,
      description: 'Product delivered to customer',
      color: 'from-rose-500 to-pink-500',
      dotColor: 'bg-rose-500',
      labelColor: 'text-rose-300',
      dateColor: 'text-rose-400',
    },
  ];
}

// --- Calendar View ---

function getCalendarDays(milestones: Milestone[]): { year: number; month: number }[] {
  // Get all months that need to be shown (from first milestone to last)
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
  'bg-rose-500': 'ring-rose-500 bg-rose-500/20 text-rose-300',
};

function CalendarMonth({ year, month, milestones }: { year: number; month: number; milestones: Milestone[] }) {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startDow = firstDay.getDay(); // 0=Sun
  const daysInMonth = lastDay.getDate();
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const monthName = firstDay.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  // Build milestone lookup by day
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
      {/* Labels for this month's milestones */}
      {Object.keys(milestoneDays).length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-800 space-y-2">
          {Object.entries(milestoneDays).map(([day, m]) => {
            const ringStyle = MILESTONE_RING_COLORS[m.dotColor] || '';
            return (
              <div key={day} className="flex items-center gap-2.5 text-xs">
                <div className={`w-6 h-6 rounded-full ring-2 ${ringStyle} flex items-center justify-center text-[10px] font-bold flex-shrink-0`}>
                  {Number(day)}
                </div>
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
  const [shipDirect, setShipDirect] = useState(false);
  const [milestones, setMilestones] = useState<Milestone[] | null>(null);
  const [copied, setCopied] = useState(false);
  const [view, setView] = useState<'timeline' | 'calendar'>('timeline');

  const handleCalculate = () => {
    if (!inHandsDate) return;
    const date = new Date(inHandsDate + 'T00:00:00');
    setMilestones(calculateMilestones(date, shipDirect));
  };

  const handleCopyTimeline = () => {
    if (!milestones) return;
    const text = milestones
      .map((m) => `${m.label}: ${formatDate(m.date)}`)
      .join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleCalculate();
  };

  // Recalculate when ship direct changes (if date is set)
  const handleShipDirectChange = (checked: boolean) => {
    setShipDirect(checked);
    if (inHandsDate) {
      const date = new Date(inHandsDate + 'T00:00:00');
      setMilestones(calculateMilestones(date, checked));
    }
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
          <label className="block text-sm font-medium text-gray-300 mb-2">
            In-Hands Date (when the customer needs the product)
          </label>
          <div className="flex gap-3 mb-4">
            <input
              type="date"
              value={inHandsDate}
              onChange={(e) => setInHandsDate(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none"
            />
            <Button onClick={handleCalculate} disabled={!inHandsDate}>
              <CalendarDays className="w-4 h-4 mr-2" />
              Calculate
            </Button>
          </div>
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
              <span className="text-xs text-gray-500 ml-2">(Factory ships directly to customer — 7 days transit instead of 14)</span>
            </div>
          </label>
        </div>

        {/* Results */}
        {milestones && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-100">Production Timeline</h2>
              <div className="flex items-center gap-2">
                {/* View toggle */}
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
                <Button variant="outline" size="sm" onClick={handleCopyTimeline}>
                  {copied ? (
                    <>
                      <Check className="w-4 h-4 mr-2" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 mr-2" />
                      Copy
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* Timeline (List) View */}
            {view === 'timeline' && (() => {
              const today = new Date();
              today.setHours(0, 0, 0, 0);

              // Figure out where "today" falls relative to milestones
              // -1 = before all milestones, 0..n-1 = after milestone[i], n-1 = after last
              let todayAfterIndex = -1;
              for (let i = 0; i < milestones.length; i++) {
                const mDate = new Date(milestones[i].date);
                mDate.setHours(0, 0, 0, 0);
                if (today.getTime() >= mDate.getTime()) {
                  todayAfterIndex = i;
                }
              }
              // Check if today falls exactly on a milestone
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
                  {/* Vertical line */}
                  <div className="absolute left-[7px] top-8 bottom-8 w-0.5 bg-gray-700" />

                  <div className="space-y-0">
                    {/* Today marker before all milestones */}
                    {!todayOnMilestone && todayAfterIndex === -1 && <TodayMarker />}

                    {milestones.map((milestone, index) => {
                      const days = daysFromNow(milestone.date);
                      const isPast = days < 0;
                      const isToday = days === 0;
                      const isUrgent = days > 0 && days <= 7;

                      // Calculate gap to next milestone
                      let gapDays: number | null = null;
                      if (index < milestones.length - 1) {
                        const nextDate = milestones[index + 1].date;
                        const thisDate = milestone.date;
                        gapDays = Math.round((nextDate.getTime() - thisDate.getTime()) / (1000 * 60 * 60 * 24));
                      }

                      // Should we show "today" marker after this milestone's gap?
                      const showTodayAfter = !todayOnMilestone && todayAfterIndex === index && index < milestones.length - 1;

                      return (
                        <div key={milestone.label}>
                          <div className="relative flex items-start gap-4 py-4">
                            {/* Color dot */}
                            <div className={`relative z-10 w-4 h-4 mt-1 rounded-full bg-gradient-to-br ${milestone.color} shadow-lg flex-shrink-0 ring-4 ring-gray-900`} />

                            {/* Content — color-coded */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-3 flex-wrap">
                                <h3 className={`font-semibold ${milestone.labelColor}`}>{milestone.label}</h3>
                                {isToday && (
                                  <span className="px-2 py-0.5 bg-teal-900/40 text-teal-400 text-xs rounded-full font-medium">
                                    Today
                                  </span>
                                )}
                                {isPast && !isToday && (
                                  <span className="px-2 py-0.5 bg-red-900/40 text-red-400 text-xs rounded-full font-medium">
                                    {Math.abs(days)} days ago
                                  </span>
                                )}
                                {isUrgent && (
                                  <span className="px-2 py-0.5 bg-orange-900/40 text-orange-400 text-xs rounded-full font-medium">
                                    {days} days away
                                  </span>
                                )}
                                {!isPast && !isToday && !isUrgent && (
                                  <span className="px-2 py-0.5 bg-gray-800 text-gray-400 text-xs rounded-full font-medium">
                                    {days} days away
                                  </span>
                                )}
                              </div>
                              <p className={`font-medium mt-0.5 ${milestone.dateColor}`}>{formatDate(milestone.date)}</p>
                              <p className="text-gray-500 text-sm mt-0.5">{milestone.description}</p>
                            </div>
                          </div>

                          {/* Gap indicator between milestones */}
                          {gapDays !== null && (
                            <div className="relative flex items-center gap-4 py-1 ml-[5px]">
                              <div className="w-4 flex justify-center flex-shrink-0" />
                              <div className="relative z-10 px-2 py-0.5 bg-gray-900 border border-gray-700 rounded-full">
                                <span className="text-[11px] text-gray-400 font-medium whitespace-nowrap">{formatGap(gapDays)}</span>
                              </div>
                            </div>
                          )}

                          {/* Today marker between milestones */}
                          {showTodayAfter && <TodayMarker />}
                        </div>
                      );
                    })}

                    {/* Today marker after all milestones */}
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

            {/* Summary card */}
            <div className="card mt-6 bg-gray-900/50 border border-gray-800">
              <h3 className="text-sm font-medium text-gray-400 mb-3">Timeline Summary</h3>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Total lead time</p>
                  <p className="text-white font-semibold">
                    {Math.abs(daysFromNow(milestones[0].date) - daysFromNow(milestones[milestones.length - 1].date))} days
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">Days until in-hands</p>
                  <p className="text-white font-semibold">{daysFromNow(milestones[milestones.length - 1].date)} days</p>
                </div>
                <div>
                  <p className="text-gray-500">Shipping</p>
                  <p className="text-white font-semibold">{shipDirect ? 'Direct (7 days)' : 'Standard (14 days)'}</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
