import tkinter as tk
import db_manager
import ui_manager
import os

if __name__ == "__main__":
    if not os.path.exists("data"):
        os.makedirs("data")

    db_manager.create_tables()

    root = tk.Tk()
    ui_manager.POSApp(root)
    root.mainloop()
