import type { InputHTMLAttributes } from 'react'

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  /** Optional label rendered above the input */
  label?: string
}

export default function RetroInput({ label, className = '', ...rest }: Props) {
  return (
    <div className="flex flex-col gap-[2px]">
      {label && (
        <label className="text-retro-xs font-retro font-medium text-retro-black">
          {label}
        </label>
      )}
      <input
        className={`
          px-2 py-[3px]
          text-retro-sm font-retro
          bg-retro-white text-retro-black
          border border-retro-black
          shadow-retro-well
          placeholder:text-retro-darkgray
          ${className}
        `}
        {...rest}
      />
    </div>
  )
}
