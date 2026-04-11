import type { ReactNode } from 'react'

interface Props {
  /** Window title shown in the title bar */
  title: string
  /** Optional status text displayed in the bottom status bar */
  statusBar?: string
  /** Called when the close button is clicked (omit to hide the button) */
  onClose?: () => void
  /** Extra CSS classes for the outer container */
  className?: string
  /** Content rendered inside the window body */
  children: ReactNode
  /** If true, window body is scrollable with retro scrollbars */
  scrollable?: boolean
  /** If true, the window is rendered as "active" (darker title bar) */
  active?: boolean
}

export default function RetroWindow({
  title,
  statusBar,
  onClose,
  className = '',
  children,
  scrollable = false,
  active = true,
}: Props) {
  return (
    <div
      className={`
        flex flex-col
        border-retro border-retro-black bg-retro-gray
        shadow-retro
        ${className}
      `}
    >
      {/* ── Title bar ──────────────────────────────────────────── */}
      <div
        className={`
          flex items-center gap-2 px-2 py-[3px]
          select-none shrink-0
          ${active ? 'bg-retro-black text-retro-white' : 'bg-retro-darkgray text-retro-white'}
        `}
      >
        {onClose && (
          <button
            onClick={onClose}
            className="
              w-[14px] h-[14px] flex items-center justify-center
              border border-retro-white bg-retro-gray text-retro-black
              text-[9px] leading-none font-bold
              hover:bg-retro-white active:bg-retro-darkgray
            "
            aria-label="Fermer"
          >
            x
          </button>
        )}
        <span className="flex-1 text-retro-xs font-bold truncate tracking-wide">
          {title}
        </span>
      </div>

      {/* ── Content area ───────────────────────────────────────── */}
      <div
        className={`
          flex-1 bg-retro-white
          border-t-0
          m-[3px] mt-0
          shadow-retro-well
          ${scrollable ? 'overflow-auto retro-scroll' : 'overflow-hidden'}
        `}
      >
        {children}
      </div>

      {/* ── Status bar (optional) ──────────────────────────────── */}
      {statusBar !== undefined && (
        <div
          className="
            px-2 py-[2px]
            text-retro-xs text-retro-black
            border-t border-retro-darkgray
            bg-retro-gray
            shadow-retro-well
            mx-[3px] mb-[3px]
            truncate shrink-0
          "
        >
          {statusBar}
        </div>
      )}
    </div>
  )
}
