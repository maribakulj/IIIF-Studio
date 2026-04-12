import { RetroButton } from './retro'

interface AdminNavProps {
  onClick: () => void
}

export default function AdminNav({ onClick }: AdminNavProps) {
  return (
    <RetroButton size="sm" onClick={onClick}>
      Admin
    </RetroButton>
  )
}
