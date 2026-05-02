import { forwardRef } from 'react';
import type { ButtonHTMLAttributes } from 'react';
import { clsx } from 'clsx';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  // HIG-flavored variants:
  //   filled   — solid accent fill (alias: primary)
  //   tinted   — translucent accent (HIG iOS button style)
  //   gray     — system-fill gray that blends into surface (alias: secondary)
  //   outline  — bordered, recedes
  //   plain    — text-only, no background (alias: ghost)
  //   danger   — destructive solid red
  variant?: 'filled' | 'primary' | 'tinted' | 'gray' | 'secondary' | 'outline' | 'plain' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'filled', size = 'md', isLoading, children, disabled, ...props }, ref) => {
    const baseStyles =
      // Layout, hit area, motion (transform + opacity only, per HIG motion guidance)
      'inline-flex items-center justify-center font-medium select-none ' +
      'rounded-hig-md ' +
      'transition-[transform,opacity,background-color,box-shadow] duration-150 ease-hig ' +
      'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-base ' +
      'disabled:opacity-40 disabled:cursor-not-allowed ' +
      'active:scale-[0.97] active:opacity-90';

    const variants: Record<NonNullable<ButtonProps['variant']>, string> = {
      filled:
        'bg-primary-600 text-white shadow-hig-1 hover:bg-primary-500 hover:shadow-hig-2',
      primary:
        'bg-primary-600 text-white shadow-hig-1 hover:bg-primary-500 hover:shadow-hig-2',
      tinted:
        'bg-primary-500/15 text-primary-300 hover:bg-primary-500/25 hover:text-primary-200',
      gray:
        'bg-fill-tertiary text-gray-100 hover:bg-fill-secondary',
      secondary:
        'bg-fill-tertiary text-gray-100 hover:bg-fill-secondary',
      outline:
        'border border-separator bg-fill-quaternary text-gray-100 hover:bg-fill-tertiary',
      plain:
        'text-gray-200 hover:bg-fill-quaternary',
      ghost:
        'text-gray-200 hover:bg-fill-quaternary',
      danger:
        'bg-red-600 text-white shadow-hig-1 hover:bg-red-500 hover:shadow-hig-2',
    };

    const sizes = {
      sm: 'px-3 py-1.5 text-sm gap-1.5',
      md: 'px-4 py-2 text-sm gap-2',
      lg: 'px-6 py-3 text-base gap-2',
    };

    return (
      <button
        ref={ref}
        className={clsx(baseStyles, variants[variant], sizes[size], className)}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? (
          <>
            <svg
              className="animate-spin -ml-1 mr-2 h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Loading...
          </>
        ) : (
          children
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
