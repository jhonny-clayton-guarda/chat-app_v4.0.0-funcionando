importScripts('https://www.gstatic.com/firebasejs/8.10.0/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/8.10.0/firebase-messaging.js');

const firebaseConfig = {
    apiKey: "AIzaSyAGkxSC0X29UoQLfi0asIEiqtRVsuo_9I0",
    authDomain: "guarda-chat-app-fde73.firebaseapp.com",
    projectId: "guarda-chat-app-fde73",
    storageBucket: "guarda-chat-app-fde73.firebasestorage.app",
    messagingSenderId: "566174764881",
    appId: "1:566174764881:web:e0288bf090f018396c8d70",
    measurementId: "G-3CP6L65Z3W"
};

firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();

// Esta função é CRUCIAL para o background. 
// Se ela não for definida corretamente, o navegador pode ignorar a notificação.
messaging.onBackgroundMessage(function(payload) {
    console.log('[firebase-messaging-sw.js] Received background message ', payload);

    // Prioriza o título e corpo que vem do backend, mas garante um fallback
    const notificationTitle = payload.data?.title || payload.notification?.title || 'Nova Mensagem';
    const notificationOptions = {
        body: payload.data?.body || payload.notification?.body || 'Você recebeu uma nova mensagem.',
        icon: '/static/icon-192.png',
        badge: '/static/icon-192.png', // Ícone pequeno na barra de status (Android)
        vibrate: [200, 100, 200],
        tag: 'chat-message', // Agrupa notificações para não encher a barra
        renotify: true, // Faz vibrar/tocar mesmo se já houver uma notificação com a mesma tag
        data: {
            url: '/' // URL para abrir ao clicar
        },
        // Configurações extras para garantir visibilidade
        requireInteraction: true, // A notificação não some sozinha até o usuário agir
        priority: 'high'
    };

    // O showNotification DEVE ser retornado como uma Promise para o Service Worker não "morrer" antes de exibir
    return self.registration.showNotification(notificationTitle, notificationOptions);
});

// Lida com o clique na notificação
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            if (clientList.length > 0) {
                let client = clientList[0];
                for (let i = 0; i < clientList.length; i++) {
                    if (clientList[i].focused) {
                        client = clientList[i];
                    }
                }
                return client.focus();
            } else {
                return clients.openWindow('/');
            }
        })
    );
});
