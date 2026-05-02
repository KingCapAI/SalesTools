import { forwardRef } from 'react';
import type { InputHTMLAttributes } from 'react';
import { clsx } from 'clsx';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label htmlFor={id} className="block text-sm font-medium text-gray-300 mb-1">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          className={clsx(
            // HIG fill style: low-opacity system fill, hairline border that strengthens on focus
            'w-full px-3 py-2 rounded-hig-md text-gray-100 placeholder-gray-500',
            'bg-fill-tertiary border',
            'transition-[background-color,border-color,box-shadow] duration-150 ease-hig',
            'focus:outline-none focus:bg-fill-secondary focus:ring-2 focus:ring-primary-500/60 focus:border-primary-500/60',
            error ? 'border-red-500/70' : 'border-separator',
            className
          )}
          {...props}
        />
        {error && <p className="mt-1 text-sm text-red-400">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
