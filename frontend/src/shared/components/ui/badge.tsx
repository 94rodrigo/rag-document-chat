import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/shared/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded px-2 py-0.5 text-[11px] font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-accent/15 text-accent border border-accent/25',
        secondary: 'bg-elevated text-text-secondary border border-border',
        destructive: 'bg-destructive/15 text-destructive border border-destructive/25',
        outline: 'border border-border text-text-secondary',
        success: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25',
        warning: 'bg-amber-500/15 text-amber-400 border border-amber-500/25',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
