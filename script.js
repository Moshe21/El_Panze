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
    const whatsappCheckoutButton = document.getElementById('whatsapp-checkout-btn'); // Renamed ID

    // Add new modal 1_2 elements
    const cartModal1_2 = document.getElementById('cart-modal_1_2');
    const closeButton1_2 = document.querySelector('.close-button_1_2');
    const modalCartTotalSpan1_2 = document.getElementById('modal-cart-total_1_2');
    const whatsappCheckoutBtn1_2 = document.getElementById('whatsapp-checkout-btn_1_2');
    const inputDireccion = document.getElementById("direccion-combo");
    const vistaDireccion = document.getElementById("direccion-confirmada");
    const textoDireccion = document.getElementById("direccion-texto");
    const btnCorregir = document.getElementById("btn-corregir");
    const checkoutBtn = document.getElementById("whatsapp-checkout-btn_1_2");


    // New modal 2 elements (payment options)
    const cartModal2 = document.getElementById('cart-modal_2');
    const closeButton2 = document.querySelector('.close-button_2');
    const modalCartTotalSpan2 = document.getElementById('modal-cart-total_2');
    const nequiBtn = document.getElementById('nequi-btn');
    const daviplataBtn = document.getElementById('daviplata-btn');
    const efectivoBtn = document.getElementById('efectivo-btn');

    // New modal 3 elements (cash payment)
    const cartModal3 = document.getElementById('cart-modal_3');
    const closeButton3 = document.querySelector('.close-button_3');
    const modalCartTotalSpan3 = document.getElementById('modal-cart-total_3');
    const billAmountInput = document.getElementById('bill-amount');
    const changeAmountSpan = document.getElementById('change-amount');
    const confirmCashBtn = document.getElementById('confirm-cash-btn');

    let cart = []; // Array to store cart items

    // --- Utility Functions ---

    function showToast(message) {
        let toast = document.getElementById('toast');
        if (!toast) {
            // Create toast element if it doesn't exist
            toast = document.createElement('div');
            toast.id = 'toast';
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.classList.add("show", "shake");
        setTimeout(() => {
            toast.classList.remove("show", "shake");
        }, 3000);
    }

    function formatPrice(price) {
        return `$${price.toLocaleString('es-CO')}`;
    }

    function calculateCartTotal() {
        let total = cart.reduce((total, item) => total + (item.price * item.quantity), 0);
   
        return total;
      }    
      function cost_domicilio (total){ 
        total = total+ 3000; 
         return total;
      }
    function updateCartDisplay() {
        modalCartList.innerHTML = '';
        let itemCount = 0;

        if (cart.length === 0) {
            const emptyMessageLi = document.createElement('li');
            emptyMessageLi.innerHTML = `<span style="font-style: italic; color: #888; text-align: center; width: 100%;">Tu pedido está vacío.</span>`;
            modalCartList.appendChild(emptyMessageLi);
        } else {
            // Display cart items
            cart.forEach((item, index) => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <span>${item.name} (x${item.quantity})</span>
                    <span>${formatPrice(item.price * item.quantity)}</span>
                    <button class="remove-item-from-modal" data-index="${index}">X</button>`;
                modalCartList.appendChild(li);
                itemCount += item.quantity;
            });

            // Add delivery charge line if applicable
            const direccionSelect = document.getElementById('direccion-select');
           
        }

        const total = calculateCartTotal();
        
        // Update all total displays
        modalCartTotalSpan.textContent = formatPrice(total);
        modalCartTotalSpan1_2.textContent = formatPrice(total);
        modalCartTotalSpan2.textContent = formatPrice(total);
        modalCartTotalSpan3.textContent = formatPrice(total);
        
        // Update cart badge
        cartItemCountSpan.textContent = itemCount;
        cartItemCountSpan.style.display = itemCount > 0 ? 'flex' : 'none';
        
        // Re-attach event listeners for remove buttons
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

    function generateWhatsAppMessage(paymentMethod, billAmount = null, change = null) {
        
        const direccion = document.getElementById("direccion-combo").value;
        
        let whatsappMessage = "¡Hola! Quisiera realizar el siguiente pedido de El Panze: \n\n";
        let totalOrderPrice = calculateCartTotal();

        cart.forEach(item => {
            whatsappMessage += `- ${item.name} x${item.quantity} (${formatPrice(item.price * item.quantity)})\n`;
        });
        whatsappMessage += `\nConjunto / Zona: ${direccion}\n`;
        whatsappMessage += `\nTotal: ${formatPrice(totalOrderPrice)}\n`;
        whatsappMessage += `Método de pago elegido: ${paymentMethod}\n`;

        if (paymentMethod === 'EFECTIVO' && billAmount !== null && change !== null) {
            whatsappMessage += `Monto con el que paga: ${formatPrice(billAmount)}\n`;
            whatsappMessage += `Cambio a devolver: ${formatPrice(change)}\n`;
        }
        
        whatsappMessage += `\n¡Gracias!`;

        const encodedMessage = encodeURIComponent(whatsappMessage);
        const phoneNumber = '573107674031'; // Phone number for El Panze

        return `https://wa.me/${phoneNumber}?text=${encodedMessage}`;
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
            showToast('➕ ¡Ítem añadido al carrito!');
        });
    });

    // Floating Cart Button click to open modal
    floatingCartBtn.addEventListener('click', () => {
        cartModal.style.display = 'flex'; // Use flex to center the modal
        updateCartDisplay(); // Ensure cart content is up-to-date when opening
    });

    // Close Modal 1 Button
    closeButton.addEventListener('click', () => {
        cartModal.style.display = 'none';
    });

    // Close Modal 1 when clicking outside the content
    window.addEventListener('click', (event) => {
        if (event.target === cartModal) {
            cartModal.style.display = 'none';
        }
    });

    // Clear Cart Button in Modal 1
    clearModalCartButton.addEventListener('click', () => {
        cart = [];
        updateCartDisplay();
        showToast('🗑️ Carrito vaciado.');
    });

    // Confirm Order Button (now opens payment modal)
    whatsappCheckoutButton.addEventListener('click', () => {
        if (cart.length === 0) {
            showToast('Tu carrito está vacío. ¡Añade algo antes de confirmar!');
            return;
        }
        cartModal.style.display = 'none'; // Close the first modal
        cartModal1_2.style.display = 'flex'; // Open the second modal
        updateCartDisplay(); // Update total in the second modal
    });

    // --- Modal 1.2 address ---
    // Close Modal 1_2 Button
    closeButton1_2.addEventListener('click', () => {
    cartModal1_2.style.display = 'none';
    });
    // Close Modal 1_2 when clicking outside the content
    window.addEventListener('click', (event) => {
        if (event.target === cartModal1_2) {
            cartModal1_2.style.display = 'none';
        }
    });
   
    const direccionesPermitidas = [
    "Batará","Aracari","Milano","Ibis","Amazilia","Jilguero","Alondra","Tángara","Andaríos","Frontino",
    "Sie 1","Sie 2","Sie 3","Sie 4",
    "Torre de San Juan 1B","Torre de San Juan 2B","Torre de San Juan 3B","Torre de San Juan 4B","Torre de San Juan 5B",
    "Torre de San Juan 6B","Torre de San Juan 7B","Torre de San Juan 8B","Torre de San Juan 9B","Torre de San Juan 10B",
    "Torre de San Juan 11B","Torre de San Juan 12B","Torre de San Juan 13B","Torre de San Juan 14B","Torre de San Juan 15B",
    "Torre de San Juan 16B","Torre de San Juan 17B","Torre de San Juan 18B","Torre de San Juan 19B","Torre de San Juan 20B",
    "Torre de San Juan 21B","Torre de San Juan 22B","Torre de San Juan 23B","Torre de San Juan 24B","Torre de San Juan 25B",
    "Torre de San Juan 26B","Torre de San Juan 27B","Torre de San Juan 28B","Torre de San Juan 29B","Torre de San Juan 30B",
    "Torre de San Juan 31B","Torre de San Juan 32B","Torre de San Juan 33B","Torre de San Juan 34B","Torre de San Juan 35B",
    "Torre de San Juan 36B","Torre de San Juan 37B","Torre de San Juan 38B"
    ];

    // desactivar confirmación al inicio
    checkoutBtn.disabled = true;
    checkoutBtn.classList.remove("active");
    
    // cuando elige dirección
    inputDireccion.addEventListener("change", () => {
        const direccion = inputDireccion.value.trim();
        if (direccion !== "") {
           
            const direccion = inputDireccion.value.trim();
            textoDireccion.textContent = direccion;
            vistaDireccion.style.display = "block";
            document.querySelector(".combo-container").style.display = "none";

            checkoutBtn.disabled = false;
            checkoutBtn.classList.add("active");
             if (!direccionesPermitidas.includes(direccion)) {
                showToast('🏢 el costo envío es $3.000 ');
                cost_domicilio(total);
                // agregar cargo de envío al total
                
            }
            whatsappCheckoutBtn1_2.addEventListener('click', () => {
                showToast('🏢Dirección seleccionada: ' + direccion);
                cartModal1_2.style.display = 'none'; // Close modal 1_2
                cartModal2.style.display = 'flex'; // Open modal 2
                updateCartDisplay();
            });
        }     
    });
    // Botón corregir → vuelve a mostrar el select
    btnCorregir.addEventListener("click", () => {
        vistaDireccion.style.display = "none";
        document.querySelector(".combo-container").style.display = "block";

        textoDireccion.textContent = direccion;
            vistaDireccion.style.display = "block";
            document.querySelector(".combo-container").style.display = "none";

            
            checkoutBtn.disabled = true;
            checkoutBtn.classList.remove("active");
        
    });
    // Validación al intentar confirmar sin dirección
    checkoutBtn.addEventListener("click", function (e) {
        const direccion = inputDireccion.value.trim();

        if (direccion === "") {
            e.preventDefault();
            showToast('🏢 Por favor seleccionar una dirección');
            return;
        }
    });
    

    // --- Modal 2 Event Listeners (Payment Options) ---

    // Close Modal 2 Button
    closeButton2.addEventListener('click', () => {
    cartModal2.style.display = 'none';
    });

    // Close Modal 2 when clicking outside the content
    window.addEventListener('click', (event) => {
        if (event.target === cartModal2) {
            cartModal2.style.display = 'none';
        }
    });

    // Nequi Button Opens Modal 3
    nequiBtn.addEventListener('click', () => {
        showToast('Has seleccionado NEQUI. Generando pedido...');
        const whatsappURL = generateWhatsAppMessage('NEQUI');
        setTimeout(() => {
            window.open(whatsappURL, '_blank');
            cart = []; // Clear cart after sending to WhatsApp
            updateCartDisplay();
            cartModal2.style.display = 'none'; // Close modal after order
        }, 1500);
    });

    // Daviplata Button Opens Modal 3
    daviplataBtn.addEventListener('click', () => {
        showToast('Has seleccionado DAVIPLATA. Generando pedido...');
        const whatsappURL = generateWhatsAppMessage('DAVIPLATA');
        setTimeout(() => {
            window.open(whatsappURL, '_blank');
            cart = []; // Clear cart after sending to WhatsApp
            updateCartDisplay();
            cartModal2.style.display = 'none'; // Close modal after order
        }, 1500);
    });

    // Efectivo Button - Opens Modal 3
    efectivoBtn.addEventListener('click', () => {
        cartModal2.style.display = 'none'; // Close current modal
        cartModal3.style.display = 'flex'; // Open the cash modal
        billAmountInput.value = ''; // Clear previous input
        changeAmountSpan.textContent = formatPrice(0); // Reset change display
        modalCartTotalSpan3.textContent = formatPrice(calculateCartTotal()); // Ensure total is updated
    });

    // --- Modal 3 Event Listeners (Cash Payment) ---

    // Close Modal 3 Button
    closeButton3.addEventListener('click', () => {
        cartModal3.style.display = 'none';
    });

    // Close Modal 3 when clicking outside the content
    window.addEventListener('click', (event) => {
        if (event.target === cartModal3) {
            cartModal3.style.display = 'none';
        }
    });

    // Calculate change as user types
    billAmountInput.addEventListener('input', () => {
        const billAmount = parseFloat(billAmountInput.value);
        const total = calculateCartTotal();
        let change = 0;

        if (!isNaN(billAmount) && billAmount >= total) {
            change = billAmount - total;
        }
        changeAmountSpan.textContent = formatPrice(change);
    });

    // Confirm Cash Button
    confirmCashBtn.addEventListener('click', () => {
        const billAmount = parseFloat(billAmountInput.value);
        const total = calculateCartTotal();

        if (isNaN(billAmount) || billAmount < total) {
            showToast('Por favor, ingresa un monto válido igual o mayor al total.');
            return;
        }

        const change = billAmount - total;
        showToast(`Pago en EFECTIVO. Cambio: ${formatPrice(change)}. Generando pedido...`);
        const whatsappURL = generateWhatsAppMessage('EFECTIVO', billAmount, change);
        
        setTimeout(() => {
            window.open(whatsappURL, '_blank');
            cart = []; // Clear cart after sending to WhatsApp
            updateCartDisplay();
            cartModal3.style.display = 'none'; // Close modal after order
        }, 1500);
    });


    // Initial display update
    updateCartDisplay();
});