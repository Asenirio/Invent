"""
Inventory Management System (IMS) Core
A Python-based desktop application for managing products, contacts, and transactions
with automated backups and data visualization analytics.
"""

import sqlite3
import datetime
import shutil
import os
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Any, Union


# --- DATABASE SETUP ---


def init_db():
    """Initializes the SQLite database with products, transactions, contacts, and users tables."""
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()

    # Products Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        price REAL,
        stock_level INTEGER DEFAULT 0,
        unit TEXT,
        supplier_id INTEGER,
        FOREIGN KEY (supplier_id) REFERENCES contacts (id)
    )
    ''')

    # Migration: Add supplier_id if it doesn't exist
    cursor.execute("PRAGMA table_info(products)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'supplier_id' not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN supplier_id INTEGER")

    # Transactions Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        type TEXT, -- 'IN' or 'OUT'
        quantity INTEGER,
        date TEXT,
        remarks TEXT,
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    ''')

    # Contacts Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        type TEXT, -- 'SUPPLIER' or 'CUSTOMER'
        phone TEXT,
        email TEXT
    )
    ''')

    # Users Table for Auth
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    ''')

    # Default Admin User (admin / admin123)
    hashed_pw = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
        ('admin', hashed_pw, 'ADMIN')
    )

    # Seed Sample Products
    sample_products = [
        ('Gaming Laptop', 'Electronics', 1200.00, 10, 'pcs', 1),
        ('Wireless Mouse', 'Accessories', 25.00, 50, 'pcs', 1),
        ('Mechanical Keyboard', 'Accessories', 85.00, 4, 'pcs', 2),
        ('4K Monitor', 'Electronics', 350.00, 8, 'pcs', 2),
        ('USB-C Hub', 'Accessories', 45.00, 2, 'pcs', 1)
    ]
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO products (name, category, price, stock_level, unit, supplier_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            sample_products
        )

    # Seed Sample Contacts
    sample_contacts = [
        ('Tech Supply Co.', 'SUPPLIER', '555-0101', 'sales@techsupply.com'),
        ('Global Logistics', 'SUPPLIER', '555-0202', 'info@globallog.com'),
        ('John Doe', 'CUSTOMER', '555-0303', 'john@example.com'),
        ('Jane Smith', 'CUSTOMER', '555-0404', 'jane@test.com')
    ]
    cursor.execute("SELECT COUNT(*) FROM contacts")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO contacts (name, type, phone, email) VALUES (?, ?, ?, ?)",
            sample_contacts
        )

    # Seed Sample Transactions (for the chart)
    cursor.execute("SELECT COUNT(*) FROM transactions")
    if cursor.fetchone()[0] == 0:
        today = datetime.datetime.now()
        transactions = []
        for i in range(10):
            # Backdate some transactions
            date = (today - datetime.timedelta(days=i % 7)
                    ).strftime("%B, %d, %Y %I:%M%p")
            transactions.append((1, 'OUT', i + 1, date))
            transactions.append((2, 'IN', 20, date))

        cursor.executemany(
            "INSERT INTO transactions (product_id, type, quantity, date) VALUES (?, ?, ?, ?)",
            transactions
        )

    conn.commit()
    conn.close()

# --- THEME & STYLES ---


class LoginWindow:
    """Handles user authentication through a secure login screen."""

    def __init__(self, root_win, on_success):
        """Initializes the login window with its components."""
        self.root = root_win
        self.root.title("IMS Login")
        self.root.geometry("400x500")
        self.root.configure(bg="#121212")
        self.on_success = on_success

        self.bg_surface = "#1E1E1E"
        self.primary_color = "#BB86FC"
        self.text_color = "#E1E1E1"

        self.ent_user: Optional[tk.Entry] = None
        self.ent_pass: Optional[tk.Entry] = None

        self.init_ui()

    def init_ui(self):
        """Sets up the UI elements for the login screen."""
        container = tk.Frame(self.root, bg="#121212")
        container.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(container, text="WELCOME BACK", font=("Segoe UI", 20,
                 "bold"), bg="#121212", fg=self.primary_color).pack(pady=20)

        tk.Label(container, text="Username", bg="#121212",
                 fg="#888888").pack(anchor="w")
        ent_user = tk.Entry(container, bg=self.bg_surface, fg=self.text_color,
                                 bd=0, insertbackground="white", font=("Segoe UI", 12))
        ent_user.pack(pady=10, ipady=8, fill="x")
        self.ent_user = ent_user

        tk.Label(container, text="Password", bg="#121212",
                 fg="#888888").pack(anchor="w")
        ent_pass = tk.Entry(
            container, show="*", bg=self.bg_surface, fg=self.text_color,
            bd=0, insertbackground="white", font=("Segoe UI", 12)
        )
        ent_pass.pack(pady=10, ipady=8, fill="x")
        self.ent_pass = ent_pass

        btn_login = tk.Button(
            container, text="SIGN IN", command=self.login,
            bg=self.primary_color, fg="black", font=("Segoe UI", 12, "bold"),
            bd=0, cursor="hand2"
        )
        btn_login.pack(pady=30, ipady=10, fill="x")

    def login(self):
        """Validates credentials against the database and triggers the success callback."""
        ent_user = self.ent_user
        ent_pass = self.ent_pass
        if ent_user is None or ent_pass is None:
            return
        user = ent_user.get()
        pw = ent_pass.get()
        hashed = hashlib.sha256(pw.encode()).hexdigest()

        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?", (user, hashed))
        result = cursor.fetchone()
        conn.close()

        if result:
            self.on_success(user)
        else:
            messagebox.showerror("Auth Error", "Invalid Username or Password")


class InventoryApp:
    """Main Application class for the Inventory Management System."""

    def __init__(self, root_win, username):
        """Initializes the main application with user-specific context."""
        self.root = root_win
        self.username = username
        self.root.title(f"IMS CORE - Logged in as: {username}")
        self.root.geometry("1100x700")
        self.root.configure(bg="#121212")

        # UI Attributes
        self.sidebar: Optional[tk.Frame] = None
        self.content_area: Optional[tk.Frame] = None
        self.ent_search: Optional[tk.Entry] = None
        self.tree: Optional[ttk.Treeview] = None
        self.contact_tree: Optional[ttk.Treeview] = None
        self.selection_label: Optional[tk.Label] = None
        self.selected_pid: Optional[Union[int, str]] = None

        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Configure Colors
        self.primary_color = "#BB86FC"
        self.bg_dark = "#121212"
        self.bg_surface = "#1E1E1E"
        self.text_color = "#E1E1E1"

        self.setup_styles()
        self.init_ui()
        init_db()
        self.auto_backup()

    def auto_backup(self):
        """Creates a timestamped backup of the inventory database."""
        if not os.path.exists('backups'):
            os.makedirs('backups')

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            shutil.copy2('inventory.db',
                         f'backups/inventory_backup_{timestamp}.db')
            print(f"Backup created: backups/inventory_backup_{timestamp}.db")
        except (IOError, OSError) as e:
            print(f"Backup failed: {e}")

    def setup_styles(self):
        """Configures the visual styles and themes for the application widgets."""
        self.style.configure("Treeview",
                             background=self.bg_surface,
                             foreground=self.text_color,
                             fieldbackground=self.bg_surface,
                             rowheight=30
                             )
        self.style.map("Treeview", background=[
                       ('selected', self.primary_color)])

        self.style.configure("TFrame", background=self.bg_dark)
        self.style.configure("TLabel", background=self.bg_dark,
                             foreground=self.text_color, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=(
            "Segoe UI", 18, "bold"), foreground=self.primary_color)

        self.style.configure("TButton",
                             padding=10,
                             background=self.primary_color,
                             foreground="#000000",
                             font=("Segoe UI", 10, "bold")
                             )

    def init_ui(self):
        """Initializes the main user interface components (sidebar and content area)."""
        # Sidebar
        sidebar = tk.Frame(self.root, bg=self.bg_surface, width=220)
        sidebar.pack(side="left", fill="y")
        self.sidebar = sidebar

        lbl_title = tk.Label(self.sidebar, text="IMS CORE", font=(
            "Segoe UI", 16, "bold"), bg=self.bg_surface, fg=self.primary_color)
        lbl_title.pack(pady=30)

        btns = [
            ("Dashboard", self.show_dashboard),
            ("Inventory", self.show_inventory),
            ("Contacts", self.show_contacts),
            ("Stock In", lambda: self.show_transaction("IN")),
            ("Stock Out", lambda: self.show_transaction("OUT")),
            ("Reports", self.show_reports)
        ]

        for text, cmd in btns:
            btn = tk.Button(
                self.sidebar, text=text, command=cmd, bg=self.bg_surface,
                fg=self.text_color, bd=0, activebackground=self.primary_color,
                font=("Segoe UI", 11), anchor="w", padx=20
            )
            btn.pack(fill="x", pady=5)

        # Main Content Area
        content_area = tk.Frame(self.root, bg=self.bg_dark)
        content_area.pack(side="right", fill="both", expand=True)
        self.content_area = content_area

        self.show_dashboard()

    def clear_content(self):
        """Clears all widgets from the main content area."""
        content_area = self.content_area
        if content_area:
            for widget in content_area.winfo_children():
                widget.destroy()

    def show_dashboard(self):
        """Renders the main dashboard with statistics and sales charts."""
        self.clear_content()
        content_area = self.content_area
        if not content_area:
            return

        header = ttk.Label(content_area,
                           text="Business Overview", style="Header.TLabel")
        header.pack(pady=20, padx=20, anchor="w")

        # Stats Cards Container
        cards_frame = tk.Frame(content_area, bg=self.bg_dark)
        cards_frame.pack(fill="x", padx=20)

        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()

        # Queries for stats
        cursor.execute("SELECT COUNT(*) FROM products")
        total_products = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM products WHERE stock_level <= 5")
        low_stock = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM contacts WHERE type='SUPPLIER'")
        total_suppliers = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM contacts WHERE type='CUSTOMER'")
        total_customers = cursor.fetchone()[0]

        today_prefix = datetime.datetime.now().strftime("%B, %d, %Y") + "%"
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE date LIKE ?", (today_prefix,))
        today_tx = cursor.fetchone()[0]

        self.create_stat_card(cards_frame, "Total Products", str(total_products), 0)
        self.create_stat_card(cards_frame, "Low Stock Items", str(low_stock), 1)
        self.create_stat_card(cards_frame, "Suppliers", str(total_suppliers), 2)
        self.create_stat_card(cards_frame, "Customers", str(total_customers), 3)
        self.create_stat_card(cards_frame, "Today's Activity", str(today_tx), 4)

        # Recent Transactions Container
        recent_frame = tk.Frame(content_area, bg=self.bg_surface, padx=20, pady=20)
        recent_frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(recent_frame, text="Recent Activities", font=("Segoe UI", 12, "bold"), 
                 bg=self.bg_surface, fg=self.primary_color).pack(anchor="w", pady=(0, 10))

        cols = ("ID", "Type", "Quantity", "Date")
        tree = ttk.Treeview(recent_frame, columns=cols, show="headings", height=8)
        w_map = {"ID": 50, "Type": 80, "Quantity": 80, "Date": 220}
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=w_map.get(col, 100))
        tree.pack(fill="both", expand=True)

        cursor.execute("SELECT id, type, quantity, date FROM transactions ORDER BY id DESC LIMIT 8")
        for row in cursor.fetchall():
            tree.insert("", "end", values=row)

        conn.close()

    def create_stat_card(self, parent, title, value, col):
        """Creates a standardized statistic card for the dashboard."""
        card = tk.Frame(parent, bg=self.bg_surface, padx=20,
                        pady=20, bd=1, relief="flat")
        card.grid(row=0, column=col, padx=10, pady=10, sticky="nsew")

        lbl_title = tk.Label(card, text=title, bg=self.bg_surface,
                             fg="#AAAAAA", font=("Segoe UI", 10))
        lbl_title.pack(anchor="w")

        lbl_val = tk.Label(card, text=value, bg=self.bg_surface,
                           fg=self.primary_color, font=("Segoe UI", 24, "bold"))
        lbl_val.pack(anchor="w", pady=5)

    def show_inventory(self):
        """Displays the inventory management view with search and action buttons."""
        self.clear_content()
        header = ttk.Label(self.content_area,
                           text="Inventory Management", style="Header.TLabel")
        header.pack(pady=20, padx=20, anchor="w")

        # Toolbar
        toolbar = tk.Frame(self.content_area, bg=self.bg_dark)
        toolbar.pack(fill="x", padx=20, pady=10)

        btn_add = ttk.Button(toolbar, text="+ Add Product",
                             command=self.add_product_dialog)
        btn_add.pack(side="left", padx=5)

        tk.Label(toolbar, text="Search:", bg=self.bg_dark,
                 fg=self.text_color).pack(side="left", padx=(20, 5))
        ent_search = tk.Entry(
            toolbar, bg=self.bg_surface, fg=self.text_color, insertbackground="white")
        ent_search.pack(side="left", padx=5, fill="x", expand=True)
        ent_search.bind(
            "<KeyRelease>", lambda _: self.refresh_inventory_table())
        self.ent_search = ent_search

        # Table
        cols = ("ID", "Name", "Category", "Price", "Stock", "Unit", "Supplier")
        tree = ttk.Treeview(
            self.content_area, columns=cols, show="headings")
        w_map = {
            "ID": 50, "Name": 150, "Category": 100, "Price": 80,
            "Stock": 80, "Unit": 80, "Supplier": 150
        }
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=w_map.get(col, 100))
        tree.pack(fill="both", expand=True, padx=20, pady=10)
        self.tree = tree

        # Action Buttons
        action_frame = tk.Frame(self.content_area, bg=self.bg_dark)
        action_frame.pack(fill="x", padx=20, pady=5)

        btn_edit = ttk.Button(
            action_frame, text="Edit Selected", command=self.edit_product_dialog)
        btn_edit.pack(side="left", padx=5)

        btn_delete = tk.Button(
            action_frame, text="Delete Selected", command=self.delete_product,
            bg="#CF6679", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5
        )
        btn_delete.pack(side="left", padx=5)

        tk.Label(action_frame, text="|", bg=self.bg_dark,
                 fg="#444444").pack(side="left", padx=10)

        btn_stock_in = tk.Button(
            action_frame, text="Restock", command=lambda: self.quick_transaction("IN"),
            bg="#03DAC6", fg="black", font=("Segoe UI", 9, "bold"), bd=0, padx=15, pady=5
        )
        btn_stock_in.pack(side="left", padx=5)

        btn_stock_out = tk.Button(
            action_frame, text="Sale", command=lambda: self.quick_transaction("OUT"),
            bg=self.primary_color, fg="black", font=("Segoe UI", 9, "bold"), bd=0, padx=15, pady=5
        )
        btn_stock_out.pack(side="left", padx=5)

        self.refresh_inventory_table()

    def refresh_inventory_table(self):
        """Reloads the inventory treeview from the database based on search criteria."""
        tree = self.tree
        ent_search = self.ent_search
        if not tree:
            return
        for item in tree.get_children():
            tree.delete(item)

        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()

        search_term = f"%{ent_search.get()}%" if ent_search else "%%"
        cursor.execute(
            """SELECT p.id, p.name, p.category, p.price, p.stock_level, p.unit, c.name 
               FROM products p 
               LEFT JOIN contacts c ON p.supplier_id = c.id 
               WHERE p.name LIKE ? OR p.category LIKE ?""",
            (search_term, search_term)
        )
        for row in cursor.fetchall():
            tree.insert("", "end", values=row)
        conn.close()

    def show_contacts(self):
        """Displays the contact management view."""
        self.clear_content()
        header = ttk.Label(self.content_area,
                           text="Contact Management", style="Header.TLabel")
        header.pack(pady=20, padx=20, anchor="w")

        toolbar = tk.Frame(self.content_area, bg=self.bg_dark)
        toolbar.pack(fill="x", padx=20, pady=10)

        btn_add = ttk.Button(toolbar, text="+ Add Contact",
                             command=self.add_contact_dialog)
        btn_add.pack(side="left", padx=5)

        cols = ("ID", "Name", "Type", "Phone", "Email")
        contact_tree = ttk.Treeview(
            self.content_area, columns=cols, show="headings")
        for col in cols:
            contact_tree.heading(col, text=col)
        contact_tree.pack(fill="both", expand=True, padx=20, pady=10)
        self.contact_tree = contact_tree

        self.refresh_contact_table()

    def refresh_contact_table(self):
        """Reloads the contact treeview with all entries from the contacts table."""
        contact_tree = self.contact_tree
        if not contact_tree:
            return
        for item in contact_tree.get_children():
            contact_tree.delete(item)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contacts")
        for row in cursor.fetchall():
            contact_tree.insert("", "end", values=row)
        conn.close()

    def add_contact_dialog(self):
        """Opens a modal dialog to create a new contact (supplier or customer)."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Contact")
        dialog.geometry("400x500")
        dialog.configure(bg=self.bg_surface)

        fields = ["Name", "Type (SUPPLIER/CUSTOMER)", "Phone", "Email"]
        entries = {}

        for field in fields:
            tk.Label(dialog, text=field, bg=self.bg_surface,
                     fg=self.text_color).pack(pady=5)
            ent = tk.Entry(dialog, bg=self.bg_dark,
                           fg=self.text_color, insertbackground="white")
            ent.pack(pady=5, padx=20, fill="x")
            entries[field] = ent

        def save():
            """Gathers form data and saves it to the contacts table."""
            data = [entries[f].get() for f in fields]
            if data[0]:
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO contacts (name, type, phone, email) VALUES (?, ?, ?, ?)", data)
                conn.commit()
                conn.close()
                self.refresh_contact_table()
                dialog.destroy()

        tk.Button(dialog, text="Save Contact", command=save,
                  bg=self.primary_color, fg="black").pack(pady=20)

    def add_product_dialog(self):
        """Opens a modal dialog to add a new product to the inventory."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Product")
        dialog.geometry("400x500")
        dialog.configure(bg=self.bg_surface)

        tk.Label(dialog, text="Product Name", bg=self.bg_surface,
                 fg=self.text_color).pack(pady=5)
        ent_name = tk.Entry(dialog, bg=self.bg_dark,
                            fg=self.text_color, insertbackground="white")
        ent_name.pack(pady=5, padx=20, fill="x")

        tk.Label(dialog, text="Category", bg=self.bg_surface,
                 fg=self.text_color).pack(pady=5)
        ent_cat = tk.Entry(dialog, bg=self.bg_dark,
                           fg=self.text_color, insertbackground="white")
        ent_cat.pack(pady=5, padx=20, fill="x")

        tk.Label(dialog, text="Price", bg=self.bg_surface,
                 fg=self.text_color).pack(pady=5)
        ent_price = tk.Entry(dialog, bg=self.bg_dark,
                             fg=self.text_color, insertbackground="white")
        ent_price.pack(pady=5, padx=20, fill="x")

        tk.Label(dialog, text="Unit", bg=self.bg_surface,
                 fg=self.text_color).pack(pady=5)
        ent_unit = tk.Entry(dialog, bg=self.bg_dark,
                            fg=self.text_color, insertbackground="white")
        ent_unit.pack(pady=5, padx=20, fill="x")

        tk.Label(dialog, text="Supplier", bg=self.bg_surface,
                 fg=self.text_color).pack(pady=5)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM contacts WHERE type='SUPPLIER'")
        suppliers = cursor.fetchall()
        conn.close()

        supplier_map = {name: sid for sid, name in suppliers}
        supplier_names = list(supplier_map.keys())

        cb_supplier = ttk.Combobox(dialog, values=supplier_names, state="readonly")
        cb_supplier.pack(pady=5, padx=20, fill="x")

        def save():
            """Validates and inserts a new product record into the database."""
            name = ent_name.get()
            cat = ent_cat.get()
            price = ent_price.get()
            unit = ent_unit.get()
            supplier_name = cb_supplier.get()
            supplier_id = supplier_map.get(supplier_name)

            if name:
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO products (name, category, price, unit, supplier_id) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (name, cat, price, unit, supplier_id)
                )
                conn.commit()
                conn.close()
                self.refresh_inventory_table()
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Name is required")

        tk.Button(dialog, text="Save Product", command=save,
                  bg=self.primary_color, fg="black").pack(pady=20)

    def edit_product_dialog(self):
        """Opens a modal dialog to edit the currently selected product."""
        tree = self.tree
        if not tree:
            return
        selected = tree.selection()
        if not selected:
            messagebox.showwarning(
                "Selection", "Please select a product to edit"
            )
            return

        vals = tree.item(selected[0])['values']

        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Product")
        dialog.geometry("400x500")
        dialog.configure(bg=self.bg_surface)

        tk.Label(dialog, text="Product Name", bg=self.bg_surface,
                 fg=self.text_color).pack(pady=5)
        ent_name = tk.Entry(dialog, bg=self.bg_dark,
                            fg=self.text_color, insertbackground="white")
        ent_name.insert(0, vals[1])
        ent_name.pack(pady=5, padx=20, fill="x")

        tk.Label(dialog, text="Category", bg=self.bg_surface,
                 fg=self.text_color).pack(pady=5)
        ent_cat = tk.Entry(dialog, bg=self.bg_dark,
                           fg=self.text_color, insertbackground="white")
        ent_cat.insert(0, vals[2])
        ent_cat.pack(pady=5, padx=20, fill="x")

        tk.Label(dialog, text="Price", bg=self.bg_surface,
                 fg=self.text_color).pack(pady=5)
        ent_price = tk.Entry(dialog, bg=self.bg_dark,
                             fg=self.text_color, insertbackground="white")
        ent_price.insert(0, vals[3])
        ent_price.pack(pady=5, padx=20, fill="x")

        tk.Label(dialog, text="Unit", bg=self.bg_surface,
                 fg=self.text_color).pack(pady=5)
        ent_unit = tk.Entry(dialog, bg=self.bg_dark,
                            fg=self.text_color, insertbackground="white")
        ent_unit.insert(0, vals[5])
        ent_unit.pack(pady=5, padx=20, fill="x")

        tk.Label(dialog, text="Supplier", bg=self.bg_surface,
                 fg=self.text_color).pack(pady=5)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM contacts WHERE type='SUPPLIER'")
        suppliers = cursor.fetchall()
        conn.close()

        supplier_map = {name: sid for sid, name in suppliers}
        supplier_names = list(supplier_map.keys())

        cb_supplier = ttk.Combobox(dialog, values=supplier_names, state="readonly")
        cb_supplier.pack(pady=5, padx=20, fill="x")
        if vals[6]: # Set current supplier
            cb_supplier.set(vals[6])

        def update():
            """Collects updated product values and updates the database record."""
            name = ent_name.get()
            cat = ent_cat.get()
            price = ent_price.get()
            unit = ent_unit.get()
            supplier_name = cb_supplier.get()
            supplier_id = supplier_map.get(supplier_name)

            if name:
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                query = (
                    "UPDATE products SET name=?, category=?, price=?, "
                    "unit=?, supplier_id=? WHERE id=?"
                )
                cursor.execute(query, (name, cat, price, unit, supplier_id, vals[0]))
                conn.commit()
                conn.close()
                self.refresh_inventory_table()
                dialog.destroy()

        tk.Button(dialog, text="Update Product", command=update,
                  bg=self.primary_color, fg="black").pack(pady=20)

    def delete_product(self):
        """Deletes the selected product from the database after user confirmation."""
        tree = self.tree
        if not tree:
            return
        selected = tree.selection()
        if not selected:
            messagebox.showwarning(
                "Selection", "Please select a product to delete")
            return

        vals = tree.item(selected[0])['values']
        if messagebox.askyesno("Confirm", f"Delete {vals[1]}?"):
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id=?", (vals[0],))
            conn.commit()
            conn.close()
            self.refresh_inventory_table()

    def show_transaction(self, mode):
        """Displays the Stock In (IN) or Stock Out (OUT) transaction management form."""
        self.clear_content()
        title = "Restock (Stock In)" if mode == "IN" else "Sales (Stock Out)"
        header = ttk.Label(self.content_area, text=title,
                           style="Header.TLabel")
        header.pack(pady=20, padx=20, anchor="w")

        # Layout Container (Left for list, Right for form)
        main_container = tk.Frame(self.content_area, bg=self.bg_dark)
        main_container.pack(fill="both", expand=True, padx=20)

        # Left Column: Product Selection
        selection_frame = tk.Frame(main_container, bg=self.bg_dark, width=500)
        selection_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))

        tk.Label(selection_frame, text="Search Product:", bg=self.bg_dark,
                 fg=self.text_color).pack(anchor="w")
        ent_search = tk.Entry(selection_frame, bg=self.bg_surface,
                              fg=self.text_color, insertbackground="white")
        ent_search.pack(fill="x", pady=5)

        cols = ("ID", "Name", "Category", "Stock", "Supplier")
        tree = ttk.Treeview(selection_frame, columns=cols, show="headings", height=12)
        w_map = {"ID": 40, "Name": 150, "Category": 100, "Stock": 60, "Supplier": 150}
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=w_map.get(col, 100))
        tree.pack(fill="both", expand=True, pady=10)

        def refresh_list(_=None):
            """Refreshes the embedded product list based on search."""
            for item in tree.get_children():
                tree.delete(item)
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            term = f"%{ent_search.get()}%"
            cursor.execute(
                """SELECT p.id, p.name, p.category, p.stock_level, c.name 
                   FROM products p 
                   LEFT JOIN contacts c ON p.supplier_id = c.id 
                   WHERE p.name LIKE ? OR p.category LIKE ?""",
                (term, term)
            )
            for row in cursor.fetchall():
                item_node = tree.insert("", "end", values=row)
                if self.selected_pid and row[0] == self.selected_pid:
                    tree.selection_set(item_node)
                    tree.see(item_node)
            conn.close()

        ent_search.bind("<KeyRelease>", refresh_list)
        refresh_list()

        # Right Column: Transaction Details
        form_frame = tk.Frame(main_container, bg=self.bg_dark, width=300)
        form_frame.pack(side="right", fill="y")

        tk.Label(form_frame, text="Selected Product",
                 bg=self.bg_dark, fg=self.text_color).pack(anchor="w")

        selection_label = tk.Label(
            form_frame, text="None Selected", bg=self.bg_surface,
            fg=self.primary_color, font=("Segoe UI", 10, "italic"), pady=10
        )
        selection_label.pack(fill="x", pady=5)
        self.selection_label = selection_label

        self.selected_pid = None

        def on_tree_select(_):
            selected = tree.selection()
            if selected:
                vals = tree.item(selected[0])['values']
                self.selected_pid = vals[0]
                local_selection_label = self.selection_label
                if local_selection_label:
                    local_selection_label.config(
                        text=f"SELECTED:\n{vals[1]}\n(ID: {vals[0]})",
                        fg=self.primary_color
                    )

        tree.bind("<<TreeviewSelect>>", on_tree_select)

        tk.Label(form_frame, text="Quantity", bg=self.bg_dark,
                 fg=self.text_color).pack(anchor="w", pady=(10, 0))
        ent_qty = tk.Entry(form_frame, bg=self.bg_surface, fg=self.text_color, font=(
            "Segoe UI", 12), insertbackground="white")
        ent_qty.pack(fill="x", pady=5)

        def process():
            """Validates the transaction form and updates both stock and transaction history."""
            pid = self.selected_pid
            qty_str = ent_qty.get()
            if pid is not None and qty_str:
                try:
                    qty = int(qty_str)
                    conn = sqlite3.connect('inventory.db')
                    cursor = conn.cursor()

                    # Stock Validation for OUT
                    if mode == "OUT":
                        cursor.execute(
                            "SELECT stock_level FROM products WHERE id = ?", (pid,))
                        res = cursor.fetchone()
                        if res:
                            current_stock = res[0]
                            if current_stock < qty:
                                self.toast("Insufficient stock!", "error")
                                conn.close()
                                return
                        else:
                            self.toast("Product not found!", "error")
                            conn.close()
                            return

                    # Update Stock
                    if mode == "IN":
                        cursor.execute(
                            "UPDATE products SET stock_level = stock_level + ? WHERE id = ?",
                            (qty, pid)
                        )
                    else:
                        cursor.execute(
                            "UPDATE products SET stock_level = stock_level - ? WHERE id = ?",
                            (qty, pid)
                        )

                    # Record Transaction
                    timestamp = datetime.datetime.now().strftime("%B, %d, %Y %I:%M%p")
                    cursor.execute(
                        "INSERT INTO transactions (product_id, type, quantity, date) "
                        "VALUES (?, ?, ?, ?)", (pid, mode, qty, timestamp)
                    )

                    conn.commit()
                    conn.close()
                    self.toast(f"Transaction Success: {mode} {qty}", "success")
                    # Clear quantity but remain on page for "continuous" selection
                    ent_qty.delete(0, tk.END)
                    refresh_list() # Update stock in treeview
                except ValueError:
                    self.toast("Invalid Quantity", "error")
            else:
                self.toast("Select product and enter quantity", "error")

        btn_process = tk.Button(
            form_frame, text=f"Confirm {mode}", command=process,
            bg=self.primary_color, fg="black", font=("Segoe UI", 12, "bold"), pady=10
        )
        btn_process.pack(pady=30, fill="x")

    def select_product_dialog(self):
        """Deprecated: Logic moved into show_transaction directly."""

    def toast(self, message, msg_type="info"):
        """Displays a brief disappearing notification at the bottom of the screen."""
        if msg_type == "success":
            color = "#BB86FC"
        elif msg_type == "error":
            color = "#CF6679"
        else:
            color = "#03DAC6"

        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.configure(bg=color)

        # Position toast at bottom right
        x = self.root.winfo_x() + self.root.winfo_width() - 320
        y = self.root.winfo_y() + self.root.winfo_height() - 80
        toast.geometry(f"300x50+{x}+{y}")

        lbl = tk.Label(toast, text=message, bg=color,
                       fg="black", font=("Segoe UI", 10, "bold"))
        lbl.pack(expand=True, fill="both")

        self.root.after(3000, toast.destroy)

    def show_reports(self):
        """Renders the transaction reports log view."""
        self.clear_content()
        header = ttk.Label(self.content_area,
                           text="Transaction Logs", style="Header.TLabel")
        header.pack(pady=20, padx=20, anchor="w")

        cols = ("ID", "Prod ID", "Type", "Qty", "Date")
        tree = ttk.Treeview(self.content_area, columns=cols, show="headings")
        w_map = {"ID": 50, "Prod ID": 80, "Type": 80, "Qty": 80, "Date": 220}
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=w_map.get(col, 100))
        tree.pack(fill="both", expand=True, padx=20, pady=10)

        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, product_id, type, quantity, date FROM transactions ORDER BY id DESC")
        for row in cursor.fetchall():
            tree.insert("", "end", values=row)
        conn.close()

    def quick_transaction(self, mode):
        """Allows direct inventory stock-in/out from the inventory list with one click."""
        tree = self.tree
        if not tree:
            return
        selected = tree.selection()
        if not selected:
            messagebox.showwarning(
                "Selection", "Please select a product first"
            )
            return

        vals = tree.item(selected[0])['values']
        self.show_transaction(mode)
        # Pre-select the product
        self.selected_pid = vals[0]
        local_selection_label = self.selection_label
        if local_selection_label:
            local_selection_label.config(
                text=f"SELECTED: {vals[1]} (ID: {vals[0]})",
                fg=self.primary_color
            )


if __name__ == "__main__":
    init_db()
    main_root = tk.Tk()

    def launch_app(user_identity):
        """Closes the login screen and starts the main application interface."""
        for widget in main_root.winfo_children():
            widget.destroy()
        InventoryApp(main_root, user_identity)

    LoginWindow(main_root, launch_app)
    main_root.mainloop()
