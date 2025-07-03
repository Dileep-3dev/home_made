// profile.js
// Handles saving user profile details using server-side API

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const form = document.getElementById('profile-form');
    const statusDiv = document.getElementById('profile-status');
    
    if (!form) return; // Exit if not on profile page
    
    const nameInput = document.getElementById('name');
    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('phone');

    // Save handler
    form.onsubmit = function(e) {
        e.preventDefault();
        saveProfileData();
    };

    function saveProfileData() {
        const profileData = {
            name: nameInput.value.trim(),
            phone: phoneInput.value.trim()
        };

        // Basic validation
        if (!profileData.name || !profileData.phone) {
            showStatus('Name and phone number are required', 'error');
            return;
        }

        fetch('/api/user/profile', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(profileData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showStatus('Profile saved successfully!', 'success');
                // Reload the page after a short delay to show updated data
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showStatus('Error saving profile: ' + (data.error || 'Unknown error'), 'error');
            }
        })
        .catch(err => {
            console.error('Error saving profile:', err);
            showStatus('Error saving profile data', 'error');
        });
    }

    function showStatus(message, type) {
        if (statusDiv) {
            statusDiv.textContent = message;
            statusDiv.className = 'flash ' + (type === 'success' ? 'success' : 'danger');
            setTimeout(() => {
                statusDiv.textContent = '';
                statusDiv.className = '';
            }, 3000);
        }
    }

    // Load order history
    const ordersBody = document.getElementById('profile-orders-body');
    if (ordersBody) {
        fetch('/api/orders')
          .then(res => res.json())
          .then(orders => {
              ordersBody.innerHTML = '';
              if (!Array.isArray(orders)) {
                  ordersBody.innerHTML = '<tr><td colspan="5">Error loading orders.</td></tr>';
                  return;
              }
              if (orders.length === 0) {
                  ordersBody.innerHTML = '<tr><td colspan="5">No orders found.</td></tr>';
                  return;
              }
              orders.forEach(o => {
                  const tr = document.createElement('tr');
                  tr.innerHTML = `
                      <td>#${o.id}</td>
                      <td>${o.date || ''}</td>
                      <td>Rs.${o.total || ''}</td>
                      <td>${o.status || 'Processing'}</td>
                      <td><a href="/orders/${o.id}">View</a></td>
                  `;
                  ordersBody.appendChild(tr);
              });
          })
          .catch(err => {
              console.error('Error loading orders:', err);
              ordersBody.innerHTML = '<tr><td colspan="5">Error loading orders.</td></tr>';
          });
    } else {
        console.log('Orders body element not found');
    }
});
