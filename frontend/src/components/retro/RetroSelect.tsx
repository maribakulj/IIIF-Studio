import { useId, type SelectHTMLAttributes } from 'react'

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  /** Optional label rendered above the select */
  label?: string
  /** Options: array of {value, label} */
  options: { value: string; label: string }[]
}

export default function RetroSelect({ label, options, className = '', ...rest }: Props) {
  const generatedId = useId()
  const selectId = rest.id ?? generatedId

  return (
    <div className="flex flex-col gap-[2px]">
      {label && (
        <label htmlFor={selectId} className="text-retro-xs font-retro font-medium text-retro-black">
          {label}
        </label>
      )}
      <select
        id={selectId}
        className={`
          px-2 py-[3px]
          text-retro-sm font-retro
          bg-retro-white text-retro-black
          border border-retro-black
          shadow-retro-well
          cursor-pointer
          ${className}
        `}
        {...rest}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}
