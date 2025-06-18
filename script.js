document.addEventListener('DOMContentLoaded', () => {
    const categoryToggles = document.querySelectorAll('.category-toggle');
    const floatingCartBtn = document.getElementById('floating-cart-btn');
    const cartModal = document.getElementById('cart-modal');
    const closeButton = document.querySelector('.close-button');
    const addToCartButtons = document.querySelectorAll('.add-to-cart-btn');
    const modalCartList = document.getElementById('modal-cart-list');
    const modalCartTotalSpan = document.getElementById('modal-cart-total');
    const cartItemCountSpan = document.getElementById('cart-item-count');
    const clearModalCartButton = document.getElementById('clear-modal-cart');
    const checkoutModalButton = document.getElementById('checkout-modal-btn');

    let cart = []; // Array to store cart items

    // --- Utility Functions ---

    function showToast(message) {
        let toast = document.getElementById('toast');
        if (!toast) {
            console.error("El elemento #toast no se encontró en el DOM.");
            return;
        }
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    function formatPrice(price) {
        return `$${price.toLocaleString('es-CO')}`;
    }

    function updateCartDisplay() {
        modalCartList.innerHTML = '';
        let total = 0;
        let itemCount = 0;

        if (cart.length === 0) {
            const emptyMessageLi = document.createElement('li');
            emptyMessageLi.innerHTML = `<span style="font-style: italic; color: #888; text-align: center; width: 100%;">Tu pedido está vacío.</span>`;
            modalCartList.appendChild(emptyMessageLi);
        } else {
            cart.forEach((item, index) => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <span>${item.name} (x${item.quantity})</span>
                    <span>${formatPrice(item.price * item.quantity)}</span>
                    <button class="remove-item-from-modal" data-index="${index}">X</button>
                `;
                modalCartList.appendChild(li);
                total += item.price * item.quantity;
                itemCount += item.quantity;
            });
        }

        modalCartTotalSpan.textContent = formatPrice(total);
        cartItemCountSpan.textContent = itemCount;
        cartItemCountSpan.style.display = itemCount > 0 ? 'flex' : 'none'; // Show/hide badge

        // Re-attach event listeners for remove buttons in modal
        document.querySelectorAll('.remove-item-from-modal').forEach(button => {
            button.addEventListener('click', (event) => {
                const itemIndex = parseInt(event.target.dataset.index);
                removeItemFromCart(itemIndex);
            });
        });
    }

    function removeItemFromCart(index) {
        if (index > -1 && index < cart.length) {
            if (cart[index].quantity > 1) {
                cart[index].quantity--;
            } else {
                cart.splice(index, 1);
            }
            updateCartDisplay();
            showToast('➖ Ítem eliminado del carrito.');
        }
    }

    // --- Event Listeners ---

    // Category Toggle Functionality
    categoryToggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            const categoryName = toggle.dataset.category;
            const content = document.getElementById(`${categoryName}-content`);
            const arrow = toggle.querySelector('.dropdown-arrow');

            // Toggle active class on the clicked category
            toggle.classList.toggle('active');
            content.classList.toggle('active');

            // Toggle arrow direction
            if (content.classList.contains('active')) {
                arrow.classList.replace('fa-chevron-down', 'fa-chevron-up');
            } else {
                arrow.classList.replace('fa-chevron-up', 'fa-chevron-down');
            }
        });
    });

    // Add to Cart from Menu Items
    addToCartButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            const itemName = event.target.dataset.name || event.target.closest('button').dataset.name;
            const itemPrice = parseInt(event.target.dataset.price || event.target.closest('button').dataset.price);

            const existingItemIndex = cart.findIndex(item => item.name === itemName);

            if (existingItemIndex > -1) {
                cart[existingItemIndex].quantity++;
            } else {
                cart.push({ name: itemName, price: itemPrice, quantity: 1 });
            }
            updateCartDisplay();
            showToast('➕ Ítem añadido al carrito!');
        });
    });

    // Floating Cart Button click to open modal
    floatingCartBtn.addEventListener('click', () => {
        cartModal.style.display = 'flex'; // Use flex to center the modal
        updateCartDisplay(); // Ensure cart content is up-to-date when opening
    });

    // Close Modal Button
    closeButton.addEventListener('click', () => {
        cartModal.style.display = 'none';
    });

    // Close Modal when clicking outside the content
    window.addEventListener('click', (event) => {
        if (event.target === cartModal) {
            cartModal.style.display = 'none';
        }
    });

    // Clear Cart Button in Modal
    clearModalCartButton.addEventListener('click', () => {
        cart = [];
        updateCartDisplay();
        showToast('🗑️ Carrito vaciado.');
    });

    // Checkout Button in Modal (WhatsApp integration)
    checkoutModalButton.addEventListener('click', () => {
        if (cart.length === 0) {
            showToast('Tu carrito está vacío. ¡Añade algo antes de confirmar!');
            return;
        }

        showToast('Generando tu pedido para WhatsApp...');

        setTimeout(() => {
            let whatsappMessage = "¡Hola! Quisiera realizar el siguiente pedido de El Panze: \n\n";
            let totalOrderPrice = 0;

            cart.forEach(item => {
                whatsappMessage += `- ${item.name} x${item.quantity} (${formatPrice(item.price * item.quantity)})\n`;
                totalOrderPrice += item.price * item.quantity;
            });

            whatsappMessage += `\nTotal: ${formatPrice(totalOrderPrice)}\n`;
            whatsappMessage += `\n¡Gracias!`;

            const encodedMessage = encodeURIComponent(whatsappMessage);
            const phoneNumber = '+57 3107674031'; // Phone number for El Panze

            const whatsappURL = `https://wa.me/${phoneNumber}?text=${encodedMessage}`;

            window.open(whatsappURL, '_blank');

            // Clear cart after sending to WhatsApp
            cart = [];
            updateCartDisplay();
            cartModal.style.display = 'none'; // Close modal after order
        }, 1500); // Small delay to show toast
    });

    // Initial display update
    updateCartDisplay();
});