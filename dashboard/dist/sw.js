const CACHE = 'mc-shell-v1'
self.addEventListener('install', e => { self.skipWaiting() })
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))))
})
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url)
  if (url.pathname.startsWith('/api')) return
  e.respondWith(
    caches.open(CACHE).then(cache =>
      cache.match(e.request).then(hit =>
        hit || fetch(e.request).then(res => { cache.put(e.request, res.clone()); return res })
          .catch(() => hit)))
  )
})
