import { useEffect, useState } from 'react'

/** Tracks OS-level prefers-color-scheme. No manual toggle in this demo (out of
 * spec scope) — charts follow the same automatic light/dark switch as the CSS. */
export function useIsDark(): boolean {
  const [isDark, setIsDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches)

  useEffect(() => {
    const mql = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e: MediaQueryListEvent) => setIsDark(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [])

  return isDark
}
