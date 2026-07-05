const CACHE = 'mc-shell-v2'

self.addEventListener('install', e => { self.skipWaiting() })

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url)
  if (url.pathname.startsWith('/api')) return

  // Navigation (index.html): network-first so new deploys are picked up immediately;
  // fall back to cache when offline.
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then(res => { caches.open(CACHE).then(c => c.put(e.request, res.clone())); return res })
        .catch(() => caches.match(e.request).then(hit => hit || caches.match('/')))
    )
    return
  }

  // Static assets have hashed filenames per build, so cache-first is safe.
  e.respondWith(
    caches.open(CACHE).then(cache =>
      cache.match(e.request).then(hit =>
        hit || fetch(e.request).then(res => { cache.put(e.request, res.clone()); return res }).catch(() => hit)))
  )
})
