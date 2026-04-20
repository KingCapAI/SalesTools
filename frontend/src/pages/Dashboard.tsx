import { Link } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { useAuth } from '../context/AuthContext';
import { Palette, Calculator, Megaphone, FileText, Layers, CalendarDays } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Card } from '../components/ui/Card';

interface AppItem {
  id: string;
  title: string;
  description: string;
  icon: LucideIcon;
  to: string;
  comingSoon?: boolean;
}

interface AppGroup {
  label: string;
  color: string; // tailwind gradient for section accent
  iconBg: string;
  iconColor: string;
  apps: AppItem[];
}

const groups: AppGroup[] = [
  {
    label: 'Design',
    color: 'from-violet-500 to-purple-600',
    iconBg: 'bg-violet-900/40',
    iconColor: 'text-violet-400',
    apps: [
      {
        id: 'ai-design-generator',
        title: 'AI Design Conceptor',
        description: 'Create custom hat design concepts using AI. Upload logos, set brand guidelines, and generate professional product shots.',
        icon: Palette,
        to: '/ai-design-generator',
      },
      {
        id: 'custom-design-builder',
        title: 'Mockup Builder',
        description: 'Build hat mockups with specific logo placements. Upload logos for each location and recreate reference hats.',
        icon: Layers,
        to: '/custom-design-builder',
      },
    ],
  },
  {
    label: 'Planning',
    color: 'from-teal-500 to-emerald-600',
    iconBg: 'bg-teal-900/40',
    iconColor: 'text-teal-400',
    apps: [
      {
        id: 'quote-estimator',
        title: 'Quote Estimator',
        description: 'Calculate pricing and generate quotes for custom orders based on quantity, materials, and decoration methods.',
        icon: Calculator,
        to: '/quote-estimator',
      },
      {
        id: 'production-planner',
        title: 'Production Planner',
        description: 'Calculate production milestones and key dates based on a customer in-hands date.',
        icon: CalendarDays,
        to: '/production-planner',
      },
    ],
  },
  {
    label: 'Resources',
    color: 'from-amber-500 to-orange-600',
    iconBg: 'bg-amber-900/40',
    iconColor: 'text-amber-400',
    apps: [
      {
        id: 'marketing-tools',
        title: 'Marketing Tools',
        description: 'Access marketing materials, templates, and resources to support your sales efforts.',
        icon: Megaphone,
        to: '/marketing-tools',
        comingSoon: true,
      },
      {
        id: 'policies',
        title: 'Policies & Processes',
        description: 'Reference company policies, procedures, and best practices for sales operations.',
        icon: FileText,
        to: '/policies',
        comingSoon: true,
      },
    ],
  },
];

const alwaysAvailable = ['production-planner', 'quote-estimator'];

export function Dashboard() {
  const { user } = useAuth();
  const allowedApps = user?.team?.allowed_apps || groups.flatMap((g) => g.apps.map((a) => a.id));

  return (
    <div className="min-h-screen bg-black">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-10">
          <h1 className="text-2xl font-bold text-gray-100">
            Welcome back, {user?.name?.split(' ')[0]}!
          </h1>
          <p className="text-gray-400 mt-1">Select an application to get started</p>
        </div>

        <div className="space-y-10">
          {groups.map((group) => (
            <section key={group.label}>
              {/* Section header */}
              <div className="flex items-center gap-3 mb-4">
                <div className={`h-0.5 w-6 rounded-full bg-gradient-to-r ${group.color}`} />
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">{group.label}</h2>
              </div>

              {/* Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {group.apps.map((app) => {
                  const isAllowed = alwaysAvailable.includes(app.id) || allowedApps.includes(app.id);
                  const isDisabled = app.comingSoon || !isAllowed;

                  const card = (
                    <Card
                      key={app.id}
                      variant={isDisabled ? 'default' : 'hover'}
                      className={`p-6 h-full ${isDisabled ? 'opacity-60' : ''}`}
                    >
                      <div className="flex flex-col h-full">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${group.iconBg}`}>
                          <app.icon className={`w-6 h-6 ${group.iconColor}`} />
                        </div>
                        <h3 className="text-lg font-semibold text-gray-100 mb-2">{app.title}</h3>
                        <p className="text-sm text-gray-400 flex-grow">{app.description}</p>
                        {app.comingSoon && (
                          <span className="inline-block mt-4 px-3 py-1 bg-gray-800 text-gray-400 text-xs font-medium rounded-full w-fit">
                            Coming Soon
                          </span>
                        )}
                      </div>
                    </Card>
                  );

                  if (isDisabled) {
                    return <div key={app.id} className="cursor-not-allowed">{card}</div>;
                  }

                  return <Link key={app.id} to={app.to}>{card}</Link>;
                })}
              </div>
            </section>
          ))}
        </div>
      </main>
    </div>
  );
}
