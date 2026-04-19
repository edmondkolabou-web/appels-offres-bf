export function useFormatMontant() {
  function formatMontant(val) {
    if (!val) return null
    if (val >= 1_000_000_000) return `${(val/1_000_000_000).toFixed(1)} Mrd FCFA`
    if (val >= 1_000_000)     return `${(val/1_000_000).toFixed(0)} M FCFA`
    if (val >= 1_000)         return `${(val/1_000).toFixed(0)} K FCFA`
    return `${val.toLocaleString('fr-FR')} FCFA`
  }
  return { formatMontant }
}
