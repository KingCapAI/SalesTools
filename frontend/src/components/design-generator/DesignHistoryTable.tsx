import { useState } from 'react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { Eye, Trash2, Search } from 'lucide-react';
import { Button } from '../ui/Button';
import { uploadsApi } from '../../api/uploads';
import type { DesignListItem } from '../../types/api';

interface DesignHistoryTableProps {
  designs: DesignListItem[];
  onDelete: (id: string) => void;
  isLoading?: boolean;
}

export function DesignHistoryTable({ designs, onDelete, isLoading }: DesignHistoryTableProps) {
  const [search, setSearch] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const filteredDesigns = designs.filter((design) =>
    design.brand_name?.toLowerCase().includes(search.toLowerCase()) ||
    design.customer_name?.toLowerCase().includes(search.toLowerCase())
  );

  const handleDelete = (id: string) => {
    if (deleteId === id) {
      onDelete(id);
      setDeleteId(null);
    } else {
      setDeleteId(id);
      // Reset after 3 seconds if not confirmed
      setTimeout(() => setDeleteId(null), 3000);
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-16 bg-gray-100 rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div>
      {/* Search */}
      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by brand or customer name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10"
          />
        </div>
      </div>

      {/* Table */}
      {filteredDesigns.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">
            {search ? 'No designs found matching your search' : 'No designs yet'}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Preview
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Design
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Brand
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Customer
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Style
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredDesigns.map((design) => (
                <tr key={design.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="w-12 h-12 rounded bg-gray-100 overflow-hidden">
                      {design.latest_image_path ? (
                        <img
                          src={uploadsApi.getFileUrl(design.latest_image_path)}
                          alt={`Design #${design.design_number}`}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-400">
                          <span role="img" aria-label="hat">🧢</span>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">
                      Design #{design.design_number}
                    </div>
                    <div className="text-sm text-gray-500">
                      v{design.current_version}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 font-medium">
                    {design.brand_name || 'Unknown'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {design.customer_name || '-'}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700 capitalize">
                      {design.style_directions?.join(', ') || '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {format(new Date(design.created_at), 'MMM d, yyyy')}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link to={`/ai-design-generator/${design.id}`}>
                        <Button variant="ghost" size="sm">
                          <Eye className="w-4 h-4" />
                        </Button>
                      </Link>
                      <Button
                        variant={deleteId === design.id ? 'danger' : 'ghost'}
                        size="sm"
                        onClick={() => handleDelete(design.id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
