import { useState, useEffect } from 'react'

// Cycles through status phrases while something is generating, so a long wait
// doesn't sit on one static line. Returns the current phrase; resets to the
// first one whenever `active` goes false.
export function useRotatingPhrase(phrases: string[], active: boolean, intervalMs = 2800): string {
  const [i, setI] = useState(0)
  useEffect(() => {
    if (!active || phrases.length <= 1) { setI(0); return }
    const id = setInterval(() => setI(p => (p + 1) % phrases.length), intervalMs)
    return () => clearInterval(id)
  }, [active, intervalMs, phrases.length])
  return phrases[Math.min(i, phrases.length - 1)] ?? ''
}
