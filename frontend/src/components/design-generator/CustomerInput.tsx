import { useState, useEffect } from 'react';
import { useCustomers, useCreateCustomer } from '../../hooks/useCustomers';
import { useBrands, useCreateBrand } from '../../hooks/useBrands';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { Plus, X } from 'lucide-react';
import type { CustomerList, BrandList } from '../../types/api';

interface CustomerInputProps {
  customerId: string;
  brandId: string;
  onCustomerChange: (customerId: string, customer?: CustomerList) => void;
  onBrandChange: (brandId: string, brand?: BrandList) => void;
}

export function CustomerInput({ customerId, brandId, onCustomerChange, onBrandChange }: CustomerInputProps) {
  const [customerSearch, setCustomerSearch] = useState('');
  const [brandSearch, setBrandSearch] = useState('');
  const [isCustomerOpen, setIsCustomerOpen] = useState(false);
  const [isBrandOpen, setIsBrandOpen] = useState(false);
  const [showCreateCustomer, setShowCreateCustomer] = useState(false);
  const [showCreateBrand, setShowCreateBrand] = useState(false);

  // New customer form
  const [newCustomerName, setNewCustomerName] = useState('');
  const [newCustomerEmail, setNewCustomerEmail] = useState('');
  const [newCustomerNotes, setNewCustomerNotes] = useState('');

  // New brand form
  const [newBrandName, setNewBrandName] = useState('');
  const [newBrandWebsite, setNewBrandWebsite] = useState('');

  const { data: customers = [], isLoading: customersLoading } = useCustomers(customerSearch);
  const { data: brands = [], isLoading: brandsLoading } = useBrands(customerId, brandSearch);
  const createCustomer = useCreateCustomer();
  const createBrand = useCreateBrand();

  const selectedCustomer = customers.find((c) => c.id === customerId);
  const selectedBrand = brands.find((b) => b.id === brandId);

  useEffect(() => {
    if (selectedCustomer) {
      setCustomerSearch(selectedCustomer.name);
    }
  }, [selectedCustomer]);

  useEffect(() => {
    if (selectedBrand) {
      setBrandSearch(selectedBrand.name);
    }
  }, [selectedBrand]);

  const handleSelectCustomer = (customer: CustomerList) => {
    onCustomerChange(customer.id, customer);
    onBrandChange(''); // Reset brand when customer changes
    setCustomerSearch(customer.name);
    setBrandSearch('');
    setIsCustomerOpen(false);
  };

  const handleSelectBrand = (brand: BrandList) => {
    onBrandChange(brand.id, brand);
    setBrandSearch(brand.name);
    setIsBrandOpen(false);
  };

  const handleCreateCustomer = async () => {
    if (!newCustomerName.trim()) return;

    try {
      const customer = await createCustomer.mutateAsync({
        name: newCustomerName,
        contact_email: newCustomerEmail || undefined,
        notes: newCustomerNotes || undefined,
      });
      onCustomerChange(customer.id, customer as CustomerList);
      onBrandChange('');
      setCustomerSearch(customer.name);
      setBrandSearch('');
      setShowCreateCustomer(false);
      setNewCustomerName('');
      setNewCustomerEmail('');
      setNewCustomerNotes('');
    } catch (error: any) {
      console.error('Failed to create customer:', error);
      alert(error.response?.data?.detail || 'Failed to create customer. Please try again.');
    }
  };

  const handleCreateBrand = async () => {
    if (!newBrandName.trim() || !customerId) return;

    try {
      const brand = await createBrand.mutateAsync({
        customer_id: customerId,
        name: newBrandName,
        website: newBrandWebsite || undefined,
      });
      onBrandChange(brand.id, brand as BrandList);
      setBrandSearch(brand.name);
      setShowCreateBrand(false);
      setNewBrandName('');
      setNewBrandWebsite('');
    } catch (error: any) {
      console.error('Failed to create brand:', error);
      alert(error.response?.data?.detail || 'Failed to create brand. Please try again.');
    }
  };

  return (
    <div className="space-y-4">
      {/* Customer Selection */}
      <div className="relative">
        <label className="label">Customer (Distributor)</label>
        <p className="text-sm text-gray-400 mb-2">
          The promotional distributor organizing this design
        </p>
        <input
          type="text"
          className="input"
          placeholder="Search or select a customer..."
          value={customerSearch}
          onChange={(e) => {
            setCustomerSearch(e.target.value);
            setIsCustomerOpen(true);
            if (!e.target.value) {
              onCustomerChange('');
              onBrandChange('');
            }
          }}
          onFocus={() => setIsCustomerOpen(true)}
        />

        {isCustomerOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setIsCustomerOpen(false)} />
            <div className="absolute z-20 w-full mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {customersLoading ? (
                <div className="p-4 text-center text-gray-400">Loading...</div>
              ) : customers.length > 0 ? (
                customers.map((customer) => (
                  <button
                    type="button"
                    key={customer.id}
                    className="w-full px-4 py-2 text-left hover:bg-gray-700 border-b border-gray-700 last:border-0"
                    onClick={() => handleSelectCustomer(customer)}
                  >
                    <div className="font-medium text-gray-100">{customer.name}</div>
                    {customer.contact_email && (
                      <div className="text-sm text-gray-400">{customer.contact_email}</div>
                    )}
                  </button>
                ))
              ) : customerSearch ? (
                <div className="p-4 text-center text-gray-400">
                  No customers found for "{customerSearch}"
                </div>
              ) : (
                <div className="p-4 text-center text-gray-400">
                  Start typing to search customers
                </div>
              )}
              <button
                type="button"
                className="w-full px-4 py-3 text-left hover:bg-gray-700 flex items-center gap-2 text-primary-400 font-medium border-t border-gray-700"
                onClick={() => {
                  setShowCreateCustomer(true);
                  setIsCustomerOpen(false);
                  setNewCustomerName(customerSearch);
                }}
              >
                <Plus className="w-4 h-4" />
                Create new customer
              </button>
            </div>
          </>
        )}
      </div>

      {/* Brand Selection - only shown after customer is selected */}
      {customerId && (
        <div className="relative">
          <label className="label">Brand</label>
          <p className="text-sm text-gray-400 mb-2">
            The company/brand whose logo will appear on the hat
          </p>
          <input
            type="text"
            className="input"
            placeholder="Search or select a brand..."
            value={brandSearch}
            onChange={(e) => {
              setBrandSearch(e.target.value);
              setIsBrandOpen(true);
              if (!e.target.value) {
                onBrandChange('');
              }
            }}
            onFocus={() => setIsBrandOpen(true)}
          />

          {isBrandOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setIsBrandOpen(false)} />
              <div className="absolute z-20 w-full mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                {brandsLoading ? (
                  <div className="p-4 text-center text-gray-400">Loading...</div>
                ) : brands.length > 0 ? (
                  brands.map((brand) => (
                    <button
                      type="button"
                      key={brand.id}
                      className="w-full px-4 py-2 text-left hover:bg-gray-700 border-b border-gray-700 last:border-0"
                      onClick={() => handleSelectBrand(brand)}
                    >
                      <div className="font-medium text-gray-100">{brand.name}</div>
                      {brand.website && (
                        <div className="text-sm text-gray-400">{brand.website}</div>
                      )}
                    </button>
                  ))
                ) : brandSearch ? (
                  <div className="p-4 text-center text-gray-400">
                    No brands found for "{brandSearch}"
                  </div>
                ) : (
                  <div className="p-4 text-center text-gray-400">
                    No brands yet. Create one below.
                  </div>
                )}
                <button
                  type="button"
                  className="w-full px-4 py-3 text-left hover:bg-gray-700 flex items-center gap-2 text-primary-400 font-medium border-t border-gray-700"
                  onClick={() => {
                    setShowCreateBrand(true);
                    setIsBrandOpen(false);
                    setNewBrandName(brandSearch);
                  }}
                >
                  <Plus className="w-4 h-4" />
                  Create new brand
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Create Customer Modal */}
      {showCreateCustomer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
          <div className="bg-gray-900 rounded-xl shadow-xl w-full max-w-md mx-4 p-6 border border-gray-800">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-100">Create New Customer</h3>
              <button
                type="button"
                onClick={() => setShowCreateCustomer(false)}
                className="text-gray-400 hover:text-gray-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-gray-400 mb-4">
              A customer is a promotional distributor who orders designs.
            </p>

            <div className="space-y-4">
              <Input
                label="Customer Name *"
                value={newCustomerName}
                onChange={(e) => setNewCustomerName(e.target.value)}
                placeholder="Enter customer/distributor name"
              />
              <Input
                label="Contact Email"
                value={newCustomerEmail}
                onChange={(e) => setNewCustomerEmail(e.target.value)}
                placeholder="contact@company.com"
              />
              <Input
                label="Notes"
                value={newCustomerNotes}
                onChange={(e) => setNewCustomerNotes(e.target.value)}
                placeholder="Optional notes about this customer"
              />
            </div>

            <div className="flex gap-3 mt-6">
              <Button
                type="button"
                variant="outline"
                className="flex-1"
                onClick={() => setShowCreateCustomer(false)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                className="flex-1"
                onClick={handleCreateCustomer}
                isLoading={createCustomer.isPending}
                disabled={!newCustomerName.trim()}
              >
                Create Customer
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Create Brand Modal */}
      {showCreateBrand && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
          <div className="bg-gray-900 rounded-xl shadow-xl w-full max-w-md mx-4 p-6 border border-gray-800">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-100">Create New Brand</h3>
              <button
                type="button"
                onClick={() => setShowCreateBrand(false)}
                className="text-gray-400 hover:text-gray-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-gray-400 mb-4">
              A brand is the company whose logo will be featured on the hat design.
            </p>

            <div className="space-y-4">
              <Input
                label="Brand Name *"
                value={newBrandName}
                onChange={(e) => setNewBrandName(e.target.value)}
                placeholder="Enter brand/company name"
              />
              <Input
                label="Website"
                value={newBrandWebsite}
                onChange={(e) => setNewBrandWebsite(e.target.value)}
                placeholder="https://example.com"
              />
            </div>

            <div className="flex gap-3 mt-6">
              <Button
                type="button"
                variant="outline"
                className="flex-1"
                onClick={() => setShowCreateBrand(false)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                className="flex-1"
                onClick={handleCreateBrand}
                isLoading={createBrand.isPending}
                disabled={!newBrandName.trim()}
              >
                Create Brand
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
