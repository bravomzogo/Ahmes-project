self.addEventListener('push', function(event) {
  let data;
  try {
    data = event.data ? event.data.json() : {};
  } catch (err) {
    console.error('Error parsing push data:', err);
    return;
  }

  // Validate required notification data
  if (!data.title || !data.body || !data.url) {
    console.error('Invalid push notification data:', data);
    return;
  }

  const options = {
    body: data.body,
    icon: '/static/images/logo.png?v=1', // Cache-busting for icon
    badge: '/static/images/badge.png?v=1', // Cache-busting for badge
    data: {
      url: data.url,
      timestamp: Date.now(),
      id: data.id || crypto.randomUUID() // Generate unique ID if not provided
    },
    vibrate: [200, 100, 200], // Vibration pattern for mobile devices
    requireInteraction: true, // Keep notification until user interacts
    actions: [
      { action: 'open', title: 'Open' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
      .catch(err => {
        console.error('Error showing notification:', err);
      })
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();

  const action = event.action;
  const notificationData = event.notification.data;

  // Handle different action types
  if (action === 'dismiss') {
    console.log('Notification dismissed:', notificationData.id);
    return;
  }

  // Default action or 'open' action
  if (!notificationData.url) {
    console.error('No URL provided in notification data:', notificationData);
    return;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clientsArr => {
        // Check if URL is already open
        const matchingClient = clientsArr.find(client =>
          client.url === notificationData.url && client.focus()
        );

        if (matchingClient) {
          return matchingClient.focus();
        }

        return clients.openWindow(notificationData.url)
          .then(windowClient => {
            console.log('Opened window for URL:', notificationData.url);
            return windowClient;
          })
          .catch(err => {
            console.error('Error opening window:', err);
          });
      })
      .catch(err => {
        console.error('Error matching clients:', err);
      })
  );
});

// Handle service worker messages
self.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'INIT') {
    console.log('Received message from client:', event.data.message);
    // Perform any initialization tasks if needed
  }
});