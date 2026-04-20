import { useState } from 'react';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/Button';
import { CalendarDays, ArrowLeft, Copy, Check } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Milestone {
  label: string;
  date: Date;
  description: string;
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

function calculateMilestones(inHandsDate: Date): Milestone[] {
  // Work backwards from in-hands date:
  // Product leaves factory 2 weeks (14 days) before in-hands
  const exitFactory = addDays(inHandsDate, -14);
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
    },
    {
      label: 'Production Files Submitted',
      date: productionFilesLocked,
      description: 'Final production-ready files (DST, vectors) submitted to factory',
      color: 'from-purple-500 to-indigo-500',
    },
    {
      label: 'Sample Expected',
      date: samplesDue,
      description: 'Pre-production sample received for approval',
      color: 'from-amber-500 to-orange-500',
    },
    {
      label: 'Exit Factory',
      date: exitFactory,
      description: 'Finished product ships from factory',
      color: 'from-emerald-500 to-green-500',
    },
    {
      label: 'In-Hands Date',
      date: inHandsDate,
      description: 'Product delivered to customer',
      color: 'from-rose-500 to-pink-500',
    },
  ];
}

export function TimelineCalculator() {
  const [inHandsDate, setInHandsDate] = useState('');
  const [milestones, setMilestones] = useState<Milestone[] | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCalculate = () => {
    if (!inHandsDate) return;
    const date = new Date(inHandsDate + 'T00:00:00');
    setMilestones(calculateMilestones(date));
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

  return (
    <div className="min-h-screen bg-black">
      <Header />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
              <h1 className="text-2xl font-bold text-gray-100">Timeline Calculator</h1>
              <p className="text-gray-400 text-sm">Calculate production milestones from an in-hands date</p>
            </div>
          </div>
        </div>

        {/* Input */}
        <div className="card mb-8">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            In-Hands Date (when the customer needs the product)
          </label>
          <div className="flex gap-3">
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
        </div>

        {/* Results */}
        {milestones && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-100">Production Timeline</h2>
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

            {/* Timeline */}
            <div className="relative">
              {/* Vertical line */}
              <div className="absolute left-6 top-8 bottom-8 w-0.5 bg-gray-700" />

              <div className="space-y-0">
                {milestones.map((milestone, index) => {
                  const days = daysFromNow(milestone.date);
                  const isPast = days < 0;
                  const isToday = days === 0;
                  const isUrgent = days > 0 && days <= 7;

                  return (
                    <div key={milestone.label} className="relative flex items-start gap-4 py-4">
                      {/* Dot */}
                      <div className={`relative z-10 w-12 h-12 rounded-full bg-gradient-to-br ${milestone.color} flex items-center justify-center shadow-lg flex-shrink-0`}>
                        <span className="text-white font-bold text-sm">{index + 1}</span>
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 flex-wrap">
                          <h3 className="text-white font-semibold">{milestone.label}</h3>
                          {isPast && (
                            <span className="px-2 py-0.5 bg-red-900/40 text-red-400 text-xs rounded-full font-medium">
                              {Math.abs(days)} days ago
                            </span>
                          )}
                          {isToday && (
                            <span className="px-2 py-0.5 bg-yellow-900/40 text-yellow-400 text-xs rounded-full font-medium">
                              Today
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
                        <p className="text-teal-400 font-medium mt-0.5">{formatDate(milestone.date)}</p>
                        <p className="text-gray-500 text-sm mt-0.5">{milestone.description}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Summary card */}
            <div className="card mt-6 bg-gray-900/50 border border-gray-800">
              <h3 className="text-sm font-medium text-gray-400 mb-3">Timeline Summary</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
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
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
