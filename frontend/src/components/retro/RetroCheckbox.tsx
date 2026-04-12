interface Props {
  /** Label text next to the checkbox */
  label: string
  /** Controlled checked state */
  checked: boolean
  /** Change handler */
  onChange: (checked: boolean) => void
  /** Disabled state */
  disabled?: boolean
  /** Extra CSS classes on the wrapper */
  className?: string
}

export default function RetroCheckbox({
  label,
  checked,
  onChange,
  disabled = false,
  className = '',
}: Props) {
  return (
    <label
      onClick={() => { if (!disabled) onChange(!checked) }}
      className={`
        inline-flex items-center gap-[6px]
        text-retro-sm font-retro
        ${disabled ? 'text-retro-darkgray cursor-not-allowed' : 'cursor-pointer'}
        select-none
        ${className}
      `}
    >
      <span
        className={`
          inline-flex items-center justify-center
          w-[13px] h-[13px]
          border border-retro-black
          bg-retro-white
          shadow-retro-well
          text-[10px] leading-none font-bold
          shrink-0
        `}
      >
        {checked && <span className="text-retro-black">x</span>}
      </span>
      {label}
    </label>
  )
}
