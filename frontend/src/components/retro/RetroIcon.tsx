interface Props {
  /** Label displayed below the icon */
  label: string
  /** Emoji or text character used as the icon glyph */
  glyph: string
  /** Click handler */
  onClick?: () => void
  /** If true, renders in selected/highlighted state */
  selected?: boolean
  /** Extra CSS classes */
  className?: string
}

export default function RetroIcon({
  label,
  glyph,
  onClick,
  selected = false,
  className = '',
}: Props) {
  return (
    <button
      onClick={onClick}
      className={`
        flex flex-col items-center gap-1
        p-2 w-[80px]
        cursor-pointer select-none
        ${className}
      `}
      onDoubleClick={onClick}
    >
      {/* Icon box */}
      <div
        className={`
          w-[48px] h-[48px]
          flex items-center justify-center
          border border-retro-black
          text-[24px] leading-none
          ${selected
            ? 'bg-retro-black text-retro-white'
            : 'bg-retro-white text-retro-black hover:bg-retro-light'
          }
          shadow-retro-outset
        `}
      >
        {glyph}
      </div>
      {/* Label */}
      <span
        className={`
          text-retro-xs text-center leading-tight
          max-w-full break-words
          ${selected
            ? 'bg-retro-select text-retro-select-text px-1'
            : 'text-retro-black'
          }
        `}
      >
        {label}
      </span>
    </button>
  )
}
