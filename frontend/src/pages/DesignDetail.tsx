import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/Button';
import { DesignPreview } from '../components/design-generator/DesignPreview';
import { VersionHistory } from '../components/design-generator/VersionHistory';
import { RevisionChat } from '../components/design-generator/RevisionChat';
import { QuoteModal } from '../components/design-generator/QuoteModal';
import { QuoteSummary } from '../components/design-generator/QuoteSummary';
import { useDesign, useCreateRevision, useAddChatMessage, useUpdateDesign } from '../hooks/useDesigns';
import { useDesignQuote, useDeleteDesignQuote, useExportDesignWithQuote } from '../hooks/useDesignQuotes';
import { ArrowLeft, Plus, CheckCircle, XCircle, Clock, Download, Calculator } from 'lucide-react';
import { uploadsApi } from '../api/uploads';
import type { ApprovalStatus } from '../types/api';

const approvalStatusConfig: Record<ApprovalStatus, { label: string; icon: typeof Clock; color: string; bgColor: string }> = {
  pending: { label: 'Pending', icon: Clock, color: 'text-yellow-400', bgColor: 'bg-yellow-900/30' },
  approved: { label: 'Approved', icon: CheckCircle, color: 'text-green-400', bgColor: 'bg-green-900/30' },
  rejected: { label: 'Rejected', icon: XCircle, color: 'text-red-400', bgColor: 'bg-red-900/30' },
};

export function DesignDetail() {
  const { designId } = useParams<{ designId: string }>();

  const { data: design, isLoading, refetch } = useDesign(designId || '');
  const createRevision = useCreateRevision();
  const addChatMessage = useAddChatMessage();
  const updateDesign = useUpdateDesign();

  // Quote hooks
  const { data: designQuote, refetch: refetchQuote } = useDesignQuote(designId || '');
  const deleteQuote = useDeleteDesignQuote();
  const exportQuote = useExportDesignWithQuote();

  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [quoteModalOpen, setQuoteModalOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black">
        <Header />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="animate-pulse space-y-4">
            <div className="h-8 w-48 bg-gray-800 rounded" />
            <div className="h-96 bg-gray-800 rounded-xl" />
          </div>
        </main>
      </div>
    );
  }

  if (!design) {
    return (
      <div className="min-h-screen bg-black">
        <Header />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center py-16">
            <p className="text-gray-400">Design not found</p>
            <Link to="/ai-design-generator" className="text-primary-400 hover:underline mt-2 inline-block">
              Go back to Design Dashboard
            </Link>
          </div>
        </main>
      </div>
    );
  }

  const versions = design.versions || [];
  const selectedVersion = selectedVersionId
    ? versions.find((v) => v.id === selectedVersionId)
    : versions[0];

  const statusConfig = approvalStatusConfig[design.approval_status];
  const StatusIcon = statusConfig.icon;

  const handleSendMessage = async (message: string) => {
    if (!designId) return;
    await addChatMessage.mutateAsync({ designId, message });
    refetch();
  };

  const handleRequestRevision = async (notes: string) => {
    if (!designId) return;
    const newVersion = await createRevision.mutateAsync({
      designId,
      data: { revision_notes: notes },
    });
    const result = await refetch();
    // Auto-switch to the newest version
    if (newVersion?.id) {
      setSelectedVersionId(newVersion.id);
    } else if (result.data?.versions?.length) {
      // Fallback: select the last version (highest version number)
      const versions = result.data.versions;
      setSelectedVersionId(versions[versions.length - 1].id);
    }
  };

  const handleDownload = async () => {
    if (!selectedVersion?.image_path) {
      alert('No design image available to download');
      return;
    }

    const designName = `King Cap Design ${design.design_number}`;
    const fileName = `${designName}.png`;

    try {
      const imageUrl = uploadsApi.getFileUrl(selectedVersion.image_path);
      const response = await fetch(imageUrl, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const blob = await response.blob();

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading design:', error);
      alert('Failed to download design');
    }
  };

  const handleSetApprovalStatus = async (status: ApprovalStatus) => {
    if (!designId) return;
    await updateDesign.mutateAsync({
      id: designId,
      data: { approval_status: status },
    });
    refetch();
  };

  const handleDeleteQuote = async () => {
    if (!designId) return;
    if (!confirm('Are you sure you want to delete this quote?')) return;
    await deleteQuote.mutateAsync(designId);
    refetchQuote();
  };

  const handleExportQuote = async (format: 'xlsx' | 'pdf') => {
    if (!designId) return;
    setIsExporting(true);
    try {
      const blob = await exportQuote.mutateAsync({ designId, format });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `design_${design?.design_number}_quote.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting quote:', error);
      alert('Failed to export quote');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-black">
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
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-gray-100">
                  {design.design_name || `Design #${design.design_number}`}
                </h1>
                <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${statusConfig.bgColor} ${statusConfig.color}`}>
                  <StatusIcon className="w-3 h-3" />
                  {statusConfig.label}
                </span>
              </div>
              <p className="text-gray-400">
                {design.brand_name} • {design.style_directions.join(', ')} • {design.hat_style.replace(/-/g, ' ')}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setQuoteModalOpen(true)}
            >
              <Calculator className="w-4 h-4 mr-2" />
              {designQuote ? 'Edit Quote' : 'Quote'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              disabled={!selectedVersion?.image_path}
            >
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
            <Link to="/ai-design-generator/new">
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                New Design
              </Button>
            </Link>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Design Preview - Main Column */}
          <div className="lg:col-span-2">
            <div className="card">
              <DesignPreview
                version={selectedVersion || null}
                designNumber={design.design_number}
                isLoading={createRevision.isPending}
              />
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Approval Status */}
            <div className="card">
              <h3 className="font-semibold text-white mb-4">Approval Status</h3>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={design.approval_status === 'approved' ? 'secondary' : 'outline'}
                  size="sm"
                  onClick={() => handleSetApprovalStatus('approved')}
                  disabled={updateDesign.isPending}
                >
                  <CheckCircle className="w-4 h-4 mr-1" />
                  Approve
                </Button>
                <Button
                  variant={design.approval_status === 'rejected' ? 'danger' : 'outline'}
                  size="sm"
                  onClick={() => handleSetApprovalStatus('rejected')}
                  disabled={updateDesign.isPending}
                >
                  <XCircle className="w-4 h-4 mr-1" />
                  Reject
                </Button>
                <Button
                  variant={design.approval_status === 'pending' ? 'secondary' : 'outline'}
                  size="sm"
                  onClick={() => handleSetApprovalStatus('pending')}
                  disabled={updateDesign.isPending}
                >
                  <Clock className="w-4 h-4 mr-1" />
                  Pending
                </Button>
              </div>
            </div>

            {/* Quote Summary */}
            <div className="card">
              <QuoteSummary
                quote={designQuote || design.quote_summary || null}
                onEdit={() => setQuoteModalOpen(true)}
                onDelete={handleDeleteQuote}
                onExport={handleExportQuote}
                isDeleting={deleteQuote.isPending}
                isExporting={isExporting}
              />
            </div>

            {/* Version History */}
            <div className="card">
              <VersionHistory
                versions={versions}
                designNumber={design.design_number}
                selectedVersionId={selectedVersion?.id || null}
                onSelectVersion={setSelectedVersionId}
              />
            </div>

            {/* Revision Chat */}
            <div className="card">
              <RevisionChat
                chats={design.chats || []}
                onSendMessage={handleSendMessage}
                onRequestRevision={handleRequestRevision}
                isLoading={createRevision.isPending || addChatMessage.isPending}
              />
            </div>
          </div>
        </div>
      </main>

      {/* Quote Modal */}
      {designId && (
        <QuoteModal
          isOpen={quoteModalOpen}
          onClose={() => setQuoteModalOpen(false)}
          designId={designId}
          existingQuote={designQuote || undefined}
          onSaved={() => {
            refetchQuote();
            refetch();
          }}
        />
      )}
    </div>
  );
}
