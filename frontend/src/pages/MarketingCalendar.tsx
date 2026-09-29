import { useCallback, useEffect, useRef, useState } from 'react';
import { Pencil, X, RotateCcw } from 'lucide-react';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/Button';
import { contentApi } from '../api/content';
import { CalendarEditor } from '../components/resources/CalendarEditor';
import type { CalendarData } from '../components/resources/CalendarEditor';
import calendarHtml from '../content/marketing-calendar-2027.html?raw';
import defaultData from '../content/marketing-calendar-2027.json';

const CONTENT_KEY = 'marketing-calendar-2027';

/**
 * 2027 Marketing Calendar.
 * The visual calendar is a self-contained HTML page (src/content/marketing-calendar-2027.html)
 * rendered in a sandboxed iframe. Its content comes from the backend (/api/content/…) so
 * editors can change copy and dates in place; the bundled JSON is the fallback.
 * Edit access is decided server-side (Settings.content_editor_emails).
 */
export function MarketingCalendar() {
  const frame = useRef<HTMLIFrameElement>(null);
  const [saved, setSaved] = useState<CalendarData>(defaultData as CalendarData);
  const [draft, setDraft] = useState<CalendarData | null>(null);
  const [canEdit, setCanEdit] = useState(false);
  const [meta, setMeta] = useState<{ updated_at?: string | null; updated_by?: string | null }>({});
  const [frameReady, setFrameReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const shown = draft ?? saved;

  const push = useCallback((data: CalendarData) => {
    frame.current?.contentWindow?.postMessage({ type: 'calendar-data', data }, '*');
  }, []);

  // Load content from the API (fall back to the bundled default on failure).
  useEffect(() => {
    contentApi.get<CalendarData>(CONTENT_KEY)
      .then((res) => { setSaved(res.data); setCanEdit(res.can_edit); setMeta({ updated_at: res.updated_at, updated_by: res.updated_by }); })
      .catch(() => { /* keep the bundled default */ });
  }, []);

  // The iframe announces when its script is ready to receive data.
  useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      if (e.source === frame.current?.contentWindow && e.data?.type === 'calendar-ready') setFrameReady(true);
    };
    window.addEventListener('message', onMsg);
    return () => window.removeEventListener('message', onMsg);
  }, []);

  useEffect(() => { if (frameReady) push(shown); }, [frameReady, shown, push]);

  const startEdit = () => { setError(null); setDraft(structuredClone(saved)); };
  const cancelEdit = () => { setDraft(null); setError(null); };
  const save = async () => {
    if (!draft) return;
    setSaving(true); setError(null);
    try {
      const res = await contentApi.update<CalendarData>(CONTENT_KEY, draft);
      setSaved(res.data); setMeta({ updated_at: res.updated_at, updated_by: res.updated_by }); setDraft(null);
    } catch (e) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Could not save. Check your connection and try again.');
    } finally { setSaving(false); }
  };
  const resetToDefault = async () => {
    setSaving(true); setError(null);
    try {
      const res = await contentApi.reset<CalendarData>(CONTENT_KEY);
      setSaved(res.data); setMeta({}); setDraft(null);
    } catch { setError('Could not reset.'); } finally { setSaving(false); }
  };

  const editing = draft !== null;
  const updatedLine = meta.updated_at
    ? `Last edited ${new Date(meta.updated_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}${meta.updated_by ? ` by ${meta.updated_by.split('@')[0]}` : ''}`
    : 'Showing the default calendar';

  return (
    <div className="min-h-screen bg-black flex flex-col">
      <Header />

      {canEdit && (
        <div className="border-b border-gray-800 bg-gray-900/60">
          <div className="max-w-[1400px] mx-auto px-4 py-2 flex flex-wrap items-center gap-3">
            <span className="text-xs text-gray-400">{updatedLine}</span>
            <div className="flex-1" />
            {error && <span className="text-xs text-red-400">{error}</span>}
            {editing ? (
              <>
                <Button size="sm" variant="plain" onClick={cancelEdit} disabled={saving}><X className="w-4 h-4 mr-1" /> Discard</Button>
                <Button size="sm" variant="filled" onClick={save} isLoading={saving}>Save and publish</Button>
              </>
            ) : (
              <>
                {meta.updated_at && (
                  <Button size="sm" variant="plain" onClick={resetToDefault} disabled={saving} title="Drop all edits and go back to the version shipped with the site"><RotateCcw className="w-4 h-4 mr-1" /> Reset to default</Button>
                )}
                <Button size="sm" variant="outline" onClick={startEdit}><Pencil className="w-4 h-4 mr-1" /> Edit calendar</Button>
              </>
            )}
          </div>
        </div>
      )}

      <div className="flex-1 flex min-h-0">
        <iframe
          ref={frame}
          title="2027 Marketing Calendar"
          srcDoc={calendarHtml}
          sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"
          className="flex-1 w-full border-0 min-w-0"
          style={{ minHeight: 'calc(100vh - 4rem)' }}
        />
        {editing && draft && (
          <aside className="w-[380px] flex-none border-l border-gray-800 bg-gray-950 flex flex-col" style={{ height: 'calc(100vh - 4rem)', position: 'sticky', top: '4rem' }}>
            <div className="px-3 pt-3 text-xs text-gray-500">Changes preview live on the left. Nothing is published until you save.</div>
            <CalendarEditor data={draft} onChange={setDraft} />
          </aside>
        )}
      </div>
    </div>
  );
}
