/**
 * Schema-driven editor for the marketing calendar payload.
 * Each collection (quarters, campaigns, shows, tentpoles) is a list of records;
 * the schema below says which fields each record has and how to edit them.
 */
import { useState } from 'react';
import { Plus, Trash2, ChevronDown, ChevronRight, ArrowUp, ArrowDown } from 'lucide-react';
import { Button } from '../ui/Button';

type FieldType = 'text' | 'textarea' | 'date' | 'bool' | 'select';
interface Field {
  key: string;
  label: string;
  type: FieldType;
  options?: { value: string; label: string }[];
  hint?: string;
}
interface Collection {
  key: string;
  label: string;
  titleKey: string;
  fields: Field[];
  children?: { key: string; label: string; fields: Field[]; blank: Record<string, unknown> };
  blank: Record<string, unknown>;
}

const PHASE_TYPES = [
  { value: 'sellin', label: 'Sell-in' },
  { value: 'overseas', label: 'Overseas window' },
  { value: 'domestic', label: 'Domestic window' },
  { value: 'live', label: 'In market' },
];

const SCHEMA: Collection[] = [
  {
    key: 'quarters',
    label: 'Quarters',
    titleKey: 'name',
    fields: [
      { key: 'q', label: 'Quarter', type: 'text' },
      { key: 'name', label: 'Theme', type: 'text' },
      { key: 'goal', label: 'Communication goal', type: 'textarea' },
      { key: 'promo', label: 'Promotion', type: 'textarea' },
      { key: 'shows', label: 'Shows', type: 'text' },
    ],
    blank: { q: 'Q1', name: '', goal: '', promo: '', shows: '' },
  },
  {
    key: 'campaigns',
    label: 'Campaigns',
    titleKey: 'n',
    fields: [
      { key: 'n', label: 'Campaign', type: 'text' },
      { key: 'sub', label: 'Subtitle', type: 'text' },
      { key: 'briefAt', label: 'Creative brief date', type: 'date', hint: 'Diamond on the chart. Leave blank if it falls outside the year.' },
      { key: 'cut', label: 'Overseas cutoff', type: 'date', hint: 'Red marker. Leave blank for domestic-only campaigns.' },
      { key: 'hero', label: 'Hero product', type: 'textarea' },
      { key: 'offer', label: 'Offer', type: 'textarea' },
      { key: 'mat', label: 'Materials', type: 'textarea' },
      { key: 'need', label: 'Hats in hand by', type: 'text' },
      { key: 'brief', label: 'Brief (label)', type: 'text' },
      { key: 'flyer', label: 'Flyer and email (label)', type: 'text' },
      { key: 'dom', label: 'Domestic until (label)', type: 'text' },
    ],
    children: {
      key: 'phases',
      label: 'Bars',
      fields: [
        { key: 't', label: 'Type', type: 'select', options: PHASE_TYPES },
        { key: 's', label: 'Start', type: 'date' },
        { key: 'e', label: 'End', type: 'date' },
        { key: 'l', label: 'Label', type: 'text' },
      ],
      blank: { t: 'sellin', s: '2027-01-01', e: '2027-02-01', l: '' },
    },
    blank: { n: '', sub: '', briefAt: '', cut: '', phases: [], hero: '', offer: '', mat: '', need: '', brief: '', flyer: '', dom: '' },
  },
  {
    key: 'shows',
    label: 'Trade shows',
    titleKey: 'n',
    fields: [
      { key: 'n', label: 'Show', type: 'text' },
      { key: 's', label: 'Start', type: 'date' },
      { key: 'e', label: 'End', type: 'date' },
      { key: 'k', label: 'Tier', type: 'select', options: [{ value: 'nat', label: 'National' }, { value: 'reg', label: 'Regional or walk' }] },
      { key: 'tbd', label: 'Plan TBD', type: 'bool' },
      { key: 'city', label: 'City', type: 'text' },
      { key: 'who', label: 'Who attends', type: 'text' },
      { key: 'role', label: 'Campaign role', type: 'textarea' },
    ],
    blank: { n: '', s: '2027-01-01', e: '2027-01-01', k: 'reg', tbd: false, city: '', who: '', role: '' },
  },
  {
    key: 'tentpoles',
    label: 'Tentpoles',
    titleKey: 'n',
    fields: [
      { key: 'n', label: 'Moment', type: 'text' },
      { key: 's', label: 'Date', type: 'date' },
      { key: 'lo', label: 'Lower row', type: 'bool', hint: 'Use to stop neighbouring labels overlapping.' },
    ],
    blank: { n: '', s: '2027-01-01', lo: false },
  },
];

type Rec = Record<string, unknown>;
export type CalendarData = Record<string, unknown> & {
  intro?: string;
  footnote?: string;
  quarters?: Rec[];
  campaigns?: Rec[];
  shows?: Rec[];
  tentpoles?: Rec[];
};

const inputCls =
  'w-full bg-gray-900 border border-gray-700 rounded-md px-2.5 py-1.5 text-sm text-gray-100 focus:outline-none focus:border-amber-500';
const labelCls = 'block text-[11px] uppercase tracking-wider text-gray-500 mb-1';

function FieldInput({ field, value, onChange }: { field: Field; value: unknown; onChange: (v: unknown) => void }) {
  const id = `f-${field.key}-${Math.random().toString(36).slice(2, 7)}`;
  if (field.type === 'bool') {
    return (
      <label className="flex items-center gap-2 text-sm text-gray-300">
        <input type="checkbox" checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} className="accent-amber-500" />
        {field.label}
      </label>
    );
  }
  return (
    <div>
      <label htmlFor={id} className={labelCls}>{field.label}</label>
      {field.type === 'textarea' ? (
        <textarea id={id} rows={3} className={inputCls} value={String(value ?? '')} onChange={(e) => onChange(e.target.value)} />
      ) : field.type === 'select' ? (
        <select id={id} className={inputCls} value={String(value ?? '')} onChange={(e) => onChange(e.target.value)}>
          {field.options?.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      ) : (
        <input id={id} type={field.type === 'date' ? 'date' : 'text'} className={inputCls} value={String(value ?? '')} onChange={(e) => onChange(e.target.value)} />
      )}
      {field.hint && <p className="text-xs text-gray-500 mt-1">{field.hint}</p>}
    </div>
  );
}

function RecordEditor({
  col, rec, index, count, onChange, onDelete, onMove,
}: {
  col: Collection; rec: Rec; index: number; count: number;
  onChange: (r: Rec) => void; onDelete: () => void; onMove: (dir: -1 | 1) => void;
}) {
  const [open, setOpen] = useState(false);
  const title = String(rec[col.titleKey] || '') || `(untitled ${col.label.toLowerCase().replace(/s$/, '')})`;
  const children = col.children;
  const childRows = (children ? (rec[children.key] as Rec[] | undefined) : undefined) ?? [];

  return (
    <div className="border border-gray-800 rounded-lg bg-gray-900/40">
      <div className="flex items-center gap-2 px-3 py-2">
        <button type="button" onClick={() => setOpen(!open)} className="flex items-center gap-2 flex-1 text-left text-sm font-medium text-gray-100 min-w-0">
          {open ? <ChevronDown className="w-4 h-4 text-gray-500 flex-none" /> : <ChevronRight className="w-4 h-4 text-gray-500 flex-none" />}
          <span className="truncate">{title}</span>
        </button>
        <button type="button" aria-label="Move up" disabled={index === 0} onClick={() => onMove(-1)} className="p-1 text-gray-500 hover:text-gray-200 disabled:opacity-30"><ArrowUp className="w-4 h-4" /></button>
        <button type="button" aria-label="Move down" disabled={index === count - 1} onClick={() => onMove(1)} className="p-1 text-gray-500 hover:text-gray-200 disabled:opacity-30"><ArrowDown className="w-4 h-4" /></button>
        <button type="button" aria-label="Delete" onClick={onDelete} className="p-1 text-gray-500 hover:text-red-400"><Trash2 className="w-4 h-4" /></button>
      </div>
      {open && (
        <div className="px-3 pb-3 space-y-3 border-t border-gray-800 pt-3">
          {col.fields.map((f) => (
            <FieldInput key={f.key} field={f} value={rec[f.key]} onChange={(v) => onChange({ ...rec, [f.key]: v })} />
          ))}
          {children && (
            <div className="pt-2">
              <div className="flex items-center justify-between mb-2">
                <span className={labelCls}>{children.label}</span>
                <button type="button" onClick={() => onChange({ ...rec, [children.key]: [...childRows, { ...children.blank }] })} className="text-xs text-amber-400 hover:text-amber-300 inline-flex items-center gap-1"><Plus className="w-3 h-3" /> Add bar</button>
              </div>
              <div className="space-y-2">
                {childRows.map((row, ri) => (
                  <div key={ri} className="grid grid-cols-[1fr_1fr] gap-2 p-2 rounded-md bg-black/40 border border-gray-800">
                    {children.fields.map((f) => (
                      <div key={f.key} className={f.key === 'l' ? 'col-span-2' : ''}>
                        <FieldInput field={f} value={row[f.key]} onChange={(v) => {
                          const next = childRows.map((r, i) => (i === ri ? { ...r, [f.key]: v } : r));
                          onChange({ ...rec, [children.key]: next });
                        }} />
                      </div>
                    ))}
                    <div className="col-span-2 flex justify-end">
                      <button type="button" onClick={() => onChange({ ...rec, [children.key]: childRows.filter((_, i) => i !== ri) })} className="text-xs text-gray-500 hover:text-red-400 inline-flex items-center gap-1"><Trash2 className="w-3 h-3" /> Remove bar</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function CalendarEditor({ data, onChange }: { data: CalendarData; onChange: (d: CalendarData) => void }) {
  const [tab, setTab] = useState<string>('text');

  const setList = (key: string, rows: Rec[]) => onChange({ ...data, [key]: rows });

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex gap-1 px-3 pt-3 pb-2 border-b border-gray-800 overflow-x-auto">
        {[{ key: 'text', label: 'Page text' }, ...SCHEMA.map((c) => ({ key: c.key, label: c.label }))].map((t) => (
          <button key={t.key} type="button" onClick={() => setTab(t.key)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider whitespace-nowrap ${tab === t.key ? 'bg-amber-500 text-black' : 'text-gray-400 hover:text-gray-100'}`}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {tab === 'text' && (
          <div className="space-y-3">
            <FieldInput field={{ key: 'intro', label: 'Intro paragraph', type: 'textarea' }} value={data.intro} onChange={(v) => onChange({ ...data, intro: String(v) })} />
            <FieldInput field={{ key: 'footnote', label: 'Footnote', type: 'textarea' }} value={data.footnote} onChange={(v) => onChange({ ...data, footnote: String(v) })} />
          </div>
        )}
        {SCHEMA.filter((c) => c.key === tab).map((col) => {
          const rows = (data[col.key] as Rec[] | undefined) ?? [];
          return (
            <div key={col.key} className="space-y-2">
              {rows.map((rec, i) => (
                <RecordEditor key={i} col={col} rec={rec} index={i} count={rows.length}
                  onChange={(r) => setList(col.key, rows.map((x, j) => (j === i ? r : x)))}
                  onDelete={() => setList(col.key, rows.filter((_, j) => j !== i))}
                  onMove={(dir) => {
                    const j = i + dir; if (j < 0 || j >= rows.length) return;
                    const next = [...rows]; [next[i], next[j]] = [next[j], next[i]]; setList(col.key, next);
                  }} />
              ))}
              <Button type="button" variant="outline" size="sm" onClick={() => setList(col.key, [...rows, { ...col.blank }])}>
                <Plus className="w-4 h-4 mr-1" /> Add {col.label.toLowerCase().replace(/s$/, '')}
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
