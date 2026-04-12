import type { ReactNode } from 'react'

type Variant = 'default' | 'success' | 'warning' | 'error' | 'info'

interface Props {
  children: ReactNode
  variant?: Variant
  className?: string
}

const variantStyles: Record<Variant, string> = {
  default:  'bg-retro-gray text-retro-black',
  success:  'bg-retro-black text-retro-white',
  warning:  'bg-retro-white text-retro-black border-dashed',
  error:    'bg-retro-white text-retro-black font-bold',
  info:     'bg-retro-light text-retro-black',
}

export default function RetroBadge({
  children,
  variant = 'default',
  className = '',
}: Props) {
  return (
    <span
      className={`
        inline-block
        px-2 py-[1px]
        text-retro-xs font-retro
        border border-retro-black
        ${variantStyles[variant]}
        ${className}
      `}
    >
      {children}
    </span>
  )
}
