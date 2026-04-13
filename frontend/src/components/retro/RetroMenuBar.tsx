import type { ReactNode } from 'react'

export interface MenuItem {
  label: string
  onClick?: () => void
  disabled?: boolean
}

interface Props {
  /** Left-aligned items (logo, menus) */
  items?: MenuItem[]
  /** Right-aligned content (search, status) */
  right?: ReactNode
  /** Extra CSS classes */
  className?: string
}

export default function RetroMenuBar({ items = [], right, className = '' }: Props) {
  return (
    <nav
      aria-label="Menu principal"
      className={`
        flex items-center
        bg-retro-gray
        border-b-retro border-retro-black
        shadow-retro-outset
        px-1 py-[2px]
        select-none shrink-0
        ${className}
      `}
    >
      {items.map((item) => (
        <button
          type="button"
          key={item.label}
          onClick={item.onClick}
          disabled={item.disabled}
          className={`
            px-3 py-[2px]
            text-retro-sm font-retro font-medium
            ${item.disabled
              ? 'text-retro-darkgray cursor-not-allowed'
              : 'text-retro-black hover:bg-retro-black hover:text-retro-white cursor-pointer'
            }
          `}
        >
          {item.label}
        </button>
      ))}
      {right && (
        <div className="ml-auto flex items-center gap-1">
          {right}
        </div>
      )}
    </nav>
  )
}
