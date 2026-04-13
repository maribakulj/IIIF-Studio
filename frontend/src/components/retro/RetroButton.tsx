import type { ReactNode, ButtonHTMLAttributes } from 'react'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode
  /** Render as a small compact button */
  size?: 'sm' | 'md'
  /** If true, renders in "pressed" state */
  pressed?: boolean
}

export default function RetroButton({
  children,
  size = 'md',
  pressed = false,
  className = '',
  disabled,
  type = 'button',
  ...rest
}: Props) {
  const padding = size === 'sm' ? 'px-2 py-[1px]' : 'px-3 py-[3px]'
  const fontSize = size === 'sm' ? 'text-retro-xs' : 'text-retro-sm'

  return (
    <button
      type={type}
      className={`
        ${padding} ${fontSize}
        font-retro font-medium
        bg-retro-gray
        border border-retro-black
        ${pressed
          ? 'shadow-retro-inset'
          : 'shadow-retro-outset active:shadow-retro-inset'
        }
        ${disabled
          ? 'text-retro-darkgray cursor-not-allowed'
          : 'text-retro-black hover:bg-retro-light cursor-pointer'
        }
        select-none
        ${className}
      `}
      disabled={disabled}
      {...rest}
    >
      {children}
    </button>
  )
}
