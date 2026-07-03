// Backend timestamps are naive UTC without a zone marker — parse as UTC,
// otherwise new Date() treats them as local time and dates drift by the offset
export function parseUtcDate(iso: string): Date {
  return new Date(/Z$|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z')
}

// Resolve a stored media reference to a usable src. Handles two forms:
//  - full S3/CDN URL (object storage enabled) → used as-is
//  - local volume path (/storage/…) → served via the /backend proxy
export function mediaSrc(fileUrl?: string | null): string {
  if (!fileUrl) return ''
  if (/^https?:\/\//i.test(fileUrl)) return fileUrl
  return `/backend${fileUrl}`
}

export function truncateText(value: string, max: number): string {
  return value.length > max ? value.slice(0, max) + '…' : value
}
