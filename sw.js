const CACHE_NAME = 'readcine-pwa-v4';
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
    caches.open(CACHE_NAME).then(async (cache) => {
      // 容错预缓存：即便个别图标网络抖动，也不阻断 SW 的成功激活
      await Promise.allSettled(
        PRECACHE_ASSETS.map((asset) =>
          cache.add(asset).catch((err) => {
            console.warn('Precache failed for asset:', asset, err);
          })
        )
      );
      return self.skipWaiting();
    })
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

  // 对于第三方 API、外链检测和跨域探针，不拦截，直接走网络
  if (url.origin !== location.origin) {
    return;
  }

  // 1. 针对页面导航请求 (HTML / 路由 / start_url)
  // 采用 Cache First + 后台静默刷新策略，保证国内网络/离线秒开，避免 Cloudflare 延迟导致“打不开”
  if (req.mode === 'navigate') {
    event.respondWith(
      (async () => {
        const cache = await caches.open(CACHE_NAME);
        const cached =
          (await cache.match(req, { ignoreSearch: true })) ||
          (await cache.match('/index.html')) ||
          (await cache.match('/'));

        // 后台网络刷新（使用 req.url 字符串作为缓存键，杜绝 navigate 模式报错）
        const fetchPromise = fetch(req)
          .then((networkRes) => {
            if (networkRes && networkRes.ok) {
              cache.put(req.url, networkRes.clone());
            }
            return networkRes;
          })
          .catch((err) => {
            console.warn('SW navigate fetch error:', err);
            return cached;
          });

        // 缓存命中直接秒开（0ms），并在后台静默更新
        if (cached) {
          fetchPromise.catch(() => {});
          return cached;
        }

        // 缓存未命中时等待网络
        const res = await fetchPromise;
        if (res) return res;

        // 终极离线兜底 HTML
        return new Response(
          '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ReadCine</title><style>body{background:#0c0f14;color:#e7ebe6;font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:20px;text-align:center;}h2{margin-bottom:8px;}p{color:#9aa3ab;}</style></head><body><div><h2>暂时无法连接网络</h2><p>请检查网络连接后下拉刷新重试。</p></div></body></html>',
          { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
        );
      })()
    );
    return;
  }

  // 2. 对于 stats.json / headlines.json：采用 Stale-While-Revalidate 策略
  if (url.pathname.endsWith('.json')) {
    event.respondWith(
      (async () => {
        const cache = await caches.open(CACHE_NAME);
        const cached = await cache.match(req, { ignoreSearch: true });
        const fetchPromise = fetch(req)
          .then((res) => {
            if (res && res.ok) {
              cache.put(req.url, res.clone());
            }
            return res;
          })
          .catch(() => cached);

        const result = cached || (await fetchPromise);
        return (
          result ||
          new Response('{}', {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
          })
        );
      })()
    );
    return;
  }

  // 3. 对于图标与静态资源：采用 Cache First 策略
  event.respondWith(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      const cached = await cache.match(req, { ignoreSearch: true });
      if (cached) {
        return cached;
      }
      try {
        const res = await fetch(req);
        if (res && res.ok) {
          cache.put(req.url, res.clone());
        }
        return res;
      } catch (err) {
        return new Response('', { status: 404 });
      }
    })()
  );
});
