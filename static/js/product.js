// Product and catalog logic separated
function renderProductCard(p, showAddBtn = true) {
    return `
    <div class="product-card">
        <img src="${p.img}" alt="${p.name}" width="150" height="100">
        <h4>${p.name}</h4>
        <p>Rs.${p.price}</p>
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
