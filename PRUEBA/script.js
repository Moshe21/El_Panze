/* script.js - carrito + modales + WA
   Asegúrate de enlazar este archivo desde index.html (ya está en el HTML provisto).
*/

document.addEventListener('DOMContentLoaded', () => {
  // Elementos UI
  const toggles = document.querySelectorAll('.category-toggle');
  const addBtns = document.querySelectorAll('.add-to-cart-btn');
  const floatingCartBtn = document.getElementById('floating-cart-btn');
  const cartModal = document.getElementById('cart-modal');
  const closeBtn = document.querySelector('.close-button');
  const modalCartList = document.getElementById('modal-cart-list');
  const modalCartTotal = document.getElementById('modal-cart-total');
  const cartCountEl = document.getElementById('cart-item-count');
  const clearModalBtn = document.getElementById('clear-modal-cart');
  const whatsappCheckoutBtn = document.getElementById('whatsapp-checkout-btn');

  const modal2 = document.getElementById('cart-modal_2');
  const closeBtn2 = document.querySelector('.close-button_2');
  const modal2Total = document.getElementById('modal-cart-total_2');
  const nequiBtn = document.getElementById('nequi-btn');
  const daviplataBtn = document.getElementById('daviplata-btn');
  const efectivoBtn = document.getElementById('efectivo-btn');

  const modal3 = document.getElementById('cart-modal_3');
  const closeBtn3 = document.querySelector('.close-button_3');
  const modal3Total = document.getElementById('modal-cart-total_3');
  const billInput = document.getElementById('bill-amount');
  const changeAmount = document.getElementById('change-amount');
  const confirmCashBtn = document.getElementById('confirm-cash-btn');

  const toastEl = document.getElementById('toast');
  const WHATSAPP_NUMBER = '573107674031'; // sin símbolos

  // Estado
  let cart = JSON.parse(localStorage.getItem('elpanze_cart') || '[]');

  // Funciones utilitarias
  const showToast = (msg) => {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    setTimeout(()=> toastEl.classList.remove('show'), 2500);
  };

  const formatPrice = (n) => {
    return '$' + n.toLocaleString('es-CO');
  };

  const calcTotal = () => cart.reduce((s,i)=> s + i.price * i.quantity, 0);

  const saveCart = () => localStorage.setItem('elpanze_cart', JSON.stringify(cart));

  // Render carrito
  function updateCartUI(){
    modalCartList.innerHTML = '';
    if(cart.length === 0){
      modalCartList.innerHTML = '<li style="text-align:center;color:#777;font-style:italic">Tu pedido está vacío.</li>';
    } else {
      cart.forEach((it, idx) => {
        const li = document.createElement('li');
        li.innerHTML = `<span>${it.name} x${it.quantity}</span>
                        <div>
                          <strong>${formatPrice(it.price * it.quantity)}</strong>
                          <button class="remove-item-from-modal" data-index="${idx}">✕</button>
                        </div>`;
        modalCartList.appendChild(li);
      });
    }

    const total = calcTotal();
    modalCartTotal.textContent = formatPrice(total);
    modal2Total.textContent = formatPrice(total);
    modal3Total.textContent = formatPrice(total);

    const qty = cart.reduce((s,i)=> s + i.quantity, 0);
    cartCountEl.textContent = qty;
    cartCountEl.style.display = qty > 0 ? 'inline-flex' : 'none';

    // listeners para eliminar
    document.querySelectorAll('.remove-item-from-modal').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const i = Number(e.target.dataset.index);
        if(cart[i].quantity > 1) cart[i].quantity--;
        else cart.splice(i,1);
        saveCart();
        updateCartUI();
        showToast('➖ Ítem eliminado');
      });
    });
  }

  // Añadir al carrito
  addBtns.forEach(b => {
    b.addEventListener('click', (e) => {
      const name = e.currentTarget.dataset.name;
      const price = Number(e.currentTarget.dataset.price);
      const idx = cart.findIndex(x => x.name === name);
      if(idx > -1) cart[idx].quantity++;
      else cart.push({ name, price, quantity: 1 });
      saveCart();
      updateCartUI();
      showToast('➕ Añadido: ' + name);
    });
  });

  // Toggle categorias (abrir/cerrar)
  toggles.forEach(t => {
    t.addEventListener('click', () => {
      const cat = t.dataset.category;
      const content = document.getElementById(`${cat}-content`);
      if(!content) return;
      content.classList.toggle('active');
      t.classList.toggle('active');
      // flecha simple
      const arrow = t.querySelector('.dropdown-arrow');
      if(content.classList.contains('active')) arrow.textContent = '▴';
      else arrow.textContent = '▾';
    });
  });

  // Abrir modal carrito
  floatingCartBtn.addEventListener('click', () => {
    cartModal.style.display = 'flex';
    updateCartUI();
  });

  closeBtn.addEventListener('click', ()=> cartModal.style.display = 'none');
  closeBtn2.addEventListener('click', ()=> modal2.style.display = 'none');
  closeBtn3.addEventListener('click', ()=> modal3.style.display = 'none');

  // Click fuera del modal cierra
  window.addEventListener('click', (ev) => {
    if(ev.target === cartModal) cartModal.style.display = 'none';
    if(ev.target === modal2) modal2.style.display = 'none';
    if(ev.target === modal3) modal3.style.display = 'none';
  });

  // Vaciar carrito
  clearModalBtn.addEventListener('click', () => {
    if(!confirm('¿Vaciar el pedido?')) return;
    cart = [];
    saveCart();
    updateCartUI();
    showToast('🗑️ Pedido vaciado');
  });

  // Confirmar -> abre modal 2 (pago)
  whatsappCheckoutBtn.addEventListener('click', () => {
    if(cart.length === 0){ showToast('Carrito vacío. Añade algo.'); return; }
    cartModal.style.display = 'none';
    modal2.style.display = 'flex';
    updateCartUI();
  });

  // Función para generar link WhatsApp
  function generateWhatsAppLink(paymentMethod, billAmount = null, change = null){
    const total = calcTotal();
    let message = '¡Hola! Quisiera hacer el siguiente pedido de El Panze:%0A%0A';
    cart.forEach(i => {
      message += `- ${i.name} x${i.quantity} (${formatPrice(i.price * i.quantity)})%0A`;
    });
    message += `%0ATotal: ${formatPrice(total)}%0A`;
    message += `Método de pago: ${paymentMethod}%0A`;
    if(paymentMethod === 'EFECTIVO' && billAmount !== null){
      message += `Paga con: ${formatPrice(billAmount)} - Cambio: ${formatPrice(change)}%0A`;
    }
    message += `%0AGracias!`;
    return `https://wa.me/${WHATSAPP_NUMBER}?text=${message}`;
  }

  // Pago Nequi
  nequiBtn.addEventListener('click', () => {
    if(cart.length === 0){ showToast('Carrito vacío'); return; }
    showToast('Generando pedido NEQUI...');
    const link = generateWhatsAppLink('NEQUI');
    setTimeout(()=> {
      window.open(link,'_blank');
      cart = []; saveCart(); updateCartUI();
      modal2.style.display = 'none';
    }, 900);
  });

  // Pago Daviplata
  daviplataBtn.addEventListener('click', () => {
    if(cart.length === 0){ showToast('Carrito vacío'); return; }
    showToast('Generando pedido DAVIPLATA...');
    const link = generateWhatsAppLink('DAVIPLATA');
    setTimeout(()=> {
      window.open(link,'_blank');
      cart = []; saveCart(); updateCartUI();
      modal2.style.display = 'none';
    }, 900);
  });

  // Pago efectivo -> abrir modal 3
  efectivoBtn.addEventListener('click', () => {
    modal2.style.display = 'none';
    modal3.style.display = 'flex';
    billInput.value = '';
    changeAmount.textContent = formatPrice(0);
    modal3Total.textContent = formatPrice(calcTotal());
  });

  // Calcular cambio al escribir
  billInput.addEventListener('input', () => {
    const val = Number(billInput.value || 0);
    const total = calcTotal();
    const change = (!isNaN(val) && val >= total) ? val - total : 0;
    changeAmount.textContent = formatPrice(change);
  });

  // Confirmar pago efectivo -> abrir WA con montos
  confirmCashBtn.addEventListener('click', () => {
    const val = Number(billInput.value || 0);
    const total = calcTotal();
    if(isNaN(val) || val < total){ showToast('Ingresa un monto igual o mayor al total'); return; }
    const change = val - total;
    showToast('Generando pedido EFECTIVO...');
    const link = generateWhatsAppLink('EFECTIVO', val, change);
    setTimeout(()=> {
      window.open(link,'_blank');
      cart = []; saveCart(); updateCartUI();
      modal3.style.display = 'none';
    }, 900);
  });

  // Inicial
  updateCartUI();
});
