const CACHE_NAME = 'guarda-chat-cache-v1';
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/service-worker.js',
  '/static/sounds/arpeggio-467.mp3',
  '/static/icon-192.png',
  '/static/icon-512.png'
];

// Instalando o Service Worker e fazendo o cache inicial
self.addEventListener('install', event => {
  console.log('[Service Worker] Instalado');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Caching all assets');
        return cache.addAll(urlsToCache);
      })
  );
});

// Captura das requisições e responde com os recursos em cache
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(event.request);
      })
  );
});

// Ativando e limpando o cache desatualizado
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (!cacheWhitelist.includes(cacheName)) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
