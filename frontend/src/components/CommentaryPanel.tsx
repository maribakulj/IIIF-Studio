import { useState, type FC } from 'react'
import type { Commentary, EditorialInfo } from '../lib/api.ts'
import { STATUS_LABELS, STATUS_VARIANTS } from '../lib/editorial.ts'
import { RetroBadge, RetroButton } from './retro'

interface Props {
  commentary: Commentary | null
  editorial: EditorialInfo
  visiblePublic: boolean
  visibleScholarly: boolean
}

const CommentaryPanel: FC<Props> = ({ commentary, editorial, visiblePublic, visibleScholarly }) => {
  const [tab, setTab] = useState<'public' | 'scholarly'>('public')

  if (!visiblePublic && !visibleScholarly) return null

  const activeTab: 'public' | 'scholarly' =
    !visiblePublic && visibleScholarly ? 'scholarly' :
    !visibleScholarly && visiblePublic ? 'public' :
    tab

  const content = activeTab === 'public' ? commentary?.public : commentary?.scholarly
  const bothVisible = visiblePublic && visibleScholarly

  return (
    <div className="p-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-retro-xs font-bold">Commentaire</span>
        <RetroBadge variant={STATUS_VARIANTS[editorial.status]}>
          {STATUS_LABELS[editorial.status]}
        </RetroBadge>
      </div>

      {bothVisible && (
        <div className="flex gap-[2px] mb-2">
          <RetroButton
            size="sm"
            pressed={activeTab === 'public'}
            onClick={() => setTab('public')}
          >
            Public
          </RetroButton>
          <RetroButton
            size="sm"
            pressed={activeTab === 'scholarly'}
            onClick={() => setTab('scholarly')}
          >
            Savant
          </RetroButton>
        </div>
      )}

      {content ? (
        <p className="text-retro-sm whitespace-pre-wrap font-retro leading-relaxed">
          {content}
        </p>
      ) : (
        <p className="text-retro-sm text-retro-darkgray">Commentaire non disponible.</p>
      )}
    </div>
  )
}

export default CommentaryPanel
