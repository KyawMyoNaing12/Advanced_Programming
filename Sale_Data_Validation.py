import datetime
import csv
import io
import re
import urllib.request
import json
import uuid  # Local fallback for UUID generation
import ftplib  # Built-in library to connect to FTP servers
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox


# ==========================================
# SINGLETON FTP MANAGER
# ==========================================
class FTPManager:
    """Singleton class managing a single active FTP connection across the application."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FTPManager, cls).__new__(cls)
            cls._instance.ftp_client = None
            cls._instance.server = ""
        return cls._instance

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls()
        return cls._instance

    def connect(self, server, user, password, timeout=5):
        """Connects to the specified FTP server."""
        self.disconnect()  # Ensure any existing connection is closed first
        self.ftp_client = ftplib.FTP(server, timeout=timeout)
        self.ftp_client.login(user=user, passwd=password)
        self.server = server
        return self.ftp_client

    def disconnect(self):
        """Safely disconnects from the FTP server."""
        if self.ftp_client:
            try:
                self.ftp_client.quit()
            except Exception:
                pass
            self.ftp_client = None
            self.server = ""

    def is_connected(self):
        """Returns True if an active FTP client connection exists."""
        return self.ftp_client is not None

    def get_client(self):
        """Returns the active ftplib.FTP instance."""
        return self.ftp_client


class FileProcessor:
    """Helper class to handle the classification and storage categorization of files"""
    def __init__(self):
        self.default_files = []  # Stores successfully processed non-error files
        self.error_logs = []     # Stores files that failed validation along with their error reason

    def add_default_file(self, filename):
        if filename not in self.default_files:
            self.default_files.append(filename)

    def add_error_log(self, filename, error_message):
        # Store as a tuple of (filename, error_reason, timestamp)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.error_logs.append((filename, error_message, timestamp))


class SalesDataApp(tk.Tk):
    """Main Application Window using pure Tkinter"""
    def __init__(self):
        super().__init__()
        
        self.title("Sales Data Validation System - Secure CSV Management")
        self.geometry("1150x850")
        self.configure(bg="#F0F4F8")  # Soft light grey/blue background
        
        # Instantiate Singleton FTP Manager
        self.ftp_manager = FTPManager.get_instance()
        
        # Instantiate our OOP FileProcessor
        self.processor = FileProcessor()
        
        # Initialize custom styles for Treeview & Notebook
        self.setup_styles()
        
        # 1. Menu Bar
        self.create_menu_bar()
        
        # 2. Top Header / App Banner
        self.header = HeaderPanel(self)
        self.header.pack(fill="x", padx=10, pady=5)
        
        # 3. FTP Connection Panel
        self.connection_panel = ConnectionPanel(self)
        self.connection_panel.pack(fill="x", padx=10, pady=5)
        
        # Main Splitter Frame (Holds Left and Right panels)
        self.content_frame = tk.Frame(self, bg="#F0F4F8")
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 4. Left Panel (CSV Files)
        self.file_panel = FilePanel(self.content_frame, self)
        self.file_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # 5. Right Panel (Activity Logs)
        self.log_panel = LogPanel(self.content_frame)
        self.log_panel.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        # 6. Bottom Status Bar
        self.status_bar = StatusBar(self)
        self.status_bar.pack(fill="x", side="bottom", padx=10, pady=10)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")  # Allows for clean styling of tabs and tables
        
        # Style Treeview (Tables)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#EEEEEE")
        style.configure("Treeview", rowheight=25, font=("Segoe UI", 10))
        
        # Style Notebook (Tabs)
        style.configure("TNotebook", background="white")
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[12, 4])
        style.map("TNotebook.Tab", background=[("selected", "#0A4D9A")], foreground=[("selected", "white")])

    def create_menu_bar(self):
        menubar = tk.Menu(self)
        for menu_name in ["File", "Connection", "File Operations", "Validation", "Processing", "Reports", "Tools", "Help"]:
            new_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label=menu_name, menu=new_menu)
        self.config(menu=menubar)

    def log_message(self, log_type, message):
        """Helper function to print logs directly to your UI's Log Panel"""
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_panel.log_table.insert("", "end", values=(now, log_type, message))


class HeaderPanel(tk.Frame):
    """Blue header bar with system title and system icon/status"""
    def __init__(self, parent):
        super().__init__(parent, bg="#0A4D9A", height=60)
        self.pack_propagate(False)
        
        self.title_label = tk.Label(
            self, text="Sales Data Validation System", 
            font=("Segoe UI", 18, "bold"), fg="white", bg="#0A4D9A"
        )
        self.title_label.pack(side="left", padx=15, pady=10)
        
        self.subtitle_label = tk.Label(
            self, text="Secure CSV Management", 
            font=("Segoe UI", 10, "italic"), fg="#A9CCE3", bg="#0A4D9A"
        )
        self.subtitle_label.pack(side="left", padx=(5, 0), pady=(18, 0))
        
        self.status_indicator = tk.Label(
            self, text="● Idle  ", fg="#2ECC71", bg="#0A4D9A", font=("Segoe UI", 12, "bold")
        )
        self.status_indicator.pack(side="right", padx=15)


class ConnectionPanel(tk.LabelFrame):
    """FTP Server Connection Configurations Panel utilizing FTPManager Singleton"""
    def __init__(self, parent):
        super().__init__(
            parent, text=" FTP Server Connection ", 
            font=("Segoe UI", 11, "bold"), fg="green", bg="#EBF5FB", bd=1, relief="solid"
        )
        self.parent = parent
        self.ftp_manager = FTPManager.get_instance()
        
        self.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)
        
        tk.Label(self, text="Server:", bg="#EBF5FB", font=("Segoe UI", 10)).grid(row=0, column=0, padx=5, pady=15, sticky="e")
        self.ent_server = tk.Entry(self, font=("Segoe UI", 10), width=18)
        self.ent_server.insert(0, "127.0.0.1")
        self.ent_server.grid(row=0, column=1, padx=5, sticky="w")
        
        tk.Label(self, text="Username:", bg="#EBF5FB", font=("Segoe UI", 10)).grid(row=0, column=2, padx=5, pady=15, sticky="e")
        self.ent_user = tk.Entry(self, font=("Segoe UI", 10), width=18)
        self.ent_user.insert(0, "kmn")
        self.ent_user.grid(row=0, column=3, padx=5, sticky="w")
        
        tk.Label(self, text="Password:", bg="#EBF5FB", font=("Segoe UI", 10)).grid(row=0, column=4, padx=5, pady=15, sticky="e")
        self.ent_pass = tk.Entry(self, show="●", font=("Segoe UI", 10), width=18)
        self.ent_pass.insert(0, "123")
        self.ent_pass.grid(row=0, column=5, padx=5, sticky="w")
        
        self.btn_connect = tk.Button(
            self, text="Connect", bg="#27AE60", fg="white", activebackground="#2196F3",
            font=("Segoe UI", 10, "bold"), bd=0, padx=12, pady=4, cursor="hand2",
            command=self.connect_to_xampp_ftp
        )
        self.btn_connect.grid(row=0, column=6, padx=5)
        
        self.btn_disconnect = tk.Button(
            self, text="Disconnect", bg="#D9534F", fg="white", activebackground="#C0392B",
            font=("Segoe UI", 10, "bold"), bd=0, padx=12, pady=4, cursor="hand2",
            command=self.disconnect_from_ftp
        )
        self.btn_disconnect.grid(row=0, column=7, padx=5)

    def connect_to_xampp_ftp(self):
        server = self.ent_server.get().strip()
        user = self.ent_user.get().strip()
        password = self.ent_pass.get()

        if not server:
            messagebox.showwarning("Warning", "Please enter an FTP Server IP address.")
            return

        try:
            self.parent.log_message("System", f"Attempting to connect to FTP server at {server}...")
            
            # Delegate connection logic to Singleton FTPManager
            self.ftp_manager.connect(server, user, password, timeout=5)
            
            self.parent.header.status_indicator.config(text="● Connected", fg="#2ECC71")
            self.parent.status_bar.lbl_status.config(text=f"Status : Connected to {server}")
            self.parent.log_message("Success", "FTP Connection established successfully!")
            
            self.parent.file_panel.refresh_file_list()
            
        except Exception as e:
            self.parent.log_message("Error", f"Connection failed: {str(e)}")
            messagebox.showerror("XAMPP Connection Error", f"Could not connect to the local FTP server.\nError: {e}")

    def disconnect_from_ftp(self):
        if self.ftp_manager.is_connected():
            self.ftp_manager.disconnect()
            self.parent.header.status_indicator.config(text="● Idle  ", fg="#E74C3C")
            self.parent.status_bar.lbl_status.config(text="Status : Disconnected")
            self.parent.file_panel.clear_file_list()
            self.parent.file_panel.all_files.clear()  # Clear memory cache
            self.parent.log_message("System", "Disconnected from FTP Server.")
        else:
            messagebox.showinfo("Status", "No active connection is currently running.")


class FilePanel(tk.Frame):
    """Left Panel: Contains local file search, standard list box, and batch controls"""
    def __init__(self, parent, app):
        super().__init__(parent, bg="white", highlightbackground="#AED6F1", highlightthickness=1)
        self.app = app
        self.ftp_manager = FTPManager.get_instance()
        
        # Array to cache mock files loaded initially
        self.all_files = []
        
        # Title Label
        tk.Label(
            self, text="📂 Server Files Directory", bg="white", fg="#0A4D9A", font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=10, pady=8)
        
        # Search Layout Frame
        search_frame = tk.Frame(self, bg="white")
        search_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(search_frame, text="Search :", bg="white", font=("Segoe UI", 10)).pack(side="left", padx=(0,5))
        self.ent_search = tk.Entry(search_frame, font=("Segoe UI", 10))
        self.ent_search.pack(side="left", fill="x", expand=True, padx=5)
        
        # Search Action Button
        self.btn_search = tk.Button(
            search_frame, text="Search", bg="#2980B9", fg="white", font=("Segoe UI", 9, "bold"),
            bd=1, relief="solid", padx=10, command=self.execute_search
        )
        self.btn_search.pack(side="left", padx=2)
        
        # Clear Button
        self.btn_clear = tk.Button(
            search_frame, text="Clear", bg="#E0E0E0", font=("Segoe UI", 9),
            bd=1, relief="solid", padx=10, command=self.clear_search
        )
        self.btn_clear.pack(side="left", padx=2)
        
        # File Treeview Wrapper
        tree_frame = tk.Frame(self, bg="white")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.file_tree = ttk.Treeview(tree_frame, columns=("Filename"), show="headings", selectmode="browse")
        self.file_tree.heading("Filename", text="Available Files:", anchor="w")
        self.file_tree.column("Filename", stretch=True)
        self.file_tree.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        
        # Initially populate treeview with our default mock values
        self.populate_treeview(self.all_files)
      
        # Operational row buttons
        btn_row = tk.Frame(self, bg="white")
        btn_row.pack(fill="x", pady=15, padx=10)
        
        def create_action_btn(parent, text, color):
            return tk.Button(
                parent, text=text, bg=color, fg="white", bd=0, 
                font=("Segoe UI", 9, "bold"), padx=8, pady=6, cursor="hand2"
            )
            
        self.btn_validate = create_action_btn(btn_row, "Validate", "#2980B9")
        self.btn_validate.pack(side="left", expand=True, fill="x", padx=2)
        self.btn_validate.config(command=self.validate_selected_file)
        
        self.btn_process = create_action_btn(btn_row, "Process", "#8E44AD")
        self.btn_process.pack(side="left", expand=True, fill="x", padx=2)
        self.btn_process.config(command=self.process_selected_file) 
                    
        self.btn_refresh = create_action_btn(btn_row, "Refresh", "#16A085")
        self.btn_refresh.pack(side="left", expand=True, fill="x", padx=2)
        self.btn_refresh.config(command=self.refresh_file_list)

    def populate_treeview(self, file_list):
        """Helper to dump a targeted list array into the GUI Treeview list box"""
        self.clear_file_list()
        for f in file_list:
            self.file_tree.insert("", "end", values=(f,))

    def execute_search(self):
        """Validates search input, prompts error box if missing, filters view if found"""
        query = self.ent_search.get().strip().lower()
        
        if not query:
            messagebox.showwarning("Search Warning", "Please type a file name keyword to search.")
            return
            
        # Match matches anywhere in the file name
        matching_files = [f for f in self.all_files if query in f.lower()]
        
        if not matching_files:
            # File is NOT found -> Show Error Box
            messagebox.showerror("Error", "Not exist file")
            self.app.log_message("Warning", f"Search failed for key: '{query}' - File not found.")
        else:
            # File IS found -> Filter the Treeview to show matches
            self.populate_treeview(matching_files)
            self.app.log_message("Search", f"Found {len(matching_files)} matching file(s) for keyword: '{query}'")

    def clear_search(self):
        """Resets search string box and brings back entire base directory list view"""
        self.ent_search.delete(0, tk.END)
        self.populate_treeview(self.all_files)

    def refresh_file_list(self):
        """Reads ALL file directory listings (regardless of format) from the FTP server"""
        if not self.ftp_manager.is_connected():
            self.all_files = []
            self.populate_treeview(self.all_files)
            return

        try:
            raw_files = []
            client = self.ftp_manager.get_client()
            client.retrlines('NLST', raw_files.append)
            
            # Filter out folder structures if visible inside your tree view
            self.all_files = [f for f in raw_files if f not in ("main", "errors", ".", "..")]
            self.populate_treeview(self.all_files)
            self.app.log_message("System", f"Loaded {len(self.all_files)} files from Server directory.")
                
        except Exception as e:
            self.app.log_message("Error", f"Failed to retrieve files: {str(e)}")

    def clear_file_list(self):
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

    # ==========================================
    # CORE VALIDATION & PROCESSING LOGIC
    # ==========================================
    def validate_selected_file(self, silent=False):
        """
        Validates the selected file.
        Returns: (bool, str) -> (is_valid, error_message)
        """
        selected_item = self.file_tree.selection()
        if not selected_item:
            if not silent:
                messagebox.showwarning("Validation Warning", "Please select a file from the list to validate.")
            return False, "No file selected"

        filename = self.file_tree.item(selected_item, "values")[0]
        if not silent:
            self.app.log_message("Validation", f"Starting evaluation for: {filename}")

        # Rule 1: Validate Filename Structure via Regex
        pattern = r"^SALES_DATA_\d{14}\.csv$"
        if not re.match(pattern, filename):
            msg = f"Rejected: Incorrectly formatted filename or unsupported file extension '{filename}'."
            if not silent:
                self.app.log_message("Rejected", msg)
                messagebox.showerror("Validation Failed", msg)
            return False, msg

        # Check FTP connection availability
        if not self.ftp_manager.is_connected():
            msg = "FTP connection is inactive."
            if not silent:
                self.app.log_message("System", "Cannot validate. Offline state active.")
                messagebox.showinfo("Simulated State", "Connect to a real live local FTP server.")
            return False, msg

        # Download and read raw contents
        try:
            memory_stream = io.BytesIO()
            client = self.ftp_manager.get_client()
            client.retrbinary(f"RETR {filename}", memory_stream.write)
            file_bytes = memory_stream.getvalue()
            
            # Rule 2: Empty 0-byte structural check
            if len(file_bytes) == 0:
                msg = f"Rejected: File '{filename}' is empty (0-byte size)."
                if not silent:
                    self.app.log_message("Rejected", msg)
                    messagebox.showerror("Validation Failed", msg)
                return False, msg

            text_data = file_bytes.decode('utf-8')
            
        except Exception as e:
            msg = f"Rejected: Decoding/FTP error - {str(e)}"
            if not silent:
                self.app.log_message("Rejected", msg)
                messagebox.showerror("Validation Failed", msg)
            return False, msg

        # Structural Row/Cell Analysis
        return self._evaluate_content_rules(filename, text_data, silent)

    def _evaluate_content_rules(self, filename, text_content, silent):
        expected_headers = [
            "transaction_id", "timestamp", "store_id", "product_id",
            "quantity", "unit_price", "total_amount", "payment_method"
        ]
        
        try:
            reader = csv.reader(io.StringIO(text_content))
            rows = list(reader)
            
            if not rows or len(rows) < 1:
                raise ValueError("No header sequence matrix found.")

            actual_headers = rows[0]
            if actual_headers != expected_headers:
                raise ValueError("Missing or incorrectly named headers.")

            transaction_ids = set()
            
            for idx, row in enumerate(rows[1:], start=2):
                if len(row) != len(expected_headers):
                    raise ValueError(f"Line {idx}: Column constraint mismatch.")

                tx_id, timestamp, store_id, prod_id, qty_str, price_str, total_str, pay_method = row

                if not all(field.strip() for field in row):
                    raise ValueError(f"Line {idx}: Empty cell value discovered.")

                if tx_id in transaction_ids:
                    raise ValueError(f"Line {idx}: Duplicate transaction_id '{tx_id}'.")
                transaction_ids.add(tx_id)

                try:
                    quantity = float(qty_str)
                    unit_price = float(price_str)
                    total_amount = float(total_str)
                except ValueError:
                    raise ValueError(f"Line {idx}: Non-numeric quantity/price/total values.")

                if quantity <= 0 or unit_price <= 0 or total_amount <= 0:
                    raise ValueError(f"Line {idx}: Values must contain valid positive numbers.")

                if abs((quantity * unit_price) - total_amount) > 0.01:
                    raise ValueError(f"Line {idx}: total_amount does not match calculation.")

            if not silent:
                self.app.log_message("Success", f"File '{filename}' validated successfully!")
                messagebox.showinfo("Validation Success", f"File '{filename}' Successfully validated.")
            return True, "Passed"

        except ValueError as err:
            if not silent:
                self.app.log_message("Rejected", f"Rejected: {str(err)}")
                messagebox.showerror("Validation Failed", f"Rejected: {str(err)}")
            return False, str(err)

    def _ensure_ftp_directory(self, folder_name):
        """Ensures that the directory folder_name exists on the FTP server."""
        client = self.ftp_manager.get_client()
        if not client:
            return
        try:
            client.cwd(folder_name)
            client.cwd("..")  # Step back up
        except Exception:
            try:
                client.mkd(folder_name)
                self.app.log_message("System", f"Created folder '{folder_name}' on FTP Server.")
            except Exception as e:
                self.app.log_message("Error", f"Could not create folder '{folder_name}': {e}")

    def _get_api_uuid(self):
        """Retrieves a v1 UUID from the external API or falls back to standard local Generation"""
        try:
            url = "https://www.uuidtools.com/api/generate/v1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
        except Exception as e:
            self.app.log_message("Warning", f"External API failed: {e}. Falling back to local UUID generator.")
        
        # Local OOP safe-fallback
        return str(uuid.uuid1())

    def process_selected_file(self):
        """
        Executes file analysis. 
        Saves successfully processed files inside 'main/' directory, 
        and problematic/error files under 'errors/' using an external API UUID as the filename.
        """
        selected_item = self.file_tree.selection()
        if not selected_item:
            messagebox.showwarning("Process Warning", "Please select a file from the list to process.")
            return

        if not self.ftp_manager.is_connected():
            messagebox.showerror("Processing Failed", "Connect to the FTP server first.")
            return

        filename = self.file_tree.item(selected_item, "values")[0]
        self.app.log_message("Processing", f"Processing file: {filename}...")

        # Run validation check silently to identify if file has errors
        is_valid, status_msg = self.validate_selected_file(silent=True)
        client = self.ftp_manager.get_client()

        if is_valid:
            # Clean non-error files go into 'main' directory
            self._ensure_ftp_directory("main")
            try:
                client.rename(filename, f"main/{filename}")
                self.app.processor.add_default_file(f"main/{filename}")
                self.app.log_message("Processed", f"SUCCESS: '{filename}' processed and stored under '/main' folder.")
                messagebox.showinfo("Process Complete", f"'{filename}' processed successfully and stored under '/main'!")
            except Exception as e:
                self.app.log_message("Error", f"Failed to move file to main: {e}")
                messagebox.showerror("FTP Error", f"Could not move valid file to /main folder.\nError: {e}")
        else:
            # File has errors -> Fetch external UUID and store in 'errors' folder
            self._ensure_ftp_directory("errors")
            new_uuid = self._get_api_uuid()
            error_filename = f"{new_uuid}.csv"
            
            try:
                client.rename(filename, f"errors/{error_filename}")
                self.app.processor.add_error_log(error_filename, status_msg)
                self.app.log_message("Error Logged", f"FAILED: '{filename}' has errors. Stored as 'errors/{error_filename}'.")
                messagebox.showerror("Process Failed", f"'{filename}' failed validation!\nStored in /errors folder as:\n{error_filename}")
            except Exception as e:
                self.app.log_message("Error", f"Failed to move error file: {e}")
                messagebox.showerror("FTP Error", f"Could not move error file to /errors folder.\nError: {e}")

        # Auto-refresh UI directory listing to reflect file movement changes
        self.refresh_file_list()


class LogPanel(tk.Frame):
    """Right Panel: Contains the tabbed log views using standard Notebook"""
    def __init__(self, parent):
        super().__init__(parent, bg="white", highlightbackground="#FADBD8", highlightthickness=1)
        
        tk.Label(
            self, text="📋 Activity Logs", bg="white", fg="#A04000", font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=10, pady=8)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_activity = tk.Frame(self.notebook, bg="white")
        self.notebook.add(self.tab_activity, text="Activity")
        
        self.setup_activity_log()

    def setup_activity_log(self):
        self.log_table = ttk.Treeview(
            self.tab_activity, columns=("Time", "Type", "Message"), show="headings"
        )
        self.log_table.heading("Time", text="Time")
        self.log_table.heading("Type", text="Type")
        self.log_table.heading("Message", text="Message")
        
        self.log_table.column("Time", width=100, anchor="center")
        self.log_table.column("Type", width=80, anchor="center")
        self.log_table.column("Message", width=280, anchor="w")
        
        self.log_table.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(self.tab_activity, orient="vertical", command=self.log_table.yview)
        self.log_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")


class StatusBar(tk.Frame):
    """Bottom bar containing status text and application control buttons"""
    def __init__(self, parent):
        super().__init__(parent, bg="#0A4D9A", height=45)
        self.parent = parent
        self.pack_propagate(False)
        
        self.lbl_status = tk.Label(
            self, text="Status : ✔ Ready", fg="white", bg="#0A4D9A", font=("Segoe UI", 10, "bold")
        )
        self.lbl_status.pack(side="left", padx=15, pady=8)
        
        self.btn_exit = tk.Button(
            self, text="Exit", bg="#961D10", fg="white", activebackground="#922B21",
            font=("Segoe UI", 10, "bold"), bd=0, padx=15, cursor="hand2", command=parent.destroy
        )
        self.btn_exit.pack(side="right", padx=10, pady=8)
        
        self.btn_help = tk.Button(
            self, text="Help", bg="#2980B9", fg="white", activebackground="#1F618D",
            font=("Segoe UI", 10, "bold"), bd=0, padx=15, cursor="hand2", command=self.show_help
        )
        self.btn_help.pack(side="right", padx=5, pady=8)
        
        self.btn_clear_logs = tk.Button(
            self, text="Clear Logs", bg="#F1C40F", fg="black", activebackground="#D4AC0D",
            font=("Segoe UI", 10, "bold"), bd=0, padx=15, cursor="hand2", command=self.clear_ui_logs
        )
        self.btn_clear_logs.pack(side="right", padx=5, pady=8)

        self.btn_error_logs = tk.Button(
            self, text="Error Logs", bg="#D9563E", fg="black", activebackground="#E9BE13",
            font=("Segoe UI", 10, "bold"), bd=0, padx=15, cursor="hand2", command=self.display_error_logs
        )
        self.btn_error_logs.pack(side="right", padx=5, pady=8)

    def display_error_logs(self):
        """Pulls logged validation errors from our FileProcessor instance and shows them"""
        logs = self.parent.processor.error_logs
        if not logs:
            messagebox.showinfo("Error Logs", "No files have encountered errors yet!")
            return
        
        # Build list structure
        log_summary = "--- Categorized OOP Error Logs ---\n\n"
        for idx, (fname, err, ts) in enumerate(logs, 1):
            log_summary += f"{idx}. File: {fname}\n   At: {ts}\n   Reason: {err}\n\n"
            
        # Create a scrollable dialog window
        top = tk.Toplevel(self)
        top.title("Stored Error Logs")
        top.geometry("600x400")
        
        text = tk.Text(top, wrap="word", font=("Segoe UI", 10))
        text.insert("1.0", log_summary)
        text.config(state="disabled")
        text.pack(fill="both", expand=True, padx=10, pady=10)

    def clear_ui_logs(self):
        """Clears the activity table treeview representation"""
        for item in self.parent.log_panel.log_table.get_children():
            self.parent.log_panel.log_table.delete(item)
        self.parent.log_message("System", "Log panel cleared.")

    def show_help(self):
        help_text = (
            "How it Works:\n\n"
            "1. Connect to your FTP Server.\n"
            "2. Select a file from the server directory.\n"
            "3. Click 'Process'.\n"
            "   - Clean/Safe files are moved under `/main` folder.\n"
            "   - Files with issues are renamed with external UUIDs and stored under `/errors` folder.\n"
            "4. Use the bottom buttons to view errors or clear panel lists."
        )
        messagebox.showinfo("Help / Guide", help_text)


if __name__ == "__main__":
    app = SalesDataApp()
    app.mainloop()