import { useEffect, useRef, useState, useCallback } from 'react';
import { Header } from '../components/layout/Header';
import './PMSMatcher.css';

/* ============== types ============== */
type RGB = [number, number, number];
type Lab = [number, number, number];
type PMSEntry = { code: string; hex: string; lab: Lab };
type Thread = { code: string; name: string };
type ThreadDict = Record<string, Thread[]>;     // pmsCode -> threads
type ThreadsByBrand = Record<string, ThreadDict>;

interface BrandIndexEntry { pmsCode: string; hex: string; lab: Lab; threads: Thread[]; }
type BrandIndex = Record<string, BrandIndexEntry[]>;

interface Pick { id: number; rgb: RGB; lab: Lab; xPct: number; yPct: number; }

interface ExactMatch { type: 'exact'; pmsCode: string; hex: string; threads: Thread[]; de: 0; }
interface ApproxMatch { type: 'approx'; pmsCode: string; hex: string; threads: Thread[]; de: number; }
interface EmptyMatch { type: 'empty'; }
type BrandMatchResult = ExactMatch | ApproxMatch | EmptyMatch;

const BRAND_LABELS: Record<string, string> = {
  'robison-anton': 'Robison-Anton',
  'marathon': 'Marathon',
  'fibres': 'Fibres',
};
const BRAND_KEYS = Object.keys(BRAND_LABELS) as Array<keyof typeof BRAND_LABELS>;

/* ============== color science ============== */
function hexToRgb(h: string): RGB {
  const s = h.replace('#', '');
  if (s.length === 3) {
    return s.split('').map(c => parseInt(c + c, 16)) as RGB;
  }
  return [parseInt(s.slice(0, 2), 16), parseInt(s.slice(2, 4), 16), parseInt(s.slice(4, 6), 16)];
}
function rgbToHex(r: number, g: number, b: number): string {
  const c = (v: number) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0');
  return '#' + c(r) + c(g) + c(b);
}
function srgbToLinear(c: number) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
function rgbToXyz(r: number, g: number, b: number): [number, number, number] {
  const lr = srgbToLinear(r), lg = srgbToLinear(g), lb = srgbToLinear(b);
  return [
    lr * 0.4124564 + lg * 0.3575761 + lb * 0.1804375,
    lr * 0.2126729 + lg * 0.7151522 + lb * 0.0721750,
    lr * 0.0193339 + lg * 0.1191920 + lb * 0.9503041,
  ];
}
function xyzToLab(x: number, y: number, z: number): Lab {
  x /= 0.95047; y /= 1; z /= 1.08883;
  const f = (t: number) => t > 0.008856 ? Math.cbrt(t) : (7.787 * t + 16 / 116);
  const fx = f(x), fy = f(y), fz = f(z);
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}
function rgbToLab(r: number, g: number, b: number): Lab {
  const [x, y, z] = rgbToXyz(r, g, b);
  return xyzToLab(x, y, z);
}
function deltaE(a: Lab, b: Lab) { return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]); }
function classifyDeltaE(de: number): 'good' | 'mid' | 'poor' {
  if (de <= 3) return 'good';
  if (de <= 7) return 'mid';
  return 'poor';
}
function luminance(r: number, g: number, b: number) {
  const L = (a: number) => { a /= 255; return a <= 0.03928 ? a / 12.92 : Math.pow((a + 0.055) / 1.055, 2.4); };
  return 0.2126 * L(r) + 0.7152 * L(g) + 0.0722 * L(b);
}

/* ============== component ============== */
export function PMSMatcher() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null);
  const frameRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const dropZoneRef = useRef<HTMLDivElement | null>(null);
  const idCounter = useRef(1);

  const pmsRef = useRef<PMSEntry[]>([]);
  const threadsRef = useRef<ThreadsByBrand>({});
  const brandIndexRef = useRef<BrandIndex>({});

  const [dataLoaded, setDataLoaded] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);
  // We keep the loaded HTMLImageElement in state so that a useEffect can draw
  // it to the React-rendered <canvas> AFTER it mounts. Drawing to a canvas
  // inside the file-load callback races React's render of .canvas-frame and
  // leaves the canvas orphaned (which is why nothing showed up before).
  const [loadedImage, setLoadedImage] = useState<HTMLImageElement | null>(null);
  const [picks, setPicks] = useState<Pick[]>([]);
  const [brands, setBrands] = useState<Record<string, boolean>>({
    'robison-anton': true, 'marathon': true, 'fibres': true,
  });
  const [cursorHex, setCursorHex] = useState('—');
  const [cursorRgb, setCursorRgb] = useState<RGB>([255, 255, 255]);
  const [imgDims, setImgDims] = useState<{ w: number; h: number } | null>(null);
  const [isDraggingFile, setIsDraggingFile] = useState(false);

  /* ========== data loading ========== */
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [pmsRaw, ra, marathon, fibres] = await Promise.all([
          fetch('/data/pms-matcher/pms.json').then(r => r.json()),
          fetch('/data/pms-matcher/robison-anton.json').then(r => r.json()),
          fetch('/data/pms-matcher/marathon.json').then(r => r.json()),
          fetch('/data/pms-matcher/fibres.json').then(r => r.json()),
        ]);
        if (cancelled) return;
        const pms: PMSEntry[] = pmsRaw.map((p: { code: string; hex: string }) => ({
          ...p, lab: rgbToLab(...hexToRgb(p.hex)),
        }));
        const threads: ThreadsByBrand = { 'robison-anton': ra, 'marathon': marathon, 'fibres': fibres };
        const byCode = new Map(pms.map(p => [p.code, p]));
        const brandIndex: BrandIndex = {};
        for (const brand of BRAND_KEYS) {
          const dict = threads[brand] || {};
          const idx: BrandIndexEntry[] = [];
          for (const code of Object.keys(dict)) {
            const p = byCode.get(code);
            if (!p) continue;
            idx.push({ pmsCode: code, hex: p.hex, lab: p.lab, threads: dict[code] });
          }
          brandIndex[brand] = idx;
        }
        pmsRef.current = pms;
        threadsRef.current = threads;
        brandIndexRef.current = brandIndex;
        setDataLoaded(true);
      } catch (err) {
        console.error('PMSMatcher: failed to load reference data', err);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  /* ========== matching helpers ========== */
  const nearestPMS = useCallback((lab: Lab, n = 1) => {
    const list = pmsRef.current.map(p => ({ ...p, de: deltaE(lab, p.lab) }));
    list.sort((a, b) => a.de - b.de);
    return list.slice(0, n);
  }, []);

  const brandMatch = useCallback((brand: string, lab: Lab, primaryPmsCode: string): BrandMatchResult => {
    const dict = threadsRef.current[brand] || {};
    if (dict[primaryPmsCode]) {
      const byCode = pmsRef.current.find(p => p.code === primaryPmsCode);
      return { type: 'exact', pmsCode: primaryPmsCode, hex: byCode?.hex || '#000', threads: dict[primaryPmsCode], de: 0 };
    }
    const idx = brandIndexRef.current[brand];
    if (!idx || idx.length === 0) return { type: 'empty' };
    let best: BrandIndexEntry | null = null;
    let bd = Infinity;
    for (const e of idx) {
      const d = deltaE(lab, e.lab);
      if (d < bd) { bd = d; best = e; }
    }
    if (!best) return { type: 'empty' };
    return { type: 'approx', pmsCode: best.pmsCode, hex: best.hex, threads: best.threads, de: bd };
  }, []);

  /* ========== file / canvas ========== */
  // Decode the file into an HTMLImageElement and stash it in state. The actual
  // canvas draw happens in the useEffect below — this is what fixes the bug
  // where the uploaded logo never appeared.
  const loadImage = useCallback((file: File) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      setLoadedImage(img);
      setImageLoaded(true);
      setPicks([]);
    };
    img.src = url;
  }, []);

  // Draw the loaded image to the React-rendered <canvas> after it mounts.
  useEffect(() => {
    if (!loadedImage) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const maxW = 900;
    const scale = Math.min(1, maxW / loadedImage.naturalWidth);
    canvas.width = Math.round(loadedImage.naturalWidth * scale);
    canvas.height = Math.round(loadedImage.naturalHeight * scale);
    const ctx = canvas.getContext('2d', { willReadFrequently: true })!;
    ctx.drawImage(loadedImage, 0, 0, canvas.width, canvas.height);
    ctxRef.current = ctx;
    setImgDims({ w: loadedImage.naturalWidth, h: loadedImage.naturalHeight });
  }, [loadedImage]);

  // React handlers for canvas interaction (replaces imperative addEventListener).
  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    const ctx = ctxRef.current;
    if (!canvas || !ctx) return;
    const rect = canvas.getBoundingClientRect();
    const x = Math.round((e.clientX - rect.left) * (canvas.width / rect.width));
    const y = Math.round((e.clientY - rect.top) * (canvas.height / rect.height));
    if (x < 0 || y < 0 || x >= canvas.width || y >= canvas.height) return;
    const sample = sampleAt(ctx, canvas, x, y);
    if (!sample) return;
    setPicks(p => [...p, {
      id: idCounter.current++,
      rgb: sample,
      lab: rgbToLab(...sample),
      xPct: x / canvas.width,
      yPct: y / canvas.height,
    }]);
  }, []);

  const handleCanvasMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    const ctx = ctxRef.current;
    if (!canvas || !ctx) return;
    const rect = canvas.getBoundingClientRect();
    const x = Math.round((e.clientX - rect.left) * (canvas.width / rect.width));
    const y = Math.round((e.clientY - rect.top) * (canvas.height / rect.height));
    if (x < 0 || y < 0 || x >= canvas.width || y >= canvas.height) return;
    const d = ctx.getImageData(x, y, 1, 1).data;
    setCursorHex(rgbToHex(d[0], d[1], d[2]).toUpperCase());
    setCursorRgb([d[0], d[1], d[2]]);
  }, []);

  const handleCanvasMouseLeave = useCallback(() => {
    setCursorHex('—');
    setCursorRgb([255, 255, 255]);
  }, []);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) loadImage(f);
  };
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingFile(false);
    const f = e.dataTransfer.files?.[0];
    if (f) loadImage(f);
  };

  const replaceImage = () => {
    setImageLoaded(false);
    setLoadedImage(null);
    setPicks([]);
    ctxRef.current = null;
    if (fileInputRef.current) fileInputRef.current.value = '';
  };
  const clearPicks = () => setPicks([]);

  const removePick = (id: number) => setPicks(ps => ps.filter(p => p.id !== id));

  /* ========== drag pin ========== */
  const onMarkerPointerDown = (id: number) => (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== undefined && e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();
    const el = e.currentTarget;
    const canvas = canvasRef.current;
    if (!canvas) return;
    el.setPointerCapture(e.pointerId);
    const cRect = canvas.getBoundingClientRect();
    const dragState = { sx: e.clientX, sy: e.clientY, cRect, moved: false };
    el.classList.add('dragging');

    const onMove = (ev: PointerEvent) => {
      const dx = ev.clientX - dragState.sx;
      const dy = ev.clientY - dragState.sy;
      if (Math.abs(dx) + Math.abs(dy) > 3) dragState.moved = true;
      const xIn = Math.max(0, Math.min(cRect.width, ev.clientX - cRect.left));
      const yIn = Math.max(0, Math.min(cRect.height, ev.clientY - cRect.top));
      el.style.left = xIn + 'px';
      el.style.top = yIn + 'px';
    };
    const finish = (ev: PointerEvent) => {
      el.classList.remove('dragging');
      el.removeEventListener('pointermove', onMove);
      el.removeEventListener('pointerup', finish);
      el.removeEventListener('pointercancel', finish);
      if (!dragState.moved) return;
      const xIn = Math.max(0, Math.min(cRect.width, ev.clientX - cRect.left));
      const yIn = Math.max(0, Math.min(cRect.height, ev.clientY - cRect.top));
      const cx = Math.round(xIn * canvas.width / cRect.width);
      const cy = Math.round(yIn * canvas.height / cRect.height);
      const ctx = ctxRef.current!;
      const sample = sampleAt(ctx, canvas, cx, cy);
      const cxC = Math.max(0, Math.min(canvas.width - 1, cx));
      const cyC = Math.max(0, Math.min(canvas.height - 1, cy));
      setPicks(ps => ps.map(p => p.id === id ? {
        ...p,
        xPct: cxC / canvas.width,
        yPct: cyC / canvas.height,
        rgb: sample ?? p.rgb,
        lab: sample ? rgbToLab(...sample) : p.lab,
      } : p));
    };
    el.addEventListener('pointermove', onMove);
    el.addEventListener('pointerup', finish);
    el.addEventListener('pointercancel', finish);
  };

  /* ========== render ========== */
  const canvas = canvasRef.current;

  return (
    <div className="pms-matcher min-h-screen">
      <Header />
      <div className="app-shell">
        {/* Toolbar */}
        <div className="toolbar">
          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <div style={{
              width: 22, height: 22, borderRadius: 6,
              background: 'linear-gradient(135deg, #1d1d1f 0%, #3a3a3c 100%)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white',
            }}>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1" />
                <circle cx="6" cy="6" r="2" fill="currentColor" />
              </svg>
            </div>
            <div className="title">PMS Matcher</div>
            <div className="subtitle">Color &amp; thread identification</div>
          </div>
          <div className="toolbar-actions">
            {imageLoaded && (
              <>
                <button className="pm-btn pm-btn-gray" onClick={replaceImage} aria-label="Replace image">
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                    <path d="M3 8a5 5 0 0 1 8.66-3.41M13 8a5 5 0 0 1-8.66 3.41" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    <path d="M11 3v3h-3M5 13v-3h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span className="lbl">Replace</span>
                </button>
                {picks.length > 0 && (
                  <button className="pm-btn pm-btn-gray" onClick={clearPicks} aria-label="Clear picks">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                      <path d="M4 5h8M5.5 5l.5 8h4l.5-8M6.5 3h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span className="lbl">Clear picks</span>
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Workspace */}
        <div className="workspace">
          {/* Canvas column */}
          <div className="canvas-col">
            {!imageLoaded && (
              <div
                ref={dropZoneRef}
                className={'empty-canvas' + (isDraggingFile ? ' dragging' : '')}
                onDragOver={e => { e.preventDefault(); setIsDraggingFile(true); }}
                onDragLeave={() => setIsDraggingFile(false)}
                onDrop={onDrop}
              >
                <div className="glyph">
                  <svg width="30" height="30" viewBox="0 0 30 30" fill="none">
                    <rect x="4" y="6" width="22" height="18" rx="2.5" stroke="currentColor" strokeWidth="1.6" />
                    <circle cx="11" cy="13" r="1.6" fill="currentColor" />
                    <path d="M5 22 L12 16 L17 20 L22 15 L26 18.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <div>
                  <h2>Drop a logo</h2>
                  <p>Or choose a file from your computer.</p>
                </div>
                <button className="pm-btn pm-btn-filled pm-btn-lg" onClick={() => fileInputRef.current?.click()}>
                  Choose file
                </button>
                <input ref={fileInputRef} type="file" accept="image/*" onChange={onFileChange} style={{ display: 'none' }} />
              </div>
            )}

            {imageLoaded && (
              <div className="canvas-card">
                <div ref={frameRef} className="canvas-frame">
                  <canvas
                    ref={canvasRef}
                    onClick={handleCanvasClick}
                    onMouseMove={handleCanvasMouseMove}
                    onMouseLeave={handleCanvasMouseLeave}
                  />
                  {picks.map((p, i) => (
                    <Marker
                      key={p.id}
                      pick={p}
                      index={i}
                      canvas={canvas}
                      onPointerDown={onMarkerPointerDown(p.id)}
                    />
                  ))}
                </div>
                <div className="canvas-meta">
                  <span className="pixel-readout">
                    <span className="swatch-dot" style={{ background: rgbToHex(...cursorRgb) }} />
                    <span className="pm-mono">{cursorHex}</span>
                  </span>
                  <span className="pm-mono">{imgDims ? `${imgDims.w} × ${imgDims.h}` : '—'}</span>
                </div>
              </div>
            )}
          </div>

          {/* Results column */}
          <div className="results-col">
            <div className="results-header">
              <h1 className="display">Picks<span className="results-count">{picks.length === 0 ? ' 0' : ` ${picks.length}`}</span></h1>
              <div className="seg">
                {BRAND_KEYS.map(b => (
                  <div
                    key={b}
                    className={'seg-item' + (brands[b] ? ' on' : '')}
                    onClick={() => setBrands(s => ({ ...s, [b]: !s[b] }))}
                  >
                    {b === 'robison-anton' ? 'R-A' : BRAND_LABELS[b]}
                  </div>
                ))}
              </div>
            </div>

            {picks.length === 0 ? (
              <div className="results-empty">
                <div className="glyph">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                    <path d="M12 4 L20 12 L13 12 L13 20 L12 20 L12 12 L4 12 Z" fill="currentColor" opacity="0.15" />
                    <path d="M12 3 V13 H4 L12 21" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                    <circle cx="17" cy="7" r="3" fill="currentColor" />
                  </svg>
                </div>
                <h3>{imageLoaded ? 'Click on the logo' : 'Drop a logo to start'}</h3>
                <p>{imageLoaded
                  ? 'Each click drops a numbered pin and shows its closest Pantone & thread codes here.'
                  : 'Once your logo is loaded, click any color region to identify it.'}</p>
              </div>
            ) : (
              <ol style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {dataLoaded && picks.map((c, i) => (
                  <PickCard
                    key={c.id}
                    pick={c}
                    index={i}
                    nearestPMS={nearestPMS}
                    brandMatch={brandMatch}
                    visibleBrands={brands}
                    onRemove={() => removePick(c.id)}
                  />
                ))}
              </ol>
            )}

            {picks.length > 0 && (
              <div className="results-footer">
                <div className="glyph">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
                    <circle cx="8" cy="5" r="0.9" fill="currentColor" />
                    <path d="M8 7.5 V11.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                </div>
                <div>
                  <strong style={{ color: 'var(--pm-label-2)', fontWeight: 600 }}>PMS values are public approximations.</strong>{' '}
                  Always confirm against a physical thread book before stitching a production piece.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============== sub-components ============== */

function sampleAt(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, cx: number, cy: number): RGB | null {
  const r0 = Math.max(0, cx - 2), r1 = Math.min(canvas.width, cx + 3);
  const c0 = Math.max(0, cy - 2), c1 = Math.min(canvas.height, cy + 3);
  const w = r1 - r0, h = c1 - c0;
  if (w <= 0 || h <= 0) return null;
  const d = ctx.getImageData(r0, c0, w, h).data;
  let R = 0, G = 0, B = 0, n = 0;
  for (let i = 0; i < d.length; i += 4) {
    if (d[i + 3] < 200) continue;
    R += d[i]; G += d[i + 1]; B += d[i + 2]; n++;
  }
  if (n === 0) return null;
  return [R / n, G / n, B / n];
}

interface MarkerProps {
  pick: Pick;
  index: number;
  canvas: HTMLCanvasElement | null;
  onPointerDown: (e: React.PointerEvent<HTMLDivElement>) => void;
}
function Marker({ pick, index, canvas, onPointerDown }: MarkerProps) {
  const cw = canvas?.clientWidth ?? 0;
  const ch = canvas?.clientHeight ?? 0;
  const lum = luminance(...pick.rgb);
  return (
    <div
      className={'pick-marker pop ' + (lum > 0.55 ? 'is-light' : 'is-dark')}
      style={{
        left: `${pick.xPct * cw}px`,
        top: `${pick.yPct * ch}px`,
        background: rgbToHex(...pick.rgb),
      }}
      onPointerDown={onPointerDown}
    >
      {String(index + 1).padStart(2, '0')}
    </div>
  );
}

interface PickCardProps {
  pick: Pick;
  index: number;
  nearestPMS: (lab: Lab, n?: number) => Array<PMSEntry & { de: number }>;
  brandMatch: (brand: string, lab: Lab, primaryPmsCode: string) => BrandMatchResult;
  visibleBrands: Record<string, boolean>;
  onRemove: () => void;
}
function PickCard({ pick, index, nearestPMS, brandMatch, visibleBrands, onRemove }: PickCardProps) {
  const top = nearestPMS(pick.lab, 3);
  if (top.length === 0) return null;
  const best = top[0];
  const lum = luminance(...pick.rgb);
  const klass = classifyDeltaE(best.de);

  return (
    <li className="pick-card">
      <div className="pick-head">
        <div
          className="pick-num"
          style={{
            background: rgbToHex(...pick.rgb),
            color: lum > 0.55 ? '#1d1d1f' : '#ffffff',
          }}
        >
          {String(index + 1).padStart(2, '0')}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
          <div className="compare">
            <div className="swatch" style={{ background: rgbToHex(...pick.rgb) }} />
            <div className="arrow">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                <path d="M2 5 H8 M5.5 2 L8 5 L5.5 8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="swatch" style={{ background: best.hex }} />
          </div>
          <div className="pms-block" style={{ minWidth: 0 }}>
            <div className="pms-code">{best.code}</div>
            <div className="pms-meta">
              <span className="pm-mono">{best.hex.toUpperCase()}</span>
              <span className={`de-pill de-${klass}`}>
                <span className="dot" />
                <span>ΔE {best.de.toFixed(1)}</span>
              </span>
            </div>
          </div>
        </div>
        <button className="pick-close" onClick={onRemove} aria-label="Remove">
          <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
            <path d="M3 3 L9 9 M9 3 L3 9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </button>
      </div>
      <div className="brands">
        {BRAND_KEYS.filter(b => visibleBrands[b]).map(brand => {
          const m = brandMatch(brand, pick.lab, best.code);
          return (
            <div key={brand} className="brand-row">
              <div className="brand-name">{BRAND_LABELS[brand]}</div>
              <div>
                {m.type === 'empty' ? (
                  <div className="brand-empty">Awaiting import</div>
                ) : (
                  <div className="brand-list">
                    {m.threads.map(t => (
                      <div key={t.code} className="brand-thread">
                        <div className="swatch-sm" style={{ background: m.hex }} />
                        <span className="code">{t.code}</span>
                        <span className="name">{t.name}</span>
                      </div>
                    ))}
                    {m.type === 'approx' && (
                      <div className="brand-via">
                        via <span className="pm-mono">{m.pmsCode}</span>{' '}
                        ·{' '}
                        <span className={`de-pill de-${classifyDeltaE(m.de)}`} style={{ padding: '0 6px 0 5px', fontSize: 11 }}>
                          <span className="dot" />
                          <span>ΔE {m.de.toFixed(1)}</span>
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </li>
  );
}
