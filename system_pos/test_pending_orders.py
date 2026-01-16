import unittest
import tkinter as tk
from unittest.mock import MagicMock, patch

import sys
sys.path.append('..')
from system_pos import ui_manager

class TestSavePendingOrderAndPendingOrdersModal(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Oculta la ventana principal
        self.app = MagicMock()
        self.app.root = self.root
        self.app.cart = {
            'Producto1': {'nombre': 'Producto1', 'precio': 1000, 'cantidad': 2},
            'Producto2': {'nombre': 'Producto2', 'precio': 500, 'cantidad': 1}
        }
        self.app.client = 'Cliente Test'
        self.app.address = 'Dirección Test'
        self.app.update_cart_display = MagicMock()
        self.app.calculate_total = MagicMock(return_value=2500)

    @patch('system_pos.ui_manager.db_manager.save_pending_order_db')
    @patch('system_pos.ui_manager.messagebox.showinfo')
    @patch('system_pos.ui_manager.messagebox.showwarning')
    def test_save_pending_order(self, mock_warning, mock_info, mock_save_db):
        # Simula el guardado de un pedido pendiente
        mock_save_db.return_value = 1
        um = ui_manager.POSApp(self.root)
        um.cart = self.app.cart.copy()
        um.root = self.root
        # Llama a la función y simula la interacción del usuario
        with patch('tkinter.ttk.Entry.get', return_value='PedidoTest'):
            um.save_pending_order('Cliente Test', 'Dirección Test', None)
        mock_save_db.assert_called()
        mock_info.assert_called()
        mock_warning.assert_not_called()

    @patch('system_pos.ui_manager.db_manager.get_all_pending_orders')
    @patch('system_pos.ui_manager.db_manager.get_pending_order_items')
    def test_pending_orders_modal_load_selected(self, mock_get_items, mock_get_orders):
        # Simula la carga de pedidos pendientes
        mock_get_orders.return_value = [
            (1, 'PedidoTest', 'Cliente Test', 'Dirección Test', '2026-01-08 12:00:00')
        ]
        mock_get_items.return_value = [
            ('Producto1', 1000, 2),
            ('Producto2', 500, 1)
        ]
        modal = ui_manager.PendingOrdersModal(self.root, self.app)
        modal.listbox.selection_set(0)
        with patch.object(ui_manager, 'PaymentMethodModal') as mock_payment_modal:
            modal.load_selected()
            mock_payment_modal.assert_called()
            self.assertEqual(self.app.cart['Producto1']['cantidad'], 2)
            self.assertEqual(self.app.client, 'Cliente Test')
            self.assertEqual(self.app.address, 'Dirección Test')

if __name__ == '__main__':
    unittest.main()
