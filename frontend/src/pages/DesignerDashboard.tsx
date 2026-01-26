import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/Button';
import { useDesigns, useDeleteDesign } from '../hooks/useDesigns';
import { uploadsApi } from '../api/uploads';
import { format } from 'date-fns';
import {
  Plus,
  Search,
  Filter,
  Eye,
  Trash2,
  CheckCircle,
  XCircle,
  Clock,
  ArrowLeft,
} from 'lucide-react';
import type { DesignListItem, ApprovalStatus } from '../types/api';

const approvalStatusConfig: Record<ApprovalStatus, { label: string; icon: typeof Clock; color: string }> = {
  pending: { label: 'Pending', icon: Clock, color: 'text-yellow-400 bg-yellow-900/30' },
  approved: { label: 'Approved', icon: CheckCircle, color: 'text-green-400 bg-green-900/30' },
  rejected: { label: 'Rejected', icon: XCircle, color: 'text-red-400 bg-red-900/30' },
};

export function DesignerDashboard() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<ApprovalStatus | ''>('');
  const [deleteId, setDeleteId] = useState<string | null>(null);

  // Fetch all designs
  const { data: designs = [], isLoading } = useDesigns({});

  const deleteDesign = useDeleteDesign();

  // Filter designs
  const filteredDesigns = designs.filter((design) => {
    const matchesSearch =
      !search ||
      design.brand_name?.toLowerCase().includes(search.toLowerCase()) ||
      design.customer_name?.toLowerCase().includes(search.toLowerCase()) ||
      design.design_name?.toLowerCase().includes(search.toLowerCase());

    const matchesStatus = !statusFilter || design.approval_status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const handleDelete = (id: string) => {
    if (deleteId === id) {
      deleteDesign.mutate(id);
      setDeleteId(null);
    } else {
      setDeleteId(id);
      setTimeout(() => setDeleteId(null), 3000);
    }
  };

  const stats = {
    total: designs.length,
    pending: designs.filter((d) => d.approval_status === 'pending').length,
    approved: designs.filter((d) => d.approval_status === 'approved').length,
    rejected: designs.filter((d) => d.approval_status === 'rejected').length,
  };

  return (
    <div className="min-h-screen bg-black">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/dashboard">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-100">Design Dashboard</h1>
              <p className="text-gray-400">Manage and create hat designs</p>
            </div>
          </div>
          <Link to="/ai-design-generator/new">
            <Button size="lg">
              <Plus className="w-5 h-5 mr-2" />
              Create New Design
            </Button>
          </Link>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="card">
            <div className="text-sm text-gray-400">Total Designs</div>
            <div className="text-2xl font-bold text-gray-100">{stats.total}</div>
          </div>
          <div className="card">
            <div className="text-sm text-yellow-400">Pending Review</div>
            <div className="text-2xl font-bold text-yellow-400">{stats.pending}</div>
          </div>
          <div className="card">
            <div className="text-sm text-green-400">Approved</div>
            <div className="text-2xl font-bold text-green-400">{stats.approved}</div>
          </div>
          <div className="card">
            <div className="text-sm text-red-400">Rejected</div>
            <div className="text-2xl font-bold text-red-400">{stats.rejected}</div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-4 mb-6">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search by brand, customer, or design name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as ApprovalStatus | '')}
              className="input pl-10 pr-8 appearance-none cursor-pointer"
            >
              <option value="">All Status</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>

        {/* Designs Grid/Table */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="card animate-pulse">
                <div className="aspect-square bg-gray-800 rounded-lg mb-4" />
                <div className="h-4 bg-gray-800 rounded mb-2" />
                <div className="h-3 bg-gray-800 rounded w-2/3" />
              </div>
            ))}
          </div>
        ) : filteredDesigns.length === 0 ? (
          <div className="card text-center py-12">
            <div className="text-gray-500 mb-4">
              <Search className="w-12 h-12 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-100 mb-2">
              {search || statusFilter ? 'No designs found' : 'No designs yet'}
            </h3>
            <p className="text-gray-400 mb-4">
              {search || statusFilter
                ? 'Try adjusting your search or filters'
                : 'Create your first design to get started'}
            </p>
            {!search && !statusFilter && (
              <Link to="/ai-design-generator/new">
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Design
                </Button>
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDesigns.map((design) => (
              <DesignCard
                key={design.id}
                design={design}
                onDelete={() => handleDelete(design.id)}
                isDeleting={deleteId === design.id}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

interface DesignCardProps {
  design: DesignListItem;
  onDelete: () => void;
  isDeleting: boolean;
}

function DesignCard({ design, onDelete, isDeleting }: DesignCardProps) {
  const statusConfig = approvalStatusConfig[design.approval_status];
  const StatusIcon = statusConfig.icon;

  return (
    <div className="card overflow-hidden group">
      {/* Image */}
      <div className="aspect-square bg-gray-800 -mx-6 -mt-6 mb-4 relative overflow-hidden">
        {design.latest_image_path ? (
          <img
            src={uploadsApi.getFileUrl(design.latest_image_path)}
            alt={design.design_name || `Design #${design.design_number}`}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-500 text-4xl">
            <span role="img" aria-label="hat">🧢</span>
          </div>
        )}

        {/* Hover Actions */}
        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
          <Link to={`/ai-design-generator/design/${design.id}`}>
            <Button variant="secondary" size="sm">
              <Eye className="w-4 h-4 mr-1" />
              View
            </Button>
          </Link>
          <Button
            variant={isDeleting ? 'danger' : 'secondary'}
            size="sm"
            onClick={onDelete}
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>

        {/* Status Badge */}
        <div
          className={`absolute top-2 right-2 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${statusConfig.color}`}
        >
          <StatusIcon className="w-3 h-3" />
          {statusConfig.label}
        </div>
      </div>

      {/* Content */}
      <div>
        <h3 className="font-semibold text-gray-100 truncate">
          {design.design_name || `Design #${design.design_number}`}
        </h3>
        <p className="text-sm text-gray-400 truncate">{design.brand_name}</p>
        {design.customer_name && (
          <p className="text-xs text-gray-500 truncate">for {design.customer_name}</p>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-800 text-xs text-gray-500">
        <span>Created {format(new Date(design.created_at), 'MMM d, yyyy')}</span>
        <span>v{design.current_version}</span>
      </div>
      {design.updated_at !== design.created_at && (
        <div className="text-xs text-gray-500 mt-1">
          Last edited {format(new Date(design.updated_at), 'MMM d, yyyy')}
        </div>
      )}
    </div>
  );
}
