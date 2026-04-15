import { useId, type TextareaHTMLAttributes } from 'react'

interface Props extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Optional label rendered above the textarea */
  label?: string
}

export default function RetroTextarea({ label, className = '', ...rest }: Props) {
  const id = useId()
  return (
    <div className="flex flex-col gap-[2px]">
      {label && (
        <label htmlFor={id} className="text-retro-xs font-retro font-medium text-retro-black">
          {label}
        </label>
      )}
      <textarea
        id={id}
        className={`
          px-2 py-[3px]
          text-retro-sm font-retro
          bg-retro-white text-retro-black
          border border-retro-black
          shadow-retro-well
          placeholder:text-retro-darkgray
          retro-scroll
          resize-y
          ${className}
        `}
        {...rest}
      />
    </div>
  )
}
