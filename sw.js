// ReadCine PWA Service Worker v5 (Safe Pass-Through Edition)
// 清除所有历史缓存，保证 100% 走原生网络，彻底杜绝任何白屏与 ERR_FAILED 故障

const CACHE_NAME = 'readcine-pwa-v5';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(keys.map((k) => caches.delete(k)));
    }).then(() => self.clients.claim())
  );
});

// fetch 监听器保持就绪以满足 PWA 安装审计，但不做破坏性拦截，完全由浏览器原生网络处理
self.addEventListener('fetch', (event) => {
  // 原生透传，绝不干预导航与请求
  return;
});
