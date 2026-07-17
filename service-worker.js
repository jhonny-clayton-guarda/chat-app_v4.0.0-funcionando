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

// Firebase Messaging Service Worker
importScripts('https://www.gstatic.com/firebasejs/8.10.0/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/8.10.0/firebase-messaging.js');

const firebaseConfig = {
  apiKey: "AIzaSyAGkxSC0X29UoQLfi0asIEiqtRVsuo_9I0", // Seu apiKey
  authDomain: "guarda-chat-app-fde73.firebaseapp.com",
  projectId: "guarda-chat-app-fde73",
  storageBucket: "guarda-chat-app-fde73.firebasestorage.app",
  messagingSenderId: "566174764881",
  appId: "1:566174764881:web:e0288bf090f018396c8d70",
  measurementId: "G-3CP6L65Z3W"
};

firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();

messaging.onBackgroundMessage(function(payload) {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: '/static/icon-192.png'
  };

  return self.registration.showNotification(notificationTitle, notificationOptions);
});

