const CACHE_NAME = 'achat-local-v1';
// Liste des éléments de base à garder en mémoire dans le téléphone
const ASSETS = [
  '/',
  '/manifest.json'
];

// Installation du gardien sur le téléphone
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
});

// Interception des pannes de réseau
self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((cachedResponse) => {
      // Si l'élément est en mémoire ou si on a du réseau, on l'affiche.
      // Sinon, on garde l'application ouverte malgré la panne.
      return cachedResponse || fetch(e.request);
    })
  );
});
