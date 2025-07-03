// Cart logic separated
function getCart() {
    return JSON.parse(localStorage.getItem('cart') || '[]');
}
function setCart(cart) {
    localStorage.setItem('cart', JSON.stringify(cart));
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
