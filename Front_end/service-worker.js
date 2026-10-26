const SHELL_CACHE = 'college-portal-shell-v5';
const APP_SHELL = [
    './',
    './index.html',
    './dashboard.html',
    './assets/graduation-background.png',
    './assets/dashboard-background.png'
];

self.addEventListener('install', event => {
    event.waitUntil(caches.open(SHELL_CACHE).then(cache => cache.addAll(APP_SHELL)));
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(keys.filter(key => key !== SHELL_CACHE).map(key => caches.delete(key))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    if (request.method !== 'GET' || url.origin !== self.location.origin) return;

    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request)
                .then(response => {
                    if (response.ok) caches.open(SHELL_CACHE).then(cache => cache.put(request, response.clone()));
                    return response;
                })
                .catch(async () => (await caches.match(request)) || (await caches.match('./dashboard.html')) || (await caches.match('./index.html')))
        );
        return;
    }

    event.respondWith(
        caches.match(request).then(cached => cached || fetch(request).then(response => {
            if (response.ok) caches.open(SHELL_CACHE).then(cache => cache.put(request, response.clone()));
            return response;
        }))
    );
});
