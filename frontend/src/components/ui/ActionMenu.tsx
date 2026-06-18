import { useState, useRef, useEffect } from 'react';
import { MoreHorizontal } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface ActionMenuItem {
  icon: LucideIcon;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
  hidden?: boolean;
}

interface ActionMenuProps {
  items: ActionMenuItem[];
}

export function ActionMenu({ items }: ActionMenuProps) {
  const [open, setOpen] = useState(false);
  // Pick the side dynamically when the menu opens so the dropdown never
  // hangs off-screen. Default 'right' matches the historical anchor.
  const [side, setSide] = useState<'left' | 'right'>('right');
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const handleToggle = () => {
    if (!open && buttonRef.current) {
      // Anchor on the side that gives the dropdown more room. A 192px-wide
      // menu wants ~200px of clearance; if the button is too close to the
      // left edge, flip the anchor to 'left' so it expands rightward.
      const rect = buttonRef.current.getBoundingClientRect();
      const spaceRight = window.innerWidth - rect.right;
      const spaceLeft = rect.left;
      setSide(spaceLeft < 200 && spaceRight > spaceLeft ? 'left' : 'right');
    }
    setOpen(!open);
  };

  const visibleItems = items.filter((i) => !i.hidden);

  return (
    <div className="relative" ref={menuRef}>
      <button
        ref={buttonRef}
        onClick={handleToggle}
        className="p-2 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 transition-colors"
        aria-label="More actions"
      >
        <MoreHorizontal className="w-5 h-5" />
      </button>

      {open && (
        <>
          {/* Backdrop captures outside taps on touch devices */}
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />

          <div
            className={
              `absolute ${side === 'right' ? 'right-0' : 'left-0'} mt-2 w-48 ` +
              `max-w-[calc(100vw-2rem)] max-h-[70vh] overflow-y-auto ` +
              `bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-40 py-1`
            }
          >
            {visibleItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.label}
                  onClick={() => {
                    if (!item.disabled && !item.loading) {
                      item.onClick();
                      setOpen(false);
                    }
                  }}
                  disabled={item.disabled || item.loading}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-300 hover:bg-gray-800 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {item.loading ? 'Loading...' : item.label}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
