import { Link } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import { Card } from '../ui/Card';

interface AppCardProps {
  title: string;
  description: string;
  icon: LucideIcon;
  to: string;
  disabled?: boolean;
  comingSoon?: boolean;
}

export function AppCard({ title, description, icon: Icon, to, disabled, comingSoon }: AppCardProps) {
  const content = (
    <Card
      variant={disabled ? 'default' : 'hover'}
      className={`p-6 h-full ${disabled ? 'opacity-60' : ''}`}
    >
      <div className="flex flex-col h-full">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${
          disabled ? 'bg-gray-800' : 'bg-primary-900/50'
        }`}>
          <Icon className={`w-6 h-6 ${disabled ? 'text-gray-500' : 'text-primary-400'}`} />
        </div>
        <h3 className="text-lg font-semibold text-gray-100 mb-2">{title}</h3>
        <p className="text-sm text-gray-400 flex-grow">{description}</p>
        {comingSoon && (
          <span className="inline-block mt-4 px-3 py-1 bg-gray-800 text-gray-400 text-xs font-medium rounded-full w-fit">
            Coming Soon
          </span>
        )}
      </div>
    </Card>
  );

  if (disabled) {
    return <div className="cursor-not-allowed">{content}</div>;
  }

  return <Link to={to}>{content}</Link>;
}
