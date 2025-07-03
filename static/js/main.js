// main.js
// --- Utility Functions ---
function getCart() {
    return JSON.parse(localStorage.getItem('cart') || '[]');
}
function setCart(cart) {
    localStorage.setItem('cart', JSON.stringify(cart));
}
function isLoggedIn() {
    // Check for server-side session by looking for user element in DOM
    const userElement = document.querySelector('.nav-user-name');
    return !!userElement;
}
function requireLogin(redirectTo) {
    if (!isLoggedIn()) {
        window.location.href = '/login?next=' + encodeURIComponent(redirectTo || window.location.pathname);
    }
}

// --- Product Card Logic ---
function renderProductCard(p, showAddBtn = true) {
    return `
    <div class="product-card">
        <img src="${p.img}" alt="${p.name}" width="150">
        <h4>${p.name}</h4>
        <p>Rs.${p.price} <span class="product-weight">(${p.weight}g)</span></p>
        <p>${p.desc}</p>
        ${showAddBtn && p.stock > 0 ? `<button class="add-to-cart-btn" data-id="${p.id}">Add to Cart</button>` : `<span class="out-of-stock">Out of Stock</span>`}
    </div>`;
}
function setupAddToCartButtons() {
    document.querySelectorAll('.add-to-cart-btn').forEach(btn => {
        btn.onclick = function(e) {
            e.stopPropagation();
            const id = +this.dataset.id;
            fetch('/api/product/' + id).then(res => res.json()).then(product => {
                if (product && product.stock > 0) addToCart(product);
            });
        };
    });
}
function addToCart(product) {
    let cart = getCart();
    const idx = cart.findIndex(item => item.id === product.id);
    if (idx > -1) {
        cart[idx].qty += 1;
    } else {
        cart.push({ ...product, qty: 1 });
    }
    setCart(cart);
    showToast('Added to cart!');
    updateCartIcon();
}
function updateCartIcon() {
    const icon = document.getElementById('cart-icon');
    if (icon) {
        const cart = getCart();
        icon.textContent = `🛒 (${cart.reduce((sum, i) => sum + i.qty, 0)})`;
    }
}
function showToast(msg) {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.className = 'show';
    setTimeout(() => { toast.className = ''; }, 2000);
}

// Group products by base_id for catalog display
function groupProductsByBaseId(products) {
    const map = {};
    products.forEach(p => {
        if (!map[p.base_id]) {
            map[p.base_id] = { ...p, weights: {} };
        }
        map[p.base_id].weights[p.weight] = p.price;
    });
    return Object.values(map);
}

function renderProductCardGrouped(p, showAddBtn = true) {
    const weightOptions = Object.entries(p.weights).map(([w, price]) => `<option value="${w}">${w}g - Rs.${price}</option>`).join('');
    return `
    <div class="product-card">
        <img src="${p.img}" alt="${p.name}" width="150">
        <h4>${p.name.replace(/ \d+g$/, '')}</h4>
        <p>${p.desc}</p>
        <label>Weight:
            <select class="weight-select" data-base-id="${p.base_id}">
                ${weightOptions}
            </select>
        </label>
        ${showAddBtn && p.stock > 0 ? `<button class="add-to-cart-btn" data-base-id="${p.base_id}">Add to Cart</button>` : `<span class="out-of-stock">Out of Stock</span>`}
    </div>`;
}

function setupAddToCartButtonsGrouped(allProducts) {
    document.querySelectorAll('.add-to-cart-btn').forEach(btn => {
        btn.onclick = function(e) {
            e.stopPropagation();
            const baseId = +this.dataset.baseId;
            const select = this.parentElement.querySelector('.weight-select');
            const weight = select.value;
            // Find the matching product variant
            const product = allProducts.find(p => p.base_id === baseId && p.weight === weight);
            if (product && product.stock > 0) addToCart(product);
        };
    });
}

// --- Homepage, Catalog, Region Map ---
document.addEventListener('DOMContentLoaded', function() {
    updateCartIcon();
    // Modal logic
    const modal = document.getElementById('browse-modal');
    const exploreBtn = document.getElementById('explore-btn');
    const closeModalBtn = document.querySelector('.close-modal');
    if (exploreBtn && modal) {
        exploreBtn.addEventListener('click', () => {
            modal.setAttribute('aria-hidden', 'false');
        });
    }
    if (closeModalBtn && modal) {
        closeModalBtn.addEventListener('click', () => {
            modal.setAttribute('aria-hidden', 'true');
        });
    }
    // Browse modal logic
    const browseBtn = document.getElementById('explore-btn');
    const browseModal = document.getElementById('browse-modal');
    if (browseBtn && browseModal) {
        browseBtn.onclick = function() {
            browseModal.style.display = 'flex';
            browseModal.focus();
        };
        browseModal.querySelector('.browse-modal-close').onclick = function() {
            browseModal.style.display = 'none';
        };
        browseModal.querySelector('.browse-modal-cancel').onclick = function() {
            browseModal.style.display = 'none';
        };
        // Optional: close modal on Escape key
        browseModal.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') browseModal.style.display = 'none';
        });
    }
    // Tab logic for featured products
    const tabs = document.querySelectorAll('.tab');
    const featuredProducts = document.getElementById('featured-products');
    function loadFeatured(type) {
        featuredProducts.innerHTML = '<div class="spinner" aria-label="Loading products..."></div>';
        fetch('/api/products')
            .then(res => res.json())
            .then(data => {
                setTimeout(() => { // Simulate delay
                    const filtered = data.filter(p => p.type === type).slice(0, 6);
                    if (filtered.length === 0) {
                        featuredProducts.innerHTML = '<p>No products available.</p>';
                        return;
                    }
                    featuredProducts.innerHTML = '';
                    // group variants and render grouped cards
                    const grouped = groupProductsByBaseId(filtered);
                    grouped.forEach(p => {
                        featuredProducts.innerHTML += renderProductCardGrouped(p);
                    });
                    // setup add-to-cart for grouped variants
                    setupAddToCartButtonsGrouped(filtered);
                }, 500);
            });
    }
    if (tabs.length && featuredProducts) {
        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                tabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                loadFeatured(this.dataset.type);
            });
        });
        loadFeatured('Pickles');
    }

    // Catalog page logic
    if (document.getElementById('product-grid')) {
        const grid = document.getElementById('product-grid');
        const searchBar = document.getElementById('search-bar');
        const typeFilter = document.getElementById('type-filter');
        let allProducts = [];
        let groupedProducts = [];
        // Read category filter from URL param and set typeFilter
        const urlParams = new URLSearchParams(window.location.search);
        const urlCategory = urlParams.get('category') || 'All';
        if (typeFilter) typeFilter.value = urlCategory;
        // Catalog title element
        const catalogTitle = document.getElementById('catalog-title');
        // Helper to update title text
        function updateCatalogTitle(cat) {
            const titles = {
                veg_pickles: 'Veg Pickles',
                non_veg_pickles: 'Non-Veg Pickles',
                snacks: 'Snacks',
                All: 'All Products'
            };
            // Only update title if we have a valid category
            if (titles[cat]) {
                catalogTitle.textContent = titles[cat];
            }
        }
        // Only update title if there's a URL category parameter
        if (urlCategory && urlCategory !== 'All') {
            updateCatalogTitle(urlCategory);
        }
        function renderProducts(products) {
            if (!products.length) {
                grid.innerHTML = '<p>No products found.</p>';
                return;
            }
            grid.innerHTML = '';
            groupedProducts = groupProductsByBaseId(products);
            groupedProducts.forEach(p => {
                grid.innerHTML += renderProductCardGrouped(p);
            });
            setupAddToCartButtonsGrouped(products);
        }
        function filterProducts() {
            let filtered = allProducts;
            const currentPath = window.location.pathname;
            
            // Only update title when user changes filter, not on initial load
            if (typeFilter && typeFilter.value) {
                updateCatalogTitle(typeFilter.value);
            }
            
            // For category-specific pages, don't apply category filtering as data is already filtered
            if (currentPath === '/veg-pickles' || currentPath === '/non-veg-pickles' || currentPath === '/snacks') {
                // Data is already category-specific, only apply search filter
            } else if (currentPath === '/products') {
                // For general products page, apply category filter if selected
                if (typeFilter && typeFilter.value && typeFilter.value !== 'All') {
                    filtered = filtered.filter(p => p.category === typeFilter.value);
                }
            } else {
                // For other pages with URL params
                if (urlCategory && urlCategory !== 'All') {
                    filtered = filtered.filter(p => p.category === urlCategory);
                } else if (typeFilter && typeFilter.value !== 'All') {
                    filtered = filtered.filter(p => p.category === typeFilter.value);
                }
            }
            
            // Search bar
            if (searchBar && searchBar.value.trim()) {
                const q = searchBar.value.trim().toLowerCase();
                filtered = filtered.filter(p => p.name.toLowerCase().includes(q));
            }
            renderProducts(filtered);
        }
        // Determine the appropriate API endpoint based on current page
        let apiEndpoint = '/api/products';
        const currentPath = window.location.pathname;
        
        if (currentPath === '/veg-pickles') {
            apiEndpoint = '/api/products/veg-pickles';
        } else if (currentPath === '/non-veg-pickles') {
            apiEndpoint = '/api/products/non-veg-pickles';
        } else if (currentPath === '/snacks') {
            apiEndpoint = '/api/products/snacks';
        }
        // For /products page, use the general endpoint
        
        fetch(apiEndpoint)
            .then(res => res.json())
            .then(data => {
                console.log('Loaded products:', data);
                // For category-specific pages, don't apply additional category filtering
                let filteredData = data;
                if (apiEndpoint === '/api/products' && urlCategory && urlCategory !== 'All') {
                    filteredData = filteredData.filter(p => p.category === urlCategory);
                }
                allProducts = filteredData;
                filterProducts();
            });
        [searchBar, typeFilter].forEach(el => {
            if (el) el.addEventListener('input', filterProducts);
        });
    }

    // Sidebar region and type filter logic for /products/map
    if (document.querySelector('.map-main-layout')) {
        const regionItems = document.querySelectorAll('.region-item');
        const typeTabs = document.querySelectorAll('.type-tab');
        const regionProducts = document.getElementById('region-products');
        // Define product distribution per region: 2 non-veg, 2 veg, 4 snacks
        const regionProductMap = {
            All:     [1,7,13],  // One non-veg, one veg, one snack
            North:   [1,7,13],  // Chicken Pickle, Mango Pickle, Banana Chips
            South:   [2,8,14],  // Fish Pickle, Lemon Pickle, Crispy Aam-Papad
            East:    [3,9,15],  // Gongura Mutton, Tomato Pickle, Chekka Pakodi
            West:    [4,10,16], // Mutton Pickle, Kakarakaya Pickle, Boondhi Acchu
            Central: [5,11,17]  // Gongura Prawns, Chintakaya Pickle, Chekkalu
        };
        let allProducts = [];
        let selectedRegion = 'All';
        let selectedType = 'All';
        function renderMapProducts(products) {
            if (!products.length) {
                regionProducts.innerHTML = '<p class="map-placeholder">No products found for this region/type.</p>';
                return;
            }
            // group variants and render grouped cards
            const grouped = groupProductsByBaseId(products);
            regionProducts.innerHTML = '<div class="product-grid">' + grouped.map(p => renderProductCardGrouped(p)).join('') + '</div>';
            setupAddToCartButtonsGrouped(products);
        }
        function filterMapProducts() {
            // Always limit products based on predefined region distribution
            const baseIds = regionProductMap[selectedRegion];
            let filtered = allProducts.filter(p => baseIds.includes(p.base_id));
            // Then apply type filter
            if (selectedType !== 'All') {
                filtered = filtered.filter(p => p.type === selectedType);
            }
            renderMapProducts(filtered);
        }
        fetch('/api/products')
            .then(res => res.json())
            .then(data => {
                allProducts = data;
                filterMapProducts();
            });
        regionItems.forEach(item => {
            item.onclick = function() {
                regionItems.forEach(i => i.classList.remove('active'));
                this.classList.add('active');
                selectedRegion = this.dataset.region;
                filterMapProducts();
            };
        });
        typeTabs.forEach(tab => {
            tab.onclick = function() {
                typeTabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                selectedType = this.dataset.type;
                filterMapProducts();
            };
        });
    }

    // Smooth scroll to Featured Delights
    const specialsBtn = document.getElementById('specials-btn');
    const featuredSection = document.getElementById('featured-delights');
    if (specialsBtn && featuredSection) {
        specialsBtn.onclick = function() {
            featuredSection.scrollIntoView({ behavior: 'smooth' });
        };
    }
    // Footer Featured Delights link
    const footerFeatured = document.querySelector('.footer-featured-link');
    if (footerFeatured && featuredSection) {
        footerFeatured.onclick = function(e) {
            e.preventDefault();
            window.scrollTo({ top: featuredSection.offsetTop - 40, behavior: 'smooth' });
        };
    }
});

// --- Cart Page ---
if (document.getElementById('cart-items')) {
    const cartItemsDiv = document.getElementById('cart-items');
    const cartSummaryDiv = document.getElementById('cart-summary');
    function renderCart() {
        let cart = getCart();
        if (!cart.length) {
            cartItemsDiv.innerHTML = '<p>Your cart is empty.</p>';
            cartSummaryDiv.innerHTML = '';
            return;
        }
        cartItemsDiv.innerHTML = '';
        let subtotal = 0;
        cart.forEach((item, idx) => {
            subtotal += item.price * item.qty;
            cartItemsDiv.innerHTML += `
            <div class="cart-item">
                <img src="${item.img}" alt="${item.name}" width="80">
                <span>${item.name}</span>
                <span>Rs.${item.price}</span>
                <button class="qty-btn" data-idx="${idx}" data-action="-">-</button>
                <span>${item.qty}</span>
                <button class="qty-btn" data-idx="${idx}" data-action="+">+</button>
                <button class="remove-btn" data-idx="${idx}">Remove</button>
            </div>`;
        });
        cartSummaryDiv.innerHTML = `<div class="cart-summary">
            <p>Subtotal: Rs.${subtotal}</p>
            <p>Shipping: Free</p>
            <p><b>Total: Rs.${subtotal}</b></p>
            <a href="/checkout" class="checkout-btn">Proceed to Checkout</a>
        </div>`;
        // Quantity and remove logic
        document.querySelectorAll('.qty-btn').forEach(btn => {
            btn.onclick = function() {
                let cart = getCart();
                const idx = +this.dataset.idx;
                if (this.dataset.action === '+') cart[idx].qty++;
                else if (cart[idx].qty > 1) cart[idx].qty--;
                setCart(cart);
                renderCart();
            };
        });
        document.querySelectorAll('.remove-btn').forEach(btn => {
            btn.onclick = function() {
                let cart = getCart();
                cart.splice(+this.dataset.idx, 1);
                setCart(cart);
                renderCart();
            };
        });
    }
    renderCart();
}

// --- Checkout, Auth, Orders ---
if (document.getElementById('checkout-form')) {
    requireLogin('/checkout');
    const formDiv = document.getElementById('checkout-form');
    const summaryDiv = document.getElementById('order-summary');
    let step = 1;
    let orderData = {};
    let userData = {};
    
    // Fetch user data from server
    function loadUserData() {
        return fetch('/api/user/profile')
            .then(response => {
                if (response.status === 401) {
                    window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                    return null;
                }
                return response.json();
            })
            .then(data => {
                if (data && !data.error) {
                    userData = data;
                    // Save to localStorage for compatibility
                    localStorage.setItem('profileInfo', JSON.stringify({
                        name: data.name || '',
                        email: data.email || '',
                        phone: data.phone || '',
                        street: data.street || '',
                        city: data.city || '',
                        pincode: data.pincode || '',
                        country: data.country || ''
                    }));
                }
                return data;
            })
            .catch(err => {
                console.error('Error loading user data:', err);
                return null;
            });
    }
    
    function renderStep() {
        showSummary(); // Always update order summary when rendering a step
        if (step === 1) {
            formDiv.innerHTML = `
                <div class="checkout-card">
                    <div class="checkout-card-header"><i class="fa-solid fa-user"></i> Contact Info</div>
                    <div class="checkout-card-body">
                        <input type='text' id='name' placeholder='Full Name' required class='checkout-input'><br>
                        <input type='email' id='email' placeholder='Email Address' required class='checkout-input'><br>
                        <input type='tel' id='phone' placeholder='Phone Number' required class='checkout-input'><br>
                        <button id='next1' class='checkout-next-btn'>Next</button>
                    </div>
                </div>`;
            // Auto-fill contact info from user data
            const nameField = document.getElementById('name');
            const emailField = document.getElementById('email');
            const phoneField = document.getElementById('phone');
            nameField.value = userData.name || '';
            emailField.value = userData.email || '';
            phoneField.value = userData.phone || '';
            // Ensure fields are visible and trigger input events if needed
            nameField.dispatchEvent(new Event('input'));
            emailField.dispatchEvent(new Event('input'));
            phoneField.dispatchEvent(new Event('input'));
            document.getElementById('next1').onclick = () => {
                orderData.name = nameField.value;
                orderData.email = emailField.value;
                orderData.phone = phoneField.value;
                step = 2; renderStep();
            };
        } else if (step === 2) {
            formDiv.innerHTML = `
                <div class="checkout-card">
                    <div class="checkout-card-header"><i class="fa-solid fa-location-dot"></i> Shipping Address</div>
                    <div class="checkout-card-body">
                        <input type='text' id='street' placeholder='Street Address' required class='checkout-input'><br>
                        <div class='checkout-row'>
                            <input type='text' id='city' placeholder='City' required class='checkout-input'>
                            <input type='text' id='pincode' placeholder='Pincode' required class='checkout-input'>
                        </div>
                        <input type='text' id='country' value='India' required class='checkout-input'><br>
                        <div class='checkout-btn-row'>
                            <button id='back1' class='checkout-back-btn'>Back</button>
                            <button id='next2' class='checkout-next-btn'>Next</button>
                        </div>
                    </div>
                </div>`;
            // Pre-fill fields from user data
            if (userData.street) document.getElementById('street').value = userData.street;
            if (userData.city) document.getElementById('city').value = userData.city;
            if (userData.pincode) document.getElementById('pincode').value = userData.pincode;
            if (userData.country) document.getElementById('country').value = userData.country;
            document.getElementById('back1').onclick = () => { step = 1; renderStep(); };
            document.getElementById('next2').onclick = () => {
                orderData.street = document.getElementById('street').value;
                orderData.city = document.getElementById('city').value;
                orderData.pincode = document.getElementById('pincode').value;
                orderData.country = document.getElementById('country').value;
                step = 3; renderStep();
            };
        } else if (step === 3) {
            // Only show Cash on Delivery (COD) as payment method
            formDiv.innerHTML = `
                <div class="checkout-card payment-method-card">
                     <div class="checkout-card-header"><i class="fa-solid fa-money-check-dollar"></i> Payment Method</div>
                     <div class="checkout-card-body">
                         <button id="cod-btn" class="checkout-next-btn">Cash on Delivery</button>
                         <button id="back2" class="checkout-back-btn">Back</button>
                     </div>
                </div>`;
            document.getElementById('back2').onclick = () => { step = 2; renderStep(); };
            document.getElementById('cod-btn').onclick = function(e) {
                e.target.disabled = true; // prevent double-click
                orderData.paymentMethod = 'COD';
                placeOrder();
            };
        }
    }
    function showSummary() {
        let cart = getCart();
        let subtotal = cart.reduce((sum, item) => sum + item.price * item.qty, 0);
        summaryDiv.innerHTML = `<div class='cart-summary'>
            <p>Subtotal: Rs.${subtotal}</p>
            <p>Shipping: Free</p>
            <p><b>Total: Rs.${subtotal}</b></p>
        </div>`;
    }
    function placeOrder() {
        let cart = getCart();
        if (!cart.length) { 
            alert('Cart is empty!'); 
            return; 
        }
        
        // Validate required order data
        if (!orderData.name || !orderData.email || !orderData.phone || 
            !orderData.street || !orderData.city || !orderData.pincode) {
            alert('Please fill in all required fields before placing order.');
            return;
        }
        
        let order = {
            ...orderData,
            items: cart,
            total: cart.reduce((sum, item) => sum + item.price * item.qty, 0),
            date: new Date().toLocaleString(),
            status: 'Placed'
        };
        
        fetch('/api/orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(order)
        })
        .then(res => {
            if (!res.ok) {
                throw new Error('Network response was not ok');
            }
            return res.json();
        })
        .then(data => {
            if (data.success) {
                localStorage.removeItem('cart');
                updateCartIcon(); // Update cart icon after clearing
                window.location.href = '/order-confirmation?orderId=' + data.orderId;
            } else {
                alert('Error placing order: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(err => {
            console.error('Error placing order:', err);
            alert('Error placing order. Please try again.');
        });
    }
    
    // Initialize checkout form
    // Fetch user data from server and update userData before rendering checkout
    loadUserData().then(() => {
        renderStep();
    });
    
    // Listen for profile updates from other windows
    window.addEventListener('message', function(event) {
        if (event.data.type === 'PROFILE_UPDATED') {
            // Reload user data and refresh the form
            loadUserData().then(() => {
                renderStep();
            });
        }
    });
}

// Conditional nav (show login/logout)
document.addEventListener('DOMContentLoaded', function() {
    // Efficiently update only the login/logout area in nav
    const navAuth = document.querySelector('.nav-auth');
    if (navAuth) {
        if (isLoggedIn()) {
            navAuth.innerHTML = '<a href="/orders">My Orders</a> <a href="/logout">Logout</a>';
        } else {
            navAuth.innerHTML = '<a href="/login">Login</a>';
        }
    }
});
// Order history page logic
if (document.getElementById('order-history')) {
    requireLogin('/orders');
    fetch('/api/orders')
        .then(res => res.json())
        .then(data => {
            if (!Array.isArray(data)) {
                document.getElementById('order-history').innerHTML = '<tr><td colspan="5">Error loading orders.</td></tr>';
                return;
            }
            if (!data.length) {
                document.getElementById('order-history').innerHTML = '<tr><td colspan="5">No orders found.</td></tr>';
                return;
            }
            document.getElementById('order-history').innerHTML = data.map(o => `
                <tr>
                  <td>#${o.id}</td>
                  <td>${o.date || ''}</td>
                  <td>Rs.${o.total || ''}</td>
                  <td>${o.status || 'Processing'}</td>
                  <td><a href="/orders/${o.id}" class="order-table-link">View Details</a></td>
                </tr>
            `).join('');
        })
        .catch(err => {
            console.error('Error loading orders:', err);
            document.getElementById('order-history').innerHTML = '<tr><td colspan="5">Error loading orders.</td></tr>';
        });
}
// Order detail page logic
if (document.getElementById('order-detail')) {
    requireLogin(window.location.pathname);
    const orderId = window.location.pathname.split('/').pop();
    fetch('/api/order/' + orderId)
        .then(res => res.json())
        .then(order => {
            if (!order || order.error) {
                document.getElementById('order-detail').innerHTML = '<p>Order not found.</p>';
                return;
            }
            let itemsHtml = '';
            if (order.items && Array.isArray(order.items)) {
                itemsHtml = order.items.map(item => `
                    <div class="order-item-row">
                        <div class="order-item-img"><img src="${item.img || '/static/img/default.jpg'}" alt="${item.name}" width="80"></div>
                        <div class="order-item-info">
                            <div class="order-item-name">${item.name}</div>
                            <div class="order-item-meta">Rs.${item.price || ''} <span class="order-item-qty">Qty: ${item.qty || ''}</span></div>
                        </div>
                    </div>
                `).join('');
            }
            document.getElementById('order-detail').innerHTML = `
                <div class="order-detail-header">
                  <h3>Order #${order.id}</h3>
                  <div class="order-detail-meta">
                    <div><b>Date:</b> ${order.date || ''}</div>
                    <div><b>Status:</b> ${order.status || 'Processing'}</div>
                    <div><b>Total:</b> Rs.${order.total || ''}</div>
                  </div>
                  <div class="order-detail-shipping">
                    <b>Shipping Info</b><br>
                    ${order.name || ''}, ${order.street || ''}, ${order.city || ''}, ${order.pincode || ''}, ${order.country || ''}
                  </div>
                </div>
                <div class="order-detail-items">
                  <h4>Items</h4>
                  ${itemsHtml || '<p>No items found.</p>'}
                </div>
                <div class="order-detail-actions">
                  <a href="/orders" class="btn">Back to Orders</a>
                </div>
            `;
        })
        .catch(err => {
            console.error('Error loading order details:', err);
            document.getElementById('order-detail').innerHTML = '<p>Error loading order details.</p>';
        });
}

// Product detail page logic
if (document.getElementById('product-detail')) {
    const productId = window.location.pathname.split('/').pop();
    fetch('/api/products')
        .then(res => res.json())
        .then(allProducts => {
            // Find all variants for this base_id
            const variant = allProducts.find(p => p.id == productId);
            if (!variant) {
                document.getElementById('product-detail').innerHTML = '<p>Product not found.</p>';
                return;
            }
            const baseId = variant.base_id;
            const variants = allProducts.filter(p => p.base_id === baseId);
            // Build dropdown
            const weightOptions = variants.map(v => `<option value="${v.weight}">${v.weight}g - Rs.${v.price}</option>`).join('');
            document.getElementById('product-detail').innerHTML = `
                <div class="product-detail-card">
                    <img src="${variant.img}" alt="${variant.name}" width="250">
                    <h3>${variant.name.replace(/ \d+g$/, '')}</h3>
                    <p>${variant.desc}</p>
                    <label>Weight:
                        <select id="detail-weight-select">
                            ${weightOptions}
                        </select>
                    </label>
                    <button id="detail-add-to-cart" data-base-id="${baseId}">Add to Cart</button>
                </div>
            `;
            document.getElementById('detail-add-to-cart').onclick = function() {
                const weight = document.getElementById('detail-weight-select').value;
                const product = allProducts.find(p => p.base_id === baseId && p.weight === weight);
                if (product && product.stock > 0) addToCart(product);
            };
        });
}

// Profile dropdown logic
document.addEventListener('DOMContentLoaded', function() {
    const profileToggle = document.getElementById('profile-toggle');
    const profileDropdown = document.getElementById('profile-dropdown');
    const logoutBtn = document.getElementById('logout-btn');
    const nameEl = document.getElementById('profile-name');
    const emailEl = document.getElementById('profile-email');
    if (!profileToggle || !profileDropdown) return;
    if (!isLoggedIn()) {
        profileToggle.onclick = () => window.location.href = '/login';
        return;
    }
    // Get user details from DOM elements (server-side rendered)
    const userElement = document.querySelector('.nav-user-name');
    if (nameEl && userElement) nameEl.textContent = userElement.textContent || 'User';
    if (emailEl) emailEl.textContent = sessionStorage.getItem('user_email') || 'user@example.com';
    // Toggle dropdown on click
    profileToggle.onclick = function(e) {
        e.stopPropagation();
        profileDropdown.classList.toggle('show');
    };
    // Logout
    if (logoutBtn) {
        logoutBtn.onclick = function() {
            window.location.href = '/logout';
        };
    }
    // Close dropdown on outside click
    document.addEventListener('click', function(e) {
        if (!profileDropdown.contains(e.target) && e.target !== profileToggle) {
            profileDropdown.classList.remove('show');
        }
    });
});

// --- Browse by Region Page Logic ---
if (document.getElementById('region-products')) {
    const container = document.getElementById('region-products');
    const regionItems = document.querySelectorAll('.region-item');
    const typeTabs = document.querySelectorAll('.type-tab');
    let allProducts = [], selectedRegion = 'All', selectedType = 'All';
    const regionMap = {
        All: [],
        North: [1,7,13],
        South: [6,10,14],
        East: [4,8,15],
        West: [3,9,16],
        Central: [5,11,17]
    };
    // Fetch products once
    fetch('/api/products')
        .then(res => res.json())
        .then(data => {
            allProducts = data;
            regionMap.All = Array.from(new Set(allProducts.map(p => p.base_id)));
            updateRegionView();
        });
    // Handle region clicks
    regionItems.forEach(item => item.addEventListener('click', () => {
        regionItems.forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        selectedRegion = item.dataset.region;
        updateRegionView();
    }));
    // Handle type clicks
    typeTabs.forEach(tab => tab.addEventListener('click', () => {
        typeTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        selectedType = tab.dataset.type;
        updateRegionView();
    }));
    // Render based on selections
    function updateRegionView() {
        let filtered = allProducts.filter(p => regionMap[selectedRegion].includes(p.base_id));
        if (selectedType !== 'All') filtered = filtered.filter(p => p.type === selectedType);
        filtered.sort((a, b) => a.name.localeCompare(b.name));
        const grouped = groupProductsByBaseId(filtered);
        container.innerHTML = grouped.length
            ? grouped.map(p => renderProductCardGrouped(p)).join('')
            : '<p>No products found for this region/type.</p>';
        setupAddToCartButtonsGrouped(filtered);
    }
}