import * as React from 'react'
import { cn } from '@/shared/lib/utils'

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        'flex h-9 w-full rounded-md border border-border bg-surface px-3 py-2',
        'text-sm text-text-primary placeholder:text-text-tertiary',
        'transition-colors duration-150',
        'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent/60',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'file:border-0 file:bg-transparent file:text-sm file:font-medium',
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
)
Input.displayName = 'Input'

export { Input }
