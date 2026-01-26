import { Header } from '../components/layout/Header';
import { Construction } from 'lucide-react';

export function MarketingTools() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-16">
          <Construction className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Marketing Tools</h1>
          <p className="text-gray-600">This feature is coming soon!</p>
        </div>
      </main>
    </div>
  );
}
