import { useState } from 'react'
import {
  RetroWindow,
  RetroButton,
  RetroMenuBar,
  RetroIcon,
  RetroCheckbox,
  RetroInput,
  RetroTextarea,
  RetroSelect,
  RetroBadge,
} from '../components/retro'

export default function RetroDemo({ onBack }: { onBack: () => void }) {
  const [checked1, setChecked1] = useState(true)
  const [checked2, setChecked2] = useState(false)
  const [selectedIcon, setSelectedIcon] = useState<string | null>(null)
  const [inputVal, setInputVal] = useState('')
  const [textareaVal, setTextareaVal] = useState('Explicit liber primus incipit secundus...')
  const [selectVal, setSelectVal] = useState('medieval-illuminated')

  return (
    <div className="min-h-screen bg-retro-dither">
      {/* ── Menu Bar ─────────────────────────────────────────── */}
      <RetroMenuBar
        items={[
          { label: 'IIIF Studio', onClick: onBack },
          { label: 'Fichier' },
          { label: 'Edition' },
          { label: 'Aide' },
          { label: 'Disabled', disabled: true },
        ]}
        right={
          <span className="text-retro-xs text-retro-darkgray px-2">
            Design System Demo
          </span>
        }
      />

      <div className="p-4 flex flex-col gap-4 max-w-4xl mx-auto">
        {/* ── Section: Buttons ──────────────────────────────── */}
        <RetroWindow title="RetroButton" statusBar="Boutons avec bevel 3D outset/inset">
          <div className="p-3 flex flex-wrap gap-2 items-center">
            <RetroButton>Normal</RetroButton>
            <RetroButton size="sm">Small</RetroButton>
            <RetroButton pressed>Pressed</RetroButton>
            <RetroButton disabled>Disabled</RetroButton>
            <RetroButton onClick={onBack}>Retour Accueil</RetroButton>
          </div>
        </RetroWindow>

        {/* ── Section: Window variants ─────────────────────── */}
        <div className="flex gap-4">
          <RetroWindow
            title="Fenetre active"
            onClose={() => {}}
            statusBar="Active window"
            className="flex-1"
            active
          >
            <div className="p-3 text-retro-sm">
              Contenu de la fenetre avec barre de titre noire.
              Le bouton [x] ferme la fenetre.
            </div>
          </RetroWindow>

          <RetroWindow
            title="Fenetre inactive"
            onClose={() => {}}
            statusBar="Inactive window"
            className="flex-1"
            active={false}
          >
            <div className="p-3 text-retro-sm">
              Une fenetre non focusee a une barre de titre grise.
            </div>
          </RetroWindow>
        </div>

        {/* ── Section: Scrollable window ───────────────────── */}
        <RetroWindow title="Scrollable Window" scrollable className="h-[150px]">
          <div className="p-3 text-retro-sm">
            {Array.from({ length: 20 }, (_, i) => (
              <p key={i}>Ligne {i + 1} — Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
            ))}
          </div>
        </RetroWindow>

        {/* ── Section: Icons ───────────────────────────────── */}
        <RetroWindow title="RetroIcon — Desktop Icons" statusBar="Cliquez pour selectionner">
          <div className="p-4 flex flex-wrap gap-2 bg-retro-dither-light">
            {[
              { glyph: '\u{1F4DC}', label: 'Beatus' },
              { glyph: '\u{1F4D6}', label: 'Cartulaire' },
              { glyph: '\u{1F4C4}', label: 'Charte' },
              { glyph: '\u{1F5BC}', label: 'Enluminures' },
              { glyph: '\u{1F4BE}', label: 'Export' },
              { glyph: '\u{2699}', label: 'Config' },
            ].map((icon) => (
              <RetroIcon
                key={icon.label}
                glyph={icon.glyph}
                label={icon.label}
                selected={selectedIcon === icon.label}
                onClick={() => setSelectedIcon(icon.label)}
              />
            ))}
          </div>
        </RetroWindow>

        {/* ── Section: Form controls ───────────────────────── */}
        <RetroWindow title="Form Controls" statusBar="Inputs, textareas, selects, checkboxes">
          <div className="p-3 flex flex-col gap-3">
            <div className="flex gap-4">
              <div className="flex-1">
                <RetroInput
                  label="Identifiant du corpus"
                  placeholder="ex: beatus-lat8878"
                  value={inputVal}
                  onChange={(e) => setInputVal(e.target.value)}
                />
              </div>
              <div className="flex-1">
                <RetroSelect
                  label="Profil de corpus"
                  value={selectVal}
                  onChange={(e) => setSelectVal(e.target.value)}
                  options={[
                    { value: 'medieval-illuminated', label: 'Medieval Illuminated' },
                    { value: 'medieval-textual', label: 'Medieval Textual' },
                    { value: 'early-modern-print', label: 'Early Modern Print' },
                    { value: 'modern-handwritten', label: 'Modern Handwritten' },
                  ]}
                />
              </div>
            </div>

            <RetroTextarea
              label="Transcription diplomatique"
              value={textareaVal}
              onChange={(e) => setTextareaVal(e.target.value)}
              rows={4}
            />

            <div className="flex gap-4">
              <RetroCheckbox
                label="OCR diplomatique"
                checked={checked1}
                onChange={setChecked1}
              />
              <RetroCheckbox
                label="Iconographie"
                checked={checked2}
                onChange={setChecked2}
              />
              <RetroCheckbox
                label="Disabled"
                checked={false}
                onChange={() => {}}
                disabled
              />
            </div>
          </div>
        </RetroWindow>

        {/* ── Section: Badges ──────────────────────────────── */}
        <RetroWindow title="RetroBadge — Status Indicators">
          <div className="p-3 flex flex-wrap gap-2 items-center">
            <RetroBadge>default</RetroBadge>
            <RetroBadge variant="success">validated</RetroBadge>
            <RetroBadge variant="warning">needs_review</RetroBadge>
            <RetroBadge variant="error">failed</RetroBadge>
            <RetroBadge variant="info">machine_draft</RetroBadge>
          </div>
        </RetroWindow>

        {/* ── Section: Typography ──────────────────────────── */}
        <RetroWindow title="Typography & Utilities">
          <div className="p-3 flex flex-col gap-2">
            <p className="text-retro-2xl font-bold">Heading 2XL — IIIF Studio</p>
            <p className="text-retro-xl font-bold">Heading XL — Beatus de Saint-Sever</p>
            <p className="text-retro-lg font-semibold">Heading LG — Folio 13r</p>
            <p className="text-retro-base">Body base — Explicit liber primus incipit secundus</p>
            <p className="text-retro-sm">Body SM — Metadata and labels</p>
            <p className="text-retro-xs text-retro-darkgray">Caption XS — Timestamps and fine print</p>
            <hr className="border-retro-darkgray" />
            <div className="flex gap-4">
              <div className="p-2 bg-retro-dither text-retro-xs">bg-retro-dither</div>
              <div className="p-2 bg-retro-dither-dark text-retro-xs text-retro-white">bg-retro-dither-dark</div>
              <div className="p-2 bg-retro-dither-light text-retro-xs">bg-retro-dither-light</div>
              <div className="p-2 bg-retro-lines text-retro-xs">bg-retro-lines</div>
            </div>
          </div>
        </RetroWindow>
      </div>
    </div>
  )
}
