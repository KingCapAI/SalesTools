import { Calculator, Edit2, Trash2, FileSpreadsheet, FileText } from 'lucide-react';
import { Button } from '../ui/Button';
import type { QuoteSummary as QuoteSummaryType } from '../../types/api';
import type { DesignQuote } from '../../api/designQuotes';

interface QuoteSummaryProps {
  quote: DesignQuote | QuoteSummaryType | null;
  onEdit: () => void;
  onDelete: () => void;
  onExport: (format: 'xlsx' | 'pdf') => void;
  isDeleting?: boolean;
  isExporting?: boolean;
}

export function QuoteSummary({ quote, onEdit, onDelete, onExport, isDeleting, isExporting }: QuoteSummaryProps) {
  if (!quote) {
    return (
      <div>
        <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
          <Calculator className="w-4 h-4" />
          Quote
        </h3>
        <div className="text-center py-6">
          <div className="w-12 h-12 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-3">
            <Calculator className="w-6 h-6 text-gray-500" />
          </div>
          <p className="text-sm text-gray-400 mb-4">No quote attached to this design</p>
          <Button variant="secondary" size="sm" onClick={onEdit}>
            <Calculator className="w-4 h-4 mr-2" />
            Create Quote
          </Button>
        </div>
      </div>
    );
  }

  const formatCurrency = (value: number | null | undefined) => {
    if (value == null) return 'N/A';
    return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div>
      <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
        <Calculator className="w-4 h-4" />
        Quote
      </h3>

      {/* Quote Type Badge */}
      <div className="flex items-center gap-2 mb-4">
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          quote.quote_type === 'domestic'
            ? 'bg-blue-900/50 text-blue-300'
            : 'bg-green-900/50 text-green-300'
        }`}>
          {quote.quote_type.charAt(0).toUpperCase() + quote.quote_type.slice(1)}
        </span>
        <span className="text-sm text-gray-400">
          {quote.quantity.toLocaleString()} pcs
        </span>
      </div>

      {/* Pricing */}
      <div className="bg-gray-800 rounded-lg p-4 mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-gray-400">Per Piece</span>
          <span className="text-lg font-semibold text-gray-100">
            {formatCurrency(quote.cached_per_piece)}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-400">Total</span>
          <span className="text-xl font-bold text-primary-400">
            {formatCurrency(quote.cached_total)}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" size="sm" onClick={onEdit}>
          <Edit2 className="w-4 h-4 mr-1" />
          Edit
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onExport('xlsx')}
          isLoading={isExporting}
        >
          <FileSpreadsheet className="w-4 h-4 mr-1" />
          Excel
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onExport('pdf')}
          isLoading={isExporting}
        >
          <FileText className="w-4 h-4 mr-1" />
          PDF
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onDelete}
          isLoading={isDeleting}
          className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>

      {/* Last Updated */}
      {'updated_at' in quote && quote.updated_at && (
        <p className="text-xs text-gray-500 mt-3">
          Updated {new Date(quote.updated_at).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}
