/**
 * PlayerPhoto — FPL official headshot with position-badge fallback.
 *
 * FPL photo URL: https://resources.premierleague.com/premierleague/photos/players/110x140/p{code}.png
 * Falls back to a position-coloured circle with initials if the image 404s
 * (common for newly promoted players or rookies).
 */

const POS_FALLBACK = {
  GK:  { bg: 'bg-yellow-500/20', text: 'text-yellow-300', border: 'border-yellow-500/40' },
  DEF: { bg: 'bg-blue-500/20',   text: 'text-blue-300',   border: 'border-blue-500/40'   },
  MID: { bg: 'bg-emerald-500/20',text: 'text-emerald-300',border: 'border-emerald-500/40'},
  FWD: { bg: 'bg-red-500/20',    text: 'text-red-300',    border: 'border-red-500/40'    },
}

/**
 * @param {number|null} code    - player.code (e.g. 223094)
 * @param {string}      name    - player.web_name (e.g. "Haaland")
 * @param {string}      pos     - position short name: GK / DEF / MID / FWD
 * @param {string}      size    - 'sm' | 'md' | 'lg' | 'xl'
 * @param {string}      className - extra tailwind classes on the wrapper
 */
export default function PlayerPhoto({ code, name, pos = 'MID', size = 'md', className = '' }) {
  const sizeMap = {
    sm: { wrapper: 'w-8 h-8',   text: 'text-[9px]'  },
    md: { wrapper: 'w-10 h-10', text: 'text-[11px]' },
    lg: { wrapper: 'w-14 h-14', text: 'text-sm'     },
    xl: { wrapper: 'w-20 h-20', text: 'text-base'   },
  }
  const { wrapper, text } = sizeMap[size] || sizeMap.md
  const fb = POS_FALLBACK[pos] || POS_FALLBACK.MID
  const initials = name ? name.slice(0, 2).toUpperCase() : pos

  if (!code) {
    return (
      <div className={`${wrapper} rounded-full ${fb.bg} border ${fb.border} flex items-center justify-center flex-shrink-0 ${className}`}>
        <span className={`${text} font-bold ${fb.text}`}>{initials}</span>
      </div>
    )
  }

  return (
    <div className={`${wrapper} rounded-full overflow-hidden flex-shrink-0 relative bg-[#0f172a] border border-white/10 ${className}`}>
      <img
        src={`https://resources.premierleague.com/premierleague/photos/players/110x140/p${code}.png`}
        alt={name}
        className="w-full h-full object-cover object-top"
        onError={e => {
          e.target.style.display = 'none'
          e.target.nextSibling.style.display = 'flex'
        }}
      />
      {/* Fallback — hidden until img errors */}
      <div
        className={`absolute inset-0 rounded-full ${fb.bg} border ${fb.border} items-center justify-center`}
        style={{ display: 'none' }}
      >
        <span className={`${text} font-bold ${fb.text}`}>{initials}</span>
      </div>
    </div>
  )
}

/**
 * PlayerPhotoCard — wider rectangular photo for pitch cards.
 * Shows the headshot cropped to fill a card-width rectangle.
 * Falls back to a coloured block with initials centred.
 */
export function PlayerPhotoCard({ code, name, pos = 'MID', height = 64, className = '' }) {
  const fb = POS_FALLBACK[pos] || POS_FALLBACK.MID

  if (!code) {
    return (
      <div
        className={`w-full flex items-center justify-center ${fb.bg} ${className}`}
        style={{ height }}
      >
        <span className={`text-sm font-bold ${fb.text}`}>{name?.slice(0, 3).toUpperCase() ?? pos}</span>
      </div>
    )
  }

  return (
    <div className={`w-full relative overflow-hidden ${className}`} style={{ height }}>
      <img
        src={`https://resources.premierleague.com/premierleague/photos/players/110x140/p${code}.png`}
        alt={name}
        className="w-full h-full object-cover object-top"
        onError={e => {
          e.target.style.display = 'none'
          e.target.nextSibling.style.display = 'flex'
        }}
      />
      {/* Fallback */}
      <div
        className={`absolute inset-0 items-center justify-center ${fb.bg}`}
        style={{ display: 'none' }}
      >
        <span className={`text-xs font-bold ${fb.text}`}>{name?.slice(0, 3).toUpperCase() ?? pos}</span>
      </div>
    </div>
  )
}
