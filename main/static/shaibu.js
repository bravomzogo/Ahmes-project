self.addEventListener('install', function(event) {
  console.log('ServiceWorker installing...');
  event.waitUntil(
    caches.open('shaibu-v1')
      .then(cache => {
        console.log('Caching assets...');
        const resources = [
          '/static/images/Ahmes.PNG?v=1',
          '/static/images/Ahmes.PNG?v=1'
        ];
        // Try caching each resource individually
        return Promise.all(
          resources.map(url =>
            fetch(url)
              .then(response => {
                if (!response.ok) {
                  console.warn(`Failed to fetch ${url}: ${response.status}`);
                  return null; // Skip failed resources
                }
                return cache.put(url, response);
              })
              .catch(err => {
                console.warn(`Failed to fetch ${url}: ${err}`);
                return null;
              })
          )
        );
      })
      .then(() => {
        console.log('ServiceWorker installed and assets cached');
        return self.skipWaiting();
      })
      .catch(err => {
        console.error('ServiceWorker install failed:', err);
      })
  );
});

self.addEventListener('activate', function(event) {
  console.log('ServiceWorker activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(name => name !== 'shaibu-v1')
          .map(name => caches.delete(name))
      );
    }).then(() => {
      console.log('Old caches cleared');
      return self.clients.claim();
    }).catch(err => {
      console.error('ServiceWorker activation failed:', err);
    })
  );
});

self.addEventListener('push', function(event) {
  console.log('Push event received:', event);
  let data;
  try {
    data = event.data ? event.data.json() : {};
    console.log('Parsed push data:', data);
  } catch (err) {
    console.error('Error parsing push data:', err);
    return;
  }

  if (!data.title || !data.body || !data.url) {
    console.error('Invalid push notification data:', data);
    return;
  }

  const options = {
    body: data.body,
    icon: '/static/images/Ahmes.PNG?v=1',
    badge: '/static/images/Ahmes.PNG?v=1',
    data: {
      url: data.url,
      timestamp: Date.now(),
      id: data.id || (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2))
    },
    vibrate: [200, 100, 200],
    requireInteraction: true,
    actions: [
      { action: 'open', title: 'Open' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };

  console.log('Showing notification with options:', options);
  event.waitUntil(
    self.registration.showNotification(data.title, options)
      .catch(err => {
        console.error('Error showing notification:', err);
      })
  );
});

self.addEventListener('notificationclick', function(event) {
  console.log('Notification clicked:', event.notification.data.id);
  event.notification.close();

  const action = event.action;
  const notificationData = event.notification.data;

  if (action === 'dismiss') {
    console.log('Notification dismissed:', notificationData.id);
    return;
  }

  if (!notificationData.url) {
    console.error('No URL provided in notification data:', notificationData);
    return;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clientsArr => {
        const matchingClient = clientsArr.find(client =>
          client.url === notificationData.url && client.focus()
        );

        if (matchingClient) {
          console.log('Focusing existing window:', notificationData.url);
          return matchingClient.focus();
        }

        console.log('Opening new window:', notificationData.url);
        return clients.openWindow(notificationData.url)
          .catch(err => {
            console.error('Error opening window:', err);
          });
      })
      .catch(err => {
        console.error('Error matching clients:', err);
      })
  );
});

self.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'INIT') {
    console.log('Received message from client:', event.data.message);
  }
});

self.addEventListener('fetch', function(event) {
  console.log('ServiceWorker fetching:', event.request.url);
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          console.log('Serving from cache:', event.request.url);
          return response;
        }
        return fetch(event.request).catch(err => {
          console.error('Fetch failed for:', event.request.url, err);
        });
      })
  );
});