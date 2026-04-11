/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      /* ── Retro palette ─────────────────────────────────────────── */
      colors: {
        retro: {
          white:    '#ffffff',
          light:    '#dfdfdf',
          gray:     '#c0c0c0',
          darkgray: '#808080',
          black:    '#000000',
          /* Accent for selected / active items */
          select:   '#000080',
          'select-text': '#ffffff',
        },
      },

      /* ── Retro fonts ───────────────────────────────────────────── */
      fontFamily: {
        retro:  ['"IBM Plex Mono"', '"Courier New"', 'Courier', 'monospace'],
        mono:   ['"IBM Plex Mono"', '"Courier New"', 'Courier', 'monospace'],
      },

      /* ── Hard drop shadows (no blur) ───────────────────────────── */
      boxShadow: {
        'retro':       '2px 2px 0px 0px #000000',
        'retro-lg':    '3px 3px 0px 0px #000000',
        /* Outset bevel (button at rest) */
        'retro-outset': 'inset -1px -1px 0 #808080, inset 1px 1px 0 #ffffff',
        /* Inset bevel (button pressed) */
        'retro-inset':  'inset 1px 1px 0 #808080, inset -1px -1px 0 #ffffff',
        /* Window inner area */
        'retro-well':   'inset 1px 1px 0 #808080, inset -1px -1px 0 #dfdfdf',
      },

      /* ── Spacing / sizing tokens ───────────────────────────────── */
      borderWidth: {
        'retro': '2px',
      },

      fontSize: {
        'retro-xs':  ['11px', { lineHeight: '16px' }],
        'retro-sm':  ['12px', { lineHeight: '18px' }],
        'retro-base': ['13px', { lineHeight: '20px' }],
        'retro-lg':  ['15px', { lineHeight: '22px' }],
        'retro-xl':  ['18px', { lineHeight: '26px' }],
        'retro-2xl': ['22px', { lineHeight: '30px' }],
      },
    },
  },
  plugins: [],
}
