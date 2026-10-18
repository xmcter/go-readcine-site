const CACHE_NAME = 'readcine-pwa-v3';
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/?source=pwa',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
  '/favicon.ico',
  '/favicon.png',
  '/apple-touch-icon.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // 对于第三方 API、外链检测和探针，不走缓存，直接网络请求
  if (url.origin !== location.origin) {
    return;
  }

  // 1. 针对页面导航请求 (HTML / 路由 / start_url 离线检测)
  // 保证离线或弱网下打开应用时绝对能返回有效 200 HTML 页面，满足 Chrome PWA 安装标准
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((networkRes) => {
          if (networkRes.ok) {
            const clone = networkRes.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          }
          return networkRes;
        })
        .catch(async () => {
          const cache = await caches.open(CACHE_NAME);
          const cached = await cache.match(req, { ignoreSearch: true });
          if (cached) return cached;
          const indexCached = (await cache.match('/index.html')) || (await cache.match('/'));
          return indexCached || new Response('Offline', { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
        })
    );
    return;
  }

  // 2. 对于 stats.json / headlines.json：采用 Stale-While-Revalidate 策略
  if (url.pathname.endsWith('.json')) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) => {
        return cache.match(req, { ignoreSearch: true }).then((cached) => {
          const fetchPromise = fetch(req).then((res) => {
            if (res.ok) {
              cache.put(req, res.clone());
            }
            return res;
          }).catch(() => cached);
          return cached || fetchPromise;
        });
      })
    );
    return;
  }

  // 3. 对于图标与静态外壳：采用 Stale-While-Revalidate 策略
  event.respondWith(
    caches.match(req, { ignoreSearch: true }).then((cached) => {
      const fetchPromise = fetch(req).then((res) => {
        if (res.ok) {
          const resClone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, resClone));
        }
        return res;
      }).catch(() => cached);
      return cached || fetchPromise;
    })
  );
});
