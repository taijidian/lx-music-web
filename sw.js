/* 洛雪音乐 Service Worker：只缓存应用外壳；API 与音频流一律直连网络 */
const CACHE = 'lxweb-shell-v1';
const SHELL = ['/', '/manifest.json', '/icons/icon-192.png', '/icons/icon-512.png', '/icons/icon-180.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;      // 平台 CDN 的封面/音频不拦截
  if (url.pathname.startsWith('/api/')) return;     // 业务 API 不缓存（链接会过期）
  if (e.request.mode === 'navigate') {
    // 页面：网络优先（保证拿到最新版），离线时回退到缓存外壳
    e.respondWith(
      fetch(e.request)
        .then(r => { const cp = r.clone(); caches.open(CACHE).then(c => c.put('/', cp)); return r; })
        .catch(() => caches.match('/'))
    );
    return;
  }
  // 其余同源静态资源：缓存优先
  e.respondWith(
    caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
      const cp = r.clone(); caches.open(CACHE).then(c => c.put(e.request, cp)); return r;
    }))
  );
});
