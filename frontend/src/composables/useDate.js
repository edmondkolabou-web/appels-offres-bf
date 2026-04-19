export function useDate() {
  const MOIS = ['janv.','févr.','mars','avr.','mai','juin',
                'juil.','août','sept.','oct.','nov.','déc.']

  function formatDate(dateStr) {
    if (!dateStr) return '—'
    const d = new Date(dateStr)
    return `${d.getDate()} ${MOIS[d.getMonth()]} ${d.getFullYear()}`
  }

  function joursRestants(dateStr) {
    if (!dateStr) return null
    const delta = Math.floor((new Date(dateStr) - new Date()) / 86400000)
    return delta
  }

  function isUrgent(dateStr) {
    const j = joursRestants(dateStr)
    return j !== null && j >= 0 && j <= 3
  }

  function relativeTime(dateStr) {
    if (!dateStr) return ''
    const diff = Math.floor((Date.now() - new Date(dateStr)) / 60000)
    if (diff < 60) return `il y a ${diff} min`
    if (diff < 1440) return `il y a ${Math.floor(diff/60)}h`
    return formatDate(dateStr)
  }

  return { formatDate, joursRestants, isUrgent, relativeTime }
}
