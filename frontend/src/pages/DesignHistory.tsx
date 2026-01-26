import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/Button';
import { DesignHistoryTable } from '../components/design-generator/DesignHistoryTable';
import { useDesigns, useDeleteDesign } from '../hooks/useDesigns';
import { useCustomers } from '../hooks/useCustomers';
import { ArrowLeft, Plus, Filter } from 'lucide-react';

export function DesignHistory() {
  const [customerId, setCustomerId] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  const { data: designs = [], isLoading, refetch } = useDesigns({
    customer_name: customerId || undefined,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  });

  const { data: customers = [] } = useCustomers();
  const deleteDesign = useDeleteDesign();

  const handleDelete = async (id: string) => {
    try {
      await deleteDesign.mutateAsync(id);
      refetch();
    } catch (error) {
      console.error('Failed to delete design:', error);
    }
  };

  const clearFilters = () => {
    setCustomerId('');
    setStartDate('');
    setEndDate('');
  };

  const hasFilters = customerId || startDate || endDate;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/ai-design-generator">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Design History</h1>
              <p className="text-gray-600">View and manage all generated designs</p>
            </div>
          </div>
          <Link to="/ai-design-generator">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              New Design
            </Button>
          </Link>
        </div>

        {/* Filters */}
        <div className="card mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="w-4 h-4 text-gray-500" />
            <h2 className="font-medium text-gray-900">Filters</h2>
            {hasFilters && (
              <button
                onClick={clearFilters}
                className="text-sm text-primary-600 hover:underline ml-auto"
              >
                Clear all
              </button>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label">Customer</label>
              <select
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                className="select"
              >
                <option value="">All Customers</option>
                {customers.map((customer) => (
                  <option key={customer.id} value={customer.id}>
                    {customer.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="input"
              />
            </div>
            <div>
              <label className="label">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="input"
              />
            </div>
          </div>
        </div>

        {/* Results */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-medium text-gray-900">
              {designs.length} {designs.length === 1 ? 'Design' : 'Designs'}
            </h2>
          </div>
          <DesignHistoryTable
            designs={designs}
            onDelete={handleDelete}
            isLoading={isLoading}
          />
        </div>
      </main>
    </div>
  );
}
