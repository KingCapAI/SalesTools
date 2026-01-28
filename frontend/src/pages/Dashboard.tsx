import { Header } from '../components/layout/Header';
import { AppCard } from '../components/layout/AppCard';
import { useAuth } from '../context/AuthContext';
import { Palette, Calculator, Megaphone, FileText, Layers } from 'lucide-react';

const apps = [
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
  {
    id: 'quote-estimator',
    title: 'Quote Estimator',
    description: 'Calculate pricing and generate quotes for custom orders based on quantity, materials, and decoration methods.',
    icon: Calculator,
    to: '/quote-estimator',
  },
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
    title: 'Policies and Processes',
    description: 'Reference company policies, procedures, and best practices for sales operations.',
    icon: FileText,
    to: '/policies',
    comingSoon: true,
  },
];

export function Dashboard() {
  const { user } = useAuth();
  const allowedApps = user?.team?.allowed_apps || apps.map((a) => a.id);

  return (
    <div className="min-h-screen bg-black">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-100">
            Welcome back, {user?.name?.split(' ')[0]}!
          </h1>
          <p className="text-gray-400 mt-1">Select an application to get started</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {apps.map((app) => {
            const isAllowed = allowedApps.includes(app.id);
            const isDisabled = app.comingSoon || !isAllowed;

            return (
              <AppCard
                key={app.id}
                title={app.title}
                description={app.description}
                icon={app.icon}
                to={app.to}
                disabled={isDisabled}
                comingSoon={app.comingSoon}
              />
            );
          })}
        </div>
      </main>
    </div>
  );
}
