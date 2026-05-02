import { forwardRef } from 'react';
import type { HTMLAttributes } from 'react';
import { clsx } from 'clsx';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  // HIG-flavored card variants:
  //   default  — opaque elevated surface, hairline border, layered shadow + inner top highlight
  //   hover    — same as default but interactive (cursor + lift on hover)
  //   material — translucent surface with backdrop-blur (HIG "regular material")
  //   raised   — sits one tier higher than default (use inside elevated containers)
  variant?: 'default' | 'hover' | 'material' | 'raised';
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', children, ...props }, ref) => {
    const base =
      'rounded-hig-lg border shadow-hig-2 ' +
      // Inner top highlight — subtle "lit from above" feel
      'shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]';

    const variantStyles: Record<NonNullable<CardProps['variant']>, string> = {
      default:
        'bg-surface-elevated border-separator',
      hover:
        'bg-surface-elevated border-separator cursor-pointer ' +
        'transition-[transform,box-shadow,border-color] duration-200 ease-hig ' +
        'hover:border-separator-opaque hover:shadow-hig-3 hover:-translate-y-0.5',
      material:
        // HIG-style translucent material; degrades gracefully without backdrop-filter
        'bg-surface-elevated/70 border-white/10 backdrop-blur-material-regular',
      raised:
        'bg-surface-raised border-separator',
    };

    return (
      <div ref={ref} className={clsx(base, variantStyles[variant], className)} {...props}>
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

export const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={clsx('p-6 pb-0', className)} {...props} />
  )
);

CardHeader.displayName = 'CardHeader';

export const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={clsx('p-6', className)} {...props} />
  )
);

CardContent.displayName = 'CardContent';

export const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={clsx('p-6 pt-0', className)} {...props} />
  )
);

CardFooter.displayName = 'CardFooter';
