importScripts('https://www.gstatic.com/firebasejs/8.10.0/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/8.10.0/firebase-messaging.js');

// Substitua pelos seus dados de configuração do Firebase
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

messaging.onBackgroundMessage(function(payload) {
    console.log('[firebase-messaging-sw.js] Received background message ', payload);

    const notificationTitle = payload.notification.title || 'Nova Mensagem';
    const notificationOptions = {
        body: payload.notification.body || 'Você recebeu uma nova mensagem.',
        icon: '/static/icon-192.png',
        // Adiciona som à notificação em segundo plano
        // Para Android, você pode especificar um som personalizado se o arquivo estiver em /static/sounds
        // Para iOS, o som é geralmente controlado pelo sistema ou pelo payload APNs
        // sound: '/static/sounds/arpeggio-467.mp3' // Descomente e ajuste se necessário
    };

    return self.registration.showNotification(notificationTitle, notificationOptions);
});

// Opcional: Adicionar um listener para o evento de clique na notificação
self.addEventListener('notificationclick', function(event) {
    console.log('[Service Worker] Notification click Received.', event);
    event.notification.close();

    // Abre a janela do aplicativo quando a notificação é clicada
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
