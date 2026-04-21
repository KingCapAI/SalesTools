import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

interface Tab {
  id: string;
  label: string;
  icon: LucideIcon;
  badge?: boolean;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  children: ReactNode;
}

export function Tabs({ tabs, activeTab, onTabChange, children }: TabsProps) {
  return (
    <div>
      {/* Tab list */}
      <div className="flex justify-center overflow-x-auto border-b border-gray-700 scrollbar-hide">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium whitespace-nowrap border-b-2 transition-colors flex-shrink-0 ${
                isActive
                  ? 'border-teal-500 text-teal-400'
                  : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600'
              }`}
            >
              <span className="relative">
                <Icon className="w-3.5 h-3.5" />
                {tab.badge && (
                  <span className="absolute -top-1 -right-1 w-2 h-2 bg-teal-400 rounded-full" />
                )}
              </span>
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Panel */}
      <div className="p-4">
        {children}
      </div>
    </div>
  );
}
