import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/Button';
import { ActionMenu } from '../components/ui/ActionMenu';
import { Tabs } from '../components/ui/Tabs';
import { VersionGallery } from '../components/design-generator/VersionGallery';
import { RevisionChat } from '../components/design-generator/RevisionChat';
import { QuoteModal } from '../components/design-generator/QuoteModal';
import { QuoteSummary } from '../components/design-generator/QuoteSummary';
import { ProductionTimeline } from '../components/design-generator/ProductionTimeline';
import {
  useCustomDesign,
  useCreateCustomDesignRevision,
  useAddCustomDesignChatMessage,
  useUpdateCustomDesign,
  useRegenerateCustomDesign,
  useSelectCustomVersion,
  useDeleteCustomVersion,
} from '../hooks/useCustomDesigns';
import { useDesignQuote, useDeleteDesignQuote, useExportDesignWithQuote } from '../hooks/useDesignQuotes';
import {
  ArrowLeft, Plus, CheckCircle, XCircle, Clock, Download,
  Calculator, RefreshCw, Layers, Pencil, MessageSquare, CalendarDays,
} from 'lucide-react';
import { uploadsApi } from '../api/uploads';
import type { ApprovalStatus } from '../types/api';

const approvalStatusConfig: Record<ApprovalStatus, { label: string; icon: typeof Clock; color: string; bgColor: string }> = {
  pending: { label: 'Pending', icon: Clock, color: 'text-yellow-400', bgColor: 'bg-yellow-900/30' },
  approved: { label: 'Approved', icon: CheckCircle, color: 'text-green-400', bgColor: 'bg-green-900/30' },
  rejected: { label: 'Rejected', icon: XCircle, color: 'text-red-400', bgColor: 'bg-red-900/30' },
};

// Side labels use WEARER's perspective to match the result template's
// "WEARERS LEFT" / "WEARERS RIGHT" labels and the AI placement prompts.
const LOCATION_LABELS: Record<string, string> = {
  front: 'Front',
  front_lower_left: "Front Lower (Wearer's Left)",
  front_lower_right: "Front Lower (Wearer's Right)",
  left: "Wearer's Left",
  right: "Wearer's Right",
  back: 'Back',
  visor: 'Visor',
};

const DECORATION_METHOD_LABELS: Record<string, string> = {
  embroidery: 'Embroidery', screen_print: 'Screen Print', patch: 'Patch',
  '3d_puff': '3D Puff', laser_cut: 'Laser Cut', heat_transfer: 'Heat Transfer', sublimation: 'Sublimation',
};

export function CustomDesignDetail() {
  const { designId } = useParams<{ designId: string }>();
  const navigate = useNavigate();

  const { data: design, isLoading, refetch } = useCustomDesign(designId || '');
  const createRevision = useCreateCustomDesignRevision();
  const addChatMessage = useAddCustomDesignChatMessage();
  const updateDesign = useUpdateCustomDesign();
  const regenerateDesign = useRegenerateCustomDesign();
  const selectVersion = useSelectCustomVersion();
  const deleteVersion = useDeleteCustomVersion();

  const { data: designQuote, refetch: refetchQuote } = useDesignQuote(designId || '');
  const deleteQuote = useDeleteDesignQuote();
  const exportQuote = useExportDesignWithQuote();

  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [quoteModalOpen, setQuoteModalOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [sidebarTab, setSidebarTab] = useState('chat');

  useEffect(() => {
    if (design?.selected_version_id && !selectedVersionId) {
      setSelectedVersionId(design.selected_version_id);
    }
  }, [design?.selected_version_id]);

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
            <Link to="/custom-design-builder" className="text-primary-400 hover:underline mt-2 inline-block">
              Go back to Custom Design Dashboard
            </Link>
          </div>
        </main>
      </div>
    );
  }

  const versions = design.versions || [];
  const chats = design.chats || [];
  const selectedVersion = selectedVersionId
    ? versions.find((v) => v.id === selectedVersionId)
    : null;

  const hasRevisions = chats.some((c) => c.is_user);
  const statusConfig = approvalStatusConfig[design.approval_status];
  const StatusIcon = statusConfig.icon;

  const handleSelectVersion = async (versionId: string) => {
    if (!designId) return;
    setSelectedVersionId(versionId);
    try {
      await selectVersion.mutateAsync({ designId, versionId });
    } catch (error: any) {
      console.error('Error selecting version:', error);
    }
  };

  const handleDeleteVersion = async (versionId: string) => {
    if (!designId) return;
    try {
      await deleteVersion.mutateAsync({ designId, versionId });
      if (selectedVersionId === versionId) {
        setSelectedVersionId(null);
      }
      refetch();
    } catch (error: any) {
      alert(error?.response?.data?.detail || 'Failed to delete version');
    }
  };

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
    if (newVersion?.id) {
      setSelectedVersionId(newVersion.id);
    } else if (result.data?.versions?.length) {
      const versions = result.data.versions;
      setSelectedVersionId(versions[versions.length - 1].id);
    }
  };

  const handleRegenerate = async () => {
    if (!designId) return;
    try {
      await regenerateDesign.mutateAsync(designId);
      setSelectedVersionId(null);
      await refetch();
    } catch (error: any) {
      console.error('Error regenerating design:', error);
      alert(`Failed to regenerate: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
    }
  };

  const handleCopyAndEdit = () => {
    const prefill = {
      customerName: design.customer_name,
      brandName: design.brand_name,
      designName: design.design_name || '',
      hatStyle: design.hat_style,
      material: design.material,
      structure: design.structure || '',
      closure: design.closure || '',
      crownColor: design.crown_color || '',
      visorColor: design.visor_color || '',
      locationLogos: (design.location_logos || []).map((l) => ({
        location: l.location,
        logo_path: l.logo_path,
        logo_filename: l.logo_filename,
        decoration_method: l.decoration_method,
        size: l.size,
        size_details: l.size_details,
      })),
      referenceHatPath: design.reference_hat_path || '',
    };
    navigate('/custom-design-builder/new', { state: { prefill } });
  };

  const handleDownload = async () => {
    if (!selectedVersion?.image_path) {
      alert('No design image available to download');
      return;
    }

    const fileName = `King Cap Custom Design ${design.design_number}.png`;

    try {
      const blob = await uploadsApi.downloadFile(selectedVersion.image_path, fileName);
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
    await updateDesign.mutateAsync({ id: designId, data: { approval_status: status } });
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
      link.download = `custom_design_${design?.design_number}_quote.${format}`;
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

  const actionItems = [
    { icon: RefreshCw, label: 'Regenerate', onClick: handleRegenerate, loading: regenerateDesign.isPending, hidden: hasRevisions },
    { icon: Pencil, label: 'Copy & Edit', onClick: handleCopyAndEdit },
    { icon: Download, label: 'Download', onClick: handleDownload, disabled: !selectedVersion?.image_path },
  ];

  const sidebarTabs = [
    { id: 'chat', label: 'Revision Chat', icon: MessageSquare, badge: chats.length > 0 },
    { id: 'details', label: 'Details', icon: Layers },
    { id: 'quote', label: 'Quote', icon: Calculator, badge: !!designQuote },
    { id: 'timeline', label: 'Timeline', icon: CalendarDays },
  ];

  return (
    <div className="min-h-screen bg-black">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header — responsive */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-4 min-w-0">
            <Link to="/custom-design-builder">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            </Link>
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0">
                <Layers className="w-5 h-5 text-white" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <h1 className="text-xl lg:text-2xl font-bold text-gray-100 truncate">
                    {design.design_name || `Custom Design #${design.design_number}`}
                  </h1>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 flex-shrink-0 ${statusConfig.bgColor} ${statusConfig.color}`}>
                    <StatusIcon className="w-3 h-3" />
                    {statusConfig.label}
                  </span>
                </div>
                <p className="text-gray-400 text-sm truncate">
                  {design.brand_name} • {design.hat_style.replace(/-/g, ' ')} • {design.location_logos.length} decoration{design.location_logos.length !== 1 ? 's' : ''}
                </p>
              </div>
            </div>
          </div>

          {/* Actions — responsive */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="hidden lg:flex items-center gap-2">
              {!hasRevisions && (
                <Button variant="outline" size="sm" onClick={handleRegenerate} isLoading={regenerateDesign.isPending} title="Generate 3 new design options">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Regenerate
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={handleCopyAndEdit} title="Open form pre-filled with these inputs">
                <Pencil className="w-4 h-4 mr-2" />
                Copy & Edit
              </Button>
              <Button variant="outline" size="sm" onClick={handleDownload} disabled={!selectedVersion?.image_path}>
                <Download className="w-4 h-4 mr-2" />
                Download
              </Button>
            </div>

            <div className="hidden md:flex lg:hidden items-center gap-1">
              {!hasRevisions && (
                <Button variant="outline" size="sm" onClick={handleRegenerate} isLoading={regenerateDesign.isPending} title="Regenerate">
                  <RefreshCw className="w-4 h-4" />
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={handleCopyAndEdit} title="Copy & Edit">
                <Pencil className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={handleDownload} disabled={!selectedVersion?.image_path} title="Download">
                <Download className="w-4 h-4" />
              </Button>
            </div>

            <div className="md:hidden">
              <ActionMenu items={actionItems} />
            </div>

            <Link to="/custom-design-builder/new">
              <Button size="sm">
                <Plus className="w-4 h-4 sm:mr-2" />
                <span className="hidden sm:inline">New Design</span>
              </Button>
            </Link>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Design Gallery */}
          <div className="lg:col-span-2">
            <div className="card">
              <VersionGallery
                versions={versions}
                designNumber={design.design_number}
                selectedVersionId={selectedVersionId}
                onSelectVersion={handleSelectVersion}
                onDeleteVersion={handleDeleteVersion}
                deletingVersionId={deleteVersion.isPending ? (deleteVersion.variables?.versionId ?? null) : null}
                isLoading={regenerateDesign.isPending}
              />
            </div>
          </div>

          {/* Sidebar — sticky on desktop */}
          <div className="lg:sticky lg:top-24 lg:self-start lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto space-y-4">
            {/* Approval Status */}
            <div className="card">
              <h3 className="font-semibold text-white mb-3 text-sm">Approval Status</h3>
              <div className="flex flex-wrap gap-2">
                <Button variant={design.approval_status === 'approved' ? 'secondary' : 'outline'} size="sm" onClick={() => handleSetApprovalStatus('approved')} disabled={updateDesign.isPending}>
                  <CheckCircle className="w-4 h-4 mr-1" /> Approve
                </Button>
                <Button variant={design.approval_status === 'rejected' ? 'danger' : 'outline'} size="sm" onClick={() => handleSetApprovalStatus('rejected')} disabled={updateDesign.isPending}>
                  <XCircle className="w-4 h-4 mr-1" /> Reject
                </Button>
                <Button variant={design.approval_status === 'pending' ? 'secondary' : 'outline'} size="sm" onClick={() => handleSetApprovalStatus('pending')} disabled={updateDesign.isPending}>
                  <Clock className="w-4 h-4 mr-1" /> Pending
                </Button>
              </div>
            </div>

            {/* Tabbed sections */}
            <div className="card p-0 overflow-hidden">
              <Tabs tabs={sidebarTabs} activeTab={sidebarTab} onTabChange={setSidebarTab}>
                {sidebarTab === 'chat' && (
                  <>
                    {selectedVersionId ? (
                      <>
                        {selectedVersion && (
                          <p className="text-xs text-gray-500 mb-2">
                            Revisions based on Option {selectedVersion.version_number}. Select a different version from the gallery.
                          </p>
                        )}
                        <RevisionChat
                          chats={chats}
                          onSendMessage={handleSendMessage}
                          onRequestRevision={handleRequestRevision}
                          isLoading={createRevision.isPending || addChatMessage.isPending || regenerateDesign.isPending}
                        />
                      </>
                    ) : (
                      <div className="text-center py-8 text-gray-500 text-sm">
                        <p>Select a design option to enable revisions.</p>
                      </div>
                    )}
                  </>
                )}

                {sidebarTab === 'details' && (
                  <div className="space-y-3">
                    {design.location_logos.map((logo) => (
                      <div key={logo.id} className="flex items-center gap-3 p-2 bg-gray-800/50 rounded-lg">
                        <img
                          src={uploadsApi.getFileUrl(logo.logo_path)}
                          alt={`${logo.location} logo`}
                          className="w-10 h-10 object-contain rounded"
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-white">
                            {LOCATION_LABELS[logo.location] || logo.location}
                          </p>
                          <p className="text-xs text-gray-400 truncate">
                            {DECORATION_METHOD_LABELS[logo.decoration_method] || logo.decoration_method} • {logo.size}
                            {logo.size_details && ` (${logo.size_details})`}
                          </p>
                        </div>
                      </div>
                    ))}
                    {design.reference_hat_path && (
                      <div className="pt-3 border-t border-gray-700">
                        <p className="text-xs text-gray-400 mb-2">Reference Hat</p>
                        <img
                          src={uploadsApi.getFileUrl(design.reference_hat_path)}
                          alt="Reference hat"
                          className="w-full max-w-[120px] rounded"
                        />
                      </div>
                    )}
                  </div>
                )}

                {sidebarTab === 'quote' && (
                  <QuoteSummary
                    quote={designQuote || design.quote_summary || null}
                    onEdit={() => setQuoteModalOpen(true)}
                    onDelete={handleDeleteQuote}
                    onExport={handleExportQuote}
                    isDeleting={deleteQuote.isPending}
                    isExporting={isExporting}
                  />
                )}

                {sidebarTab === 'timeline' && (
                  <ProductionTimeline quoteData={designQuote} alwaysExpanded />
                )}
              </Tabs>
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
          designData={design}
          selectedVersion={selectedVersion}
          onSaved={() => {
            refetchQuote();
            refetch();
          }}
        />
      )}
    </div>
  );
}
