var CACHE_NAME = 'snap-lab-v1';
var SNAPCHAT_HOSTS = [
  'accounts.snapchat.com',
  'static.snapchat.com',
  'accounts.snapchat.com.sc-tuna.com',
  'api.snapchat.com',
  'app.snapchat.com',
];

self.addEventListener('install', function(e) {
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(k) { return k !== CACHE_NAME; }).map(function(k) { return caches.delete(k); })
      );
    })
  );
  return self.clients.claim();
});

self.addEventListener('fetch', function(e) {
  var url = new URL(e.request.url);

  var isBlocked = SNAPCHAT_HOSTS.some(function(host) {
    return url.hostname === host || url.hostname.endsWith('.' + host);
  });

  if (isBlocked) {
    if (url.pathname.match(/\.(css|js|png|jpg|gif|svg|ico|webp|woff2?|ttf|eot)$/i)) {
      e.respondWith(fetch(e.request).catch(function() { return syntheticResponse(url); }));
    } else {
      e.respondWith(syntheticResponse(url));
    }
    return;
  }

  e.respondWith(
    fetch(e.request).catch(function() {
      return caches.match(e.request);
    })
  );
});

function syntheticResponse(url) {
  var ct = 'text/plain';
  if (url.pathname.match(/\.json$/)) ct = 'application/json';
  else if (url.pathname.match(/\.html?$/)) ct = 'text/html';

  var body = ct === 'application/json' ? '{}' : '';
  return new Response(body, {
    status: 200,
    statusText: 'OK',
    headers: {
      'Content-Type': ct,
      'Cache-Control': 'no-store',
      'X-Snap-Lab': 'blocked',
    },
  });
}
