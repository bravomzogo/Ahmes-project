// Register service worker with cache-busting and update checks
if ('serviceWorker' in navigator) {
  // Add version parameter to prevent caching
  const swUrl = `/static/shaibu.js?v=${Date.now()}`;
  
  navigator.serviceWorker.register(swUrl)
    .then(registration => {
      console.log('ServiceWorker registration successful with scope:', registration.scope);
      
      // Check for updates immediately
      registration.update();
      
      // Periodic update check (every 1 hour)
      setInterval(() => {
        registration.update().then(() => {
          console.log('ServiceWorker update check completed');
        });
      }, 60 * 60 * 1000);

      // Track installation state
      registration.addEventListener('updatefound', () => {
        const installingWorker = registration.installing;
        console.log('New ServiceWorker version found:', installingWorker);
        
        installingWorker.addEventListener('statechange', () => {
          if (installingWorker.state === 'installed') {
            if (navigator.serviceWorker.controller) {
              console.log('New content available; please refresh.');
              // Optional: Show update notification to user
            } else {
              console.log('Content is cached for offline use.');
            }
          }
        });
      });

      return registration.pushManager.getSubscription()
        .then(subscription => {
          if (subscription) {
            console.log('Existing push subscription found');
            return subscription;
          }
          
          console.log('Creating new push subscription');
          return registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array('{{ VAPID_PUBLIC_KEY }}')
          });
        });
    })
    .then(subscription => {
      if (!subscription) {
        console.log('Push subscription not available');
        return;
      }
      
      console.log('Sending subscription to server');
      fetch('/save-subscription/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
          subscription: subscription,
          sw_version: 'v1.0'  // Add version identifier
        })
      })
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to save subscription');
        }
        console.log('Subscription saved successfully');
      })
      .catch(err => {
        console.error('Subscription save error:', err);
      });
    })
    .catch(err => {
      console.error('ServiceWorker registration failed:', err);
      // Optional: Show error to user
    });
} else {
  console.warn('Service workers are not supported in this browser');
}

// Helper function to convert VAPID key
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}

// Helper function to get CSRF token
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Add event listener to handle page reload for updates
window.addEventListener('load', () => {
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({
      type: 'INIT',
      message: 'Client is loaded'
    });
  }
});