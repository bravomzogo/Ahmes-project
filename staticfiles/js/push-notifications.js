if ('serviceWorker' in navigator) {
  // Prevent multiple registrations
  if (!navigator.serviceWorker.controller) {
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
            const vapidPublicKey = 'BOJOfVu1lrA7KjqPNvU9Q5Cwl0/q8K0IbT1ZCFIVTN8gbwbZYTl63G9fLdx2EzD434kPnj51KFEoItvWzEiFtes=';
            console.log('VAPID Public Key:', vapidPublicKey); // Debug log
            try {
              return registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
              });
            } catch (err) {
              console.error('Push subscription failed:', err);
              throw err;
            }
          });
      })
      .then(subscription => {
        if (!subscription) {
          console.log('Push subscription not available');
          return;
        }
        
        console.log('Sending subscription to server');
        return fetch('/save-subscription/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify({
            subscription: subscription,
            sw_version: 'v1.0'
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
        if (err.name === 'InvalidAccessError') {
          console.error('Invalid VAPID public key. Check key format and length:', vapidPublicKey);
        }
      });
  } else {
    console.log('ServiceWorker already registered:', navigator.serviceWorker.controller.scriptURL);
  }
} else {
  console.warn('Service workers are not supported in this browser');
}

function urlBase64ToUint8Array(base64String) {
  try {
    if (!base64String || typeof base64String !== 'string') {
      throw new Error('VAPID public key is empty or not a string');
    }

    console.log('Processing VAPID key:', base64String); // Debug log
    const cleanedBase64 = base64String
      .trim()
      .replace(/\n/g, '')
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const padding = '='.repeat((4 - cleanedBase64.length % 4) % 4);
    const base64 = cleanedBase64 + padding;

    const rawData = window.atob(base64);
    const uint8Array = Uint8Array.from([...rawData].map(char => char.charCodeAt(0)));
    
    // Validate key length (65 bytes for uncompressed P-256)
    if (uint8Array.length !== 65) {
      throw new Error(`Invalid VAPID key length: ${uint8Array.length} bytes (expected 65)`);
    }
    
    return uint8Array;
  } catch (err) {
    console.error('Failed to convert VAPID key to Uint8Array:', err);
    throw err;
  }
}

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

window.addEventListener('load', () => {
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({
      type: 'INIT',
      message: 'Client is loaded'
    });
  }
});