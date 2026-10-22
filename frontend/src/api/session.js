// Protected API readers/writers share one session-expiry notification.
export async function sessionFetch(path, options) {
  const response = await fetch(path, options)
  if (response.status === 401 && !path.startsWith('/api/auth/')) {
    globalThis.dispatchEvent?.(new Event('runtu-session-expired'))
  }
  return response
}
