# Don't delete
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime, timedelta, timezone
from tkcalendar import Calendar
import threading
import os
import pandas as pd
import nseDataFetch
import bseDataFetch


# Set the daily automatic fetch time here (24-hour HH:MM format)
AUTO_FETCH_TIME = "18:18"
AUTO_FETCH_ENABLED = True
IST = timezone(timedelta(hours=5, minutes=30))


class StockDataMiningUI:
    """Main UI class for Stock Data Mining"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Data Mining - NSE & BSE Historical Data Fetcher")
        self.root.geometry("1200x700")
        
        # Initialize fetchers
        self.nse_fetcher = None
        self.bse_fetcher = None
        self.fetch_thread = None
        self.auto_fetch_thread = None
        self.last_auto_fetch_date = None
        self.auto_fetch_time = AUTO_FETCH_TIME
        self.auto_fetch_enabled = AUTO_FETCH_ENABLED
        
        # Create UI
        self.setup_ui()

        if self.auto_fetch_enabled:
            self.root.after(1000, self.schedule_next_auto_fetch)
    
    def setup_ui(self):
        """Setup the main UI layout"""
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.nse_frame = ttk.Frame(self.notebook)
        self.bse_frame = ttk.Frame(self.notebook)
        self.data_viewer_frame = ttk.Frame(self.notebook)
        self.logs_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.nse_frame, text="NSE Data Fetcher")
        self.notebook.add(self.bse_frame, text="BSE Data Fetcher")
        self.notebook.add(self.data_viewer_frame, text="Data Viewer")
        self.notebook.add(self.logs_frame, text="Logs & Status")
        
        # Setup each tab
        self.setup_nse_tab()
        self.setup_bse_tab()
        self.setup_data_viewer_tab()
        self.setup_logs_tab()
    
    def setup_nse_tab(self):
        """Setup NSE data fetcher tab"""
        # Title
        title_label = tk.Label(self.nse_frame, text="NSE Historical Stock Data Fetcher", 
                              font=("Arial", 14, "bold"), bg="lightblue", pady=10)
        title_label.pack(fill='x')
        
        # Info frame
        info_frame = tk.Frame(self.nse_frame, bg="lightyellow", padx=10, pady=5)
        info_frame.pack(fill='x', padx=5, pady=5)
        
        info_text = tk.Label(info_frame, 
                            text="Fetches historical stock data for NSE-listed companies (up to 15 years back)\n" +
                                 "Data is saved in NSE/ folder with symbol-wise subfolders",
                            bg="lightyellow", wraplength=500, justify='left')
        info_text.pack()
        
        # Control panel
        control_frame = tk.LabelFrame(self.nse_frame, text="Fetch Settings", padx=10, pady=10)
        control_frame.pack(fill='x', padx=5, pady=5)
        
        # Date range frame
        date_frame = tk.Frame(control_frame)
        date_frame.pack(fill='x', pady=5)
        
        tk.Label(date_frame, text="Start Date (YYYY-MM-DD):", width=20).pack(side='left', padx=5)
        self.nse_start_date = tk.Entry(date_frame, width=15)
        self.nse_start_date.pack(side='left', padx=5)
        self.nse_start_date.insert(0, (self.ist_now() - timedelta(days=365*10)).strftime('%Y-%m-%d'))
        
        tk.Button(date_frame, text="📅", command=lambda: self.pick_date(self.nse_start_date),
                 bg="lightblue", width=3).pack(side='left', padx=2)
        
        tk.Label(date_frame, text="  End Date (YYYY-MM-DD):", width=18).pack(side='left', padx=5)
        self.nse_end_date = tk.Entry(date_frame, width=15)
        self.nse_end_date.pack(side='left', padx=5)
        self.nse_end_date.insert(0, self.ist_now().strftime('%Y-%m-%d'))
        
        tk.Button(date_frame, text="📅", command=lambda: self.pick_date(self.nse_end_date),
                 bg="lightblue", width=3).pack(side='left', padx=2)
        
        # Stock range frame
        range_frame = tk.Frame(control_frame)
        range_frame.pack(fill='x', pady=5)
        
        tk.Label(range_frame, text="Stock Index Range - Start:", width=20).pack(side='left', padx=5)
        self.nse_start_idx = tk.Entry(range_frame, width=5)
        self.nse_start_idx.pack(side='left', padx=5)
        self.nse_start_idx.insert(0, "0")
        
        tk.Label(range_frame, text="  End:", width=5).pack(side='left', padx=5)
        self.nse_end_idx = tk.Entry(range_frame, width=5)
        self.nse_end_idx.pack(side='left', padx=5)
        self.nse_end_idx.insert(0, "0")  # 0 means all
        
        # Buttons frame
        button_frame = tk.Frame(control_frame)
        button_frame.pack(fill='x', pady=10)
        
        tk.Button(button_frame, text="Fetch All NSE Stocks", command=self.fetch_all_nse,
                 bg="green", fg="white", padx=10).pack(side='left', padx=5)
        
        tk.Button(button_frame, text="Fetch Stock Range", command=self.fetch_range_nse,
                 bg="orange", fg="white", padx=10).pack(side='left', padx=5)
        
        tk.Button(button_frame, text="Clear Fields", command=self.clear_nse_fields,
                 bg="gray", fg="white", padx=10).pack(side='left', padx=5)
        
        # Progress bar
        self.nse_progress = ttk.Progressbar(self.nse_frame, mode='indeterminate')
        self.nse_progress.pack(fill='x', padx=5, pady=5)
        
        # Status label
        self.nse_status = tk.Label(self.nse_frame, text="Ready", fg="green")
        self.nse_status.pack(fill='x', padx=5)
    
    def setup_bse_tab(self):
        """Setup BSE data fetcher tab"""
        # Title
        title_label = tk.Label(self.bse_frame, text="BSE Historical Stock Data Fetcher", 
                              font=("Arial", 14, "bold"), bg="lightcyan", pady=10)
        title_label.pack(fill='x')
        
        # Info frame
        info_frame = tk.Frame(self.bse_frame, bg="lightyellow", padx=10, pady=5)
        info_frame.pack(fill='x', padx=5, pady=5)
        
        info_text = tk.Label(info_frame, 
                            text="Fetches historical stock data for BSE-listed companies (up to 15 years back)\n" +
                                 "Data is saved in BSE/ folder with symbol-wise subfolders",
                            bg="lightyellow", wraplength=500, justify='left')
        info_text.pack()
        
        # Control panel
        control_frame = tk.LabelFrame(self.bse_frame, text="Fetch Settings", padx=10, pady=10)
        control_frame.pack(fill='x', padx=5, pady=5)
        
        # Date range frame
        date_frame = tk.Frame(control_frame)
        date_frame.pack(fill='x', pady=5)
        
        tk.Label(date_frame, text="Start Date (YYYY-MM-DD):", width=20).pack(side='left', padx=5)
        self.bse_start_date = tk.Entry(date_frame, width=15)
        self.bse_start_date.pack(side='left', padx=5)
        self.bse_start_date.insert(0, (self.ist_now() - timedelta(days=365*10)).strftime('%Y-%m-%d'))
        
        tk.Button(date_frame, text="📅", command=lambda: self.pick_date(self.bse_start_date),
                 bg="lightcyan", width=3).pack(side='left', padx=2)
        
        tk.Label(date_frame, text="  End Date (YYYY-MM-DD):", width=18).pack(side='left', padx=5)
        self.bse_end_date = tk.Entry(date_frame, width=15)
        self.bse_end_date.pack(side='left', padx=5)
        self.bse_end_date.insert(0, self.ist_now().strftime('%Y-%m-%d'))
        
        tk.Button(date_frame, text="📅", command=lambda: self.pick_date(self.bse_end_date),
                 bg="lightcyan", width=3).pack(side='left', padx=2)
        
        # Stock range frame
        range_frame = tk.Frame(control_frame)
        range_frame.pack(fill='x', pady=5)
        
        tk.Label(range_frame, text="Stock Index Range - Start:", width=20).pack(side='left', padx=5)
        self.bse_start_idx = tk.Entry(range_frame, width=5)
        self.bse_start_idx.pack(side='left', padx=5)
        self.bse_start_idx.insert(0, "0")
        
        tk.Label(range_frame, text="  End:", width=5).pack(side='left', padx=5)
        self.bse_end_idx = tk.Entry(range_frame, width=5)
        self.bse_end_idx.pack(side='left', padx=5)
        self.bse_end_idx.insert(0, "0")  # 0 means all
        
        # Buttons frame
        button_frame = tk.Frame(control_frame)
        button_frame.pack(fill='x', pady=10)
        
        tk.Button(button_frame, text="Fetch All BSE Stocks", command=self.fetch_all_bse,
                 bg="darkgreen", fg="white", padx=10).pack(side='left', padx=5)
        
        tk.Button(button_frame, text="Fetch Stock Range", command=self.fetch_range_bse,
                 bg="orange", fg="white", padx=10).pack(side='left', padx=5)
        
        tk.Button(button_frame, text="Clear Fields", command=self.clear_bse_fields,
                 bg="gray", fg="white", padx=10).pack(side='left', padx=5)
        
        # Progress bar
        self.bse_progress = ttk.Progressbar(self.bse_frame, mode='indeterminate')
        self.bse_progress.pack(fill='x', padx=5, pady=5)
        
        # Status label
        self.bse_status = tk.Label(self.bse_frame, text="Ready", fg="green")
        self.bse_status.pack(fill='x', padx=5)
    
    def setup_data_viewer_tab(self):
        """Setup Data Viewer tab"""
        # Title
        title_label = tk.Label(self.data_viewer_frame, text="Stock Data Viewer", 
                              font=("Arial", 14, "bold"), bg="lightyellow", pady=10)
        title_label.pack(fill='x')
        
        # Control panel
        control_frame = tk.LabelFrame(self.data_viewer_frame, text="Select Data Source & Companies", padx=10, pady=10)
        control_frame.pack(fill='x', padx=5, pady=5)
        
        # Source selection
        source_frame = tk.Frame(control_frame)
        source_frame.pack(fill='x', pady=5)
        
        tk.Label(source_frame, text="Data Source:", width=15).pack(side='left', padx=5)
        self.data_source_var = tk.StringVar(value="NSE")
        tk.Radiobutton(source_frame, text="NSE", variable=self.data_source_var, 
                      value="NSE", command=self.refresh_company_list).pack(side='left', padx=5)
        tk.Radiobutton(source_frame, text="BSE", variable=self.data_source_var, 
                      value="BSE", command=self.refresh_company_list).pack(side='left', padx=5)
        
        # Company selection frame
        company_frame = tk.Frame(control_frame)
        company_frame.pack(fill='both', expand=True, pady=5)
        
        tk.Label(company_frame, text="Available Companies (select one or more):", font=("Arial", 9, "bold")).pack(anchor='w', padx=5)
        
        # Listbox with scrollbar
        scrollbar = tk.Scrollbar(company_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.company_listbox = tk.Listbox(company_frame, selectmode='multiple', 
                                         yscrollcommand=scrollbar.set, height=6)
        self.company_listbox.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.config(command=self.company_listbox.yview)
        
        # Buttons frame
        button_frame = tk.Frame(control_frame)
        button_frame.pack(fill='x', pady=10)
        
        tk.Button(button_frame, text="Load Selected Data", command=self.load_selected_data,
                 bg="blue", fg="white", padx=10).pack(side='left', padx=5)
        tk.Button(button_frame, text="Refresh List", command=self.refresh_company_list,
                 bg="gray", fg="white", padx=10).pack(side='left', padx=5)
        
        # Data display frame
        display_frame = tk.LabelFrame(self.data_viewer_frame, text="Stock Data", padx=5, pady=5)
        display_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create treeview for tabular data display
        columns = ('Date', 'Open', 'High', 'Low', 'Close', 'Volume')
        self.data_tree = ttk.Treeview(display_frame, columns=columns, height=20, show='tree headings')
        
        # Define column headings and widths
        self.data_tree.heading('#0', text='Company')
        self.data_tree.column('#0', width=100)
        
        for col in columns:
            self.data_tree.heading(col, text=col)
            if col == 'Date':
                self.data_tree.column(col, width=100)
            elif col == 'Volume':
                self.data_tree.column(col, width=120)
            else:
                self.data_tree.column(col, width=90)
        
        # Add scrollbars
        tree_scrollbar_y = tk.Scrollbar(display_frame, orient='vertical', command=self.data_tree.yview)
        tree_scrollbar_x = tk.Scrollbar(display_frame, orient='horizontal', command=self.data_tree.xview)
        self.data_tree.configure(yscroll=tree_scrollbar_y.set, xscroll=tree_scrollbar_x.set)
        
        self.data_tree.grid(row=0, column=0, sticky='nsew')
        tree_scrollbar_y.grid(row=0, column=1, sticky='ns')
        tree_scrollbar_x.grid(row=1, column=0, sticky='ew')
        
        display_frame.grid_rowconfigure(0, weight=1)
        display_frame.grid_columnconfigure(0, weight=1)
        
        # Status frame
        status_frame = tk.Frame(self.data_viewer_frame)
        status_frame.pack(fill='x', padx=5, pady=5)
        
        self.data_viewer_status = tk.Label(status_frame, text="Ready", fg="green")
        self.data_viewer_status.pack(anchor='w')
        
        # Load initial company list
        self.refresh_company_list()
    
    def pick_date(self, entry_widget):
        """Open calendar popup to pick a date"""
        def on_date_select(date):
            # Convert from m/d/yy to YYYY-MM-DD format
            from datetime import datetime as dt
            try:
                date_obj = dt.strptime(str(date), '%m/%d/%y')
                formatted_date = date_obj.strftime('%Y-%m-%d')
            except:
                formatted_date = str(date)
            
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, formatted_date)
            top.destroy()
        
        try:
            current_date = datetime.strptime(entry_widget.get(), '%Y-%m-%d')
        except:
            current_date = datetime.now()
        
        top = tk.Toplevel(self.root)
        top.title("Select Date")
        top.geometry("320x280")
        
        cal = Calendar(top, selectmode='day', year=current_date.year, 
                      month=current_date.month, day=current_date.day)
        cal.pack(padx=10, pady=10, fill='both', expand=True)
        
        tk.Button(top, text="Select", command=lambda: on_date_select(cal.get_date())).pack(pady=5)
    
    def refresh_company_list(self):
        """Refresh the list of available companies based on selected source"""
        source = self.data_source_var.get()
        self.company_listbox.delete(0, tk.END)
        
        try:
            if source == "NSE":
                folder = os.path.join(os.getcwd(), "NSE")
            else:
                folder = os.path.join(os.getcwd(), "BSE")
            
            if os.path.exists(folder):
                companies = sorted([d for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d))])
                for company in companies:
                    self.company_listbox.insert(tk.END, company)
                self.data_viewer_status.config(text=f"Found {len(companies)} companies", fg="green")
            else:
                self.data_viewer_status.config(text=f"{source} folder not found", fg="red")
        except Exception as e:
            self.data_viewer_status.config(text=f"Error: {str(e)}", fg="red")
    
    def load_selected_data(self):
        """Load and display data for selected companies"""
        selected_indices = self.company_listbox.curselection()
        
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select at least one company")
            return
        
        source = self.data_source_var.get()
        folder = os.path.join(os.getcwd(), source)
        
        # Clear existing data
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)
        
        try:
            self.data_viewer_status.config(text="Loading data...", fg="orange")
            self.root.update()
            
            total_records = 0
            
            for idx in selected_indices:
                company = self.company_listbox.get(idx)
                company_path = os.path.join(folder, company)
                
                # Get the most recent CSV file
                csv_files = [f for f in os.listdir(company_path) if f.endswith('.csv')]
                if csv_files:
                    # Sort by date and get the latest
                    latest_file = sorted(csv_files)[-1]
                    csv_path = os.path.join(company_path, latest_file)
                    
                    # Read the CSV file
                    df = pd.read_csv(csv_path)
                    
                    # Add data to treeview, limit to last 100 rows for performance
                    df_display = df.tail(100) if len(df) > 100 else df
                    
                    for idx_row, row in df_display.iterrows():
                        try:
                            values = (
                                str(row.get('Date', ''))[:10],
                                f"{float(row.get('Open', 0)):.2f}",
                                f"{float(row.get('High', 0)):.2f}",
                                f"{float(row.get('Low', 0)):.2f}",
                                f"{float(row.get('Close', 0)):.2f}",
                                f"{int(float(row.get('Volume', 0))):,}"
                            )
                            self.data_tree.insert('', 'end', text=company, values=values)
                            total_records += 1
                        except:
                            pass
            
            self.data_viewer_status.config(
                text=f"Loaded {len(list(selected_indices))} companies, {total_records} records displayed", 
                fg="green"
            )
        
        except Exception as e:
            self.data_viewer_status.config(text=f"Error loading data: {str(e)}", fg="red")
    
    def setup_logs_tab(self):
        """Setup logs and status tab"""
        # Title
        title_label = tk.Label(self.logs_frame, text="Logs & Status", 
                              font=("Arial", 14, "bold"), bg="lightgray", pady=10)
        title_label.pack(fill='x')
        
        # Tabs for different logs
        logs_notebook = ttk.Notebook(self.logs_frame)
        logs_notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # NSE Log
        nse_log_frame = ttk.Frame(logs_notebook)
        logs_notebook.add(nse_log_frame, text="NSE Log")
        
        tk.Label(nse_log_frame, text="NSE Fetch Log:", font=("Arial", 10, "bold")).pack(anchor='w', padx=5)
        self.nse_log_text = scrolledtext.ScrolledText(nse_log_frame, height=20, width=100, wrap='word')
        self.nse_log_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # BSE Log
        bse_log_frame = ttk.Frame(logs_notebook)
        logs_notebook.add(bse_log_frame, text="BSE Log")
        
        tk.Label(bse_log_frame, text="BSE Fetch Log:", font=("Arial", 10, "bold")).pack(anchor='w', padx=5)
        self.bse_log_text = scrolledtext.ScrolledText(bse_log_frame, height=20, width=100, wrap='word')
        self.bse_log_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Clear logs button frame
        button_frame = tk.Frame(self.logs_frame)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        tk.Button(button_frame, text="Clear All Logs", command=self.clear_all_logs,
                 bg="red", fg="white").pack(side='left', padx=5)
        
        tk.Button(button_frame, text="Refresh Log Files", command=self.refresh_log_files,
                 bg="blue", fg="white").pack(side='left', padx=5)

    def ist_now(self):
        """Return the current time in IST."""
        return datetime.now(IST)

    def parse_auto_fetch_time(self):
        """Parse the configured auto fetch time as an IST time object."""
        return datetime.strptime(self.auto_fetch_time, "%H:%M").time()

    def get_next_auto_fetch_run(self):
        """Return the next scheduled auto fetch run time in IST."""
        scheduled_time = self.parse_auto_fetch_time()
        now = self.ist_now()
        candidate = now.replace(hour=scheduled_time.hour, minute=scheduled_time.minute, second=0, microsecond=0)

        if candidate <= now:
            candidate = candidate + timedelta(days=1)

        return candidate

    def schedule_next_auto_fetch(self):
        """Schedule the next automatic fetch based on IST time."""
        try:
            if not self.auto_fetch_enabled:
                return

            next_run = self.get_next_auto_fetch_run()
            delay_ms = max(1000, int((next_run - self.ist_now()).total_seconds() * 1000))
            self.log_nse(f"Next automatic fetch scheduled for {next_run.strftime('%Y-%m-%d %H:%M:%S')} IST")
            self.log_bse(f"Next automatic fetch scheduled for {next_run.strftime('%Y-%m-%d %H:%M:%S')} IST")
            self.root.after(delay_ms, self.start_auto_fetch_if_due)
        except Exception as e:
            self.log_nse(f"Auto fetch scheduler error: {str(e)}")
            self.log_bse(f"Auto fetch scheduler error: {str(e)}")
            self.root.after(60000, self.schedule_next_auto_fetch)

    def start_auto_fetch_if_due(self):
        """Start the scheduled automatic fetch and queue the next run."""
        try:
            if not self.auto_fetch_enabled:
                return

            now = self.ist_now()
            if self.last_auto_fetch_date == now.date():
                self.root.after(1000, self.schedule_next_auto_fetch)
                return

            if self.fetch_thread is not None and self.fetch_thread.is_alive():
                self.root.after(1000, self.schedule_next_auto_fetch)
                return

            if self.auto_fetch_thread is None or not self.auto_fetch_thread.is_alive():
                self.last_auto_fetch_date = now.date()
                self.auto_fetch_thread = threading.Thread(target=self._auto_fetch_worker, daemon=True)
                self.auto_fetch_thread.start()
        finally:
            self.root.after(1000, self.schedule_next_auto_fetch)

    def _auto_fetch_worker(self):
        """Worker thread for the daily automatic NSE and BSE fetch."""
        try:
            run_now = self.ist_now()
            run_date = run_now.strftime('%Y-%m-%d')
            start_date = run_date
            end_date = (run_now + timedelta(days=1)).strftime('%Y-%m-%d')

            self.log_nse(f"Automatic fetch started for {run_date}")
            self.log_bse(f"Automatic fetch started for {run_date}")
            self.update_nse_status("Automatic fetch running...", "orange")
            self.update_bse_status("Automatic fetch running...", "orange")

            self.nse_fetcher = nseDataFetch.get_nse_fetcher()
            nse_loaded = self.nse_fetcher.load_stocks_list()
            if nse_loaded is None:
                raise Exception("Failed to load NSE stocks list for automatic fetch.")

            def nse_progress(current, total, symbol):
                self.log_nse(f"Auto progress: {current}/{total} - {symbol}")
                self.update_nse_status(f"Auto fetching {symbol}... ({current}/{total})", "blue")

            nse_results = self.nse_fetcher.fetch_all_stocks(start_date, end_date, nse_progress)
            nse_summary = self.nse_fetcher.get_fetch_summary(nse_results)
            self.log_nse(nse_summary)
            self.update_nse_status("Automatic NSE fetch completed!", "green")

            self.bse_fetcher = bseDataFetch.get_bse_fetcher()
            bse_loaded = self.bse_fetcher.load_stocks_list()
            if bse_loaded is None:
                raise Exception("Failed to load BSE stocks list for automatic fetch.")

            def bse_progress(current, total, symbol):
                self.log_bse(f"Auto progress: {current}/{total} - {symbol}")
                self.update_bse_status(f"Auto fetching {symbol}... ({current}/{total})", "blue")

            bse_results = self.bse_fetcher.fetch_all_stocks(start_date, end_date, bse_progress)
            bse_summary = self.bse_fetcher.get_fetch_summary(bse_results)
            self.log_bse(bse_summary)
            self.update_bse_status("Automatic BSE fetch completed!", "green")

            self.log_nse(f"Automatic fetch finished for {run_date}")
            self.log_bse(f"Automatic fetch finished for {run_date}")
        except Exception as e:
            error_msg = f"Automatic fetch error: {str(e)}"
            self.log_nse(error_msg)
            self.log_bse(error_msg)
            self.update_nse_status(error_msg, "red")
            self.update_bse_status(error_msg, "red")
        finally:
            self.auto_fetch_thread = None
    
    def log_nse(self, message):
        """Log message to NSE log"""
        self.nse_log_text.insert(tk.END, f"[{self.ist_now().strftime('%H:%M:%S')}] {message}\n")
        self.nse_log_text.see(tk.END)
        self.root.update()
    
    def log_bse(self, message):
        """Log message to BSE log"""
        self.bse_log_text.insert(tk.END, f"[{self.ist_now().strftime('%H:%M:%S')}] {message}\n")
        self.bse_log_text.see(tk.END)
        self.root.update()
    
    def update_nse_status(self, message, color="black"):
        """Update NSE status label"""
        self.nse_status.config(text=message, fg=color)
        self.root.update()
    
    def update_bse_status(self, message, color="black"):
        """Update BSE status label"""
        self.bse_status.config(text=message, fg=color)
        self.root.update()
    
    def fetch_all_nse(self):
        """Fetch all NSE stocks"""
        self.fetch_thread = threading.Thread(target=self._fetch_all_nse_worker, daemon=True)
        self.fetch_thread.start()
    
    def _fetch_all_nse_worker(self):
        """Worker thread for NSE fetch"""
        try:
            self.update_nse_status("Loading stocks list...", "orange")
            self.nse_progress.start()
            
            self.nse_fetcher = nseDataFetch.get_nse_fetcher()
            self.nse_fetcher.load_stocks_list()
            
            start_date = self.nse_start_date.get() if self.nse_start_date.get() else None
            end_date = self.nse_end_date.get() if self.nse_end_date.get() else None
            
            self.log_nse(f"Starting fetch for all NSE stocks from {start_date} to {end_date}")
            self.update_nse_status("Fetching NSE data...", "orange")
            
            def progress_callback(current, total, symbol):
                self.log_nse(f"Progress: {current}/{total} - {symbol}")
                self.update_nse_status(f"Fetching {symbol}... ({current}/{total})", "blue")
            
            results = self.nse_fetcher.fetch_all_stocks(start_date, end_date, progress_callback)
            summary = self.nse_fetcher.get_fetch_summary(results)
            
            self.log_nse(summary)
            self.update_nse_status("Fetch completed!", "green")
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.log_nse(error_msg)
            self.update_nse_status(error_msg, "red")
        finally:
            self.nse_progress.stop()
    
    def fetch_range_nse(self):
        """Fetch NSE stocks in specified range"""
        try:
            start_idx = int(self.nse_start_idx.get())
            end_idx = int(self.nse_end_idx.get())
            
            if end_idx == 0:
                messagebox.showinfo("Info", "End index 0 means all stocks. Use 'Fetch All NSE Stocks' button instead.")
                return
            
            self.fetch_thread = threading.Thread(target=self._fetch_range_nse_worker, 
                                               args=(start_idx, end_idx), daemon=True)
            self.fetch_thread.start()
        except ValueError:
            messagebox.showerror("Error", "Invalid index values. Please enter integers.")
    
    def _fetch_range_nse_worker(self, start_idx, end_idx):
        """Worker thread for NSE range fetch"""
        try:
            self.update_nse_status("Loading stocks list...", "orange")
            self.nse_progress.start()
            
            self.nse_fetcher = nseDataFetch.get_nse_fetcher()
            self.nse_fetcher.load_stocks_list()
            
            start_date = self.nse_start_date.get() if self.nse_start_date.get() else None
            end_date = self.nse_end_date.get() if self.nse_end_date.get() else None
            
            self.log_nse(f"Starting fetch for NSE stocks {start_idx} to {end_idx}")
            
            stocks_to_fetch = self.nse_fetcher.stocks_df.iloc[start_idx:end_idx]
            results = {}
            
            for idx, row in stocks_to_fetch.iterrows():
                symbol = row['Symbol']
                self.log_nse(f"Fetching {symbol}...")
                self.update_nse_status(f"Fetching {symbol}...", "blue")
                
                data = self.nse_fetcher.fetch_stock_data(symbol, start_date, end_date)
                if data is not None:
                    self.nse_fetcher.save_stock_data_consolidated(symbol, data)
                    results[symbol] = {'status': 'success', 'records': len(data)}
                else:
                    results[symbol] = {'status': 'failed', 'records': 0}
            
            summary = self.nse_fetcher.get_fetch_summary(results)
            self.log_nse(summary)
            self.update_nse_status("Range fetch completed!", "green")
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.log_nse(error_msg)
            self.update_nse_status(error_msg, "red")
        finally:
            self.nse_progress.stop()
    
    def fetch_all_bse(self):
        """Fetch all BSE stocks"""
        self.fetch_thread = threading.Thread(target=self._fetch_all_bse_worker, daemon=True)
        self.fetch_thread.start()
    
    def _fetch_all_bse_worker(self):
        """Worker thread for BSE fetch"""
        try:
            self.update_bse_status("Loading stocks list...", "orange")
            self.bse_progress.start()
            
            self.bse_fetcher = bseDataFetch.get_bse_fetcher()
            loaded = self.bse_fetcher.load_stocks_list()
            
            if loaded is None:
                raise Exception("Failed to load BSE stocks list. Check the file path and format.")
            
            start_date = self.bse_start_date.get() if self.bse_start_date.get() else None
            end_date = self.bse_end_date.get() if self.bse_end_date.get() else None
            
            self.log_bse(f"Starting fetch for all BSE stocks from {start_date} to {end_date}")
            self.update_bse_status("Fetching BSE data...", "orange")
            
            def progress_callback(current, total, symbol):
                self.log_bse(f"Progress: {current}/{total} - {symbol}")
                self.update_bse_status(f"Fetching {symbol}... ({current}/{total})", "blue")
            
            results = self.bse_fetcher.fetch_all_stocks(start_date, end_date, progress_callback)
            summary = self.bse_fetcher.get_fetch_summary(results)
            
            self.log_bse(summary)
            self.update_bse_status("Fetch completed!", "green")
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.log_bse(error_msg)
            self.update_bse_status(error_msg, "red")
        finally:
            self.bse_progress.stop()
    
    def fetch_range_bse(self):
        """Fetch BSE stocks in specified range"""
        try:
            start_idx = int(self.bse_start_idx.get())
            end_idx = int(self.bse_end_idx.get())
            
            if end_idx == 0:
                messagebox.showinfo("Info", "End index 0 means all stocks. Use 'Fetch All BSE Stocks' button instead.")
                return
            
            self.fetch_thread = threading.Thread(target=self._fetch_range_bse_worker, 
                                               args=(start_idx, end_idx), daemon=True)
            self.fetch_thread.start()
        except ValueError:
            messagebox.showerror("Error", "Invalid index values. Please enter integers.")
    
    def _fetch_range_bse_worker(self, start_idx, end_idx):
        """Worker thread for BSE range fetch"""
        try:
            self.update_bse_status("Loading stocks list...", "orange")
            self.bse_progress.start()
            
            self.bse_fetcher = bseDataFetch.get_bse_fetcher()
            loaded = self.bse_fetcher.load_stocks_list()
            
            if loaded is None:
                raise Exception("Failed to load BSE stocks list. Check the file path and format.")
            
            start_date = self.bse_start_date.get() if self.bse_start_date.get() else None
            end_date = self.bse_end_date.get() if self.bse_end_date.get() else None
            
            self.log_bse(f"Starting fetch for BSE stocks {start_idx} to {end_idx}")
            
            stocks_to_fetch = self.bse_fetcher.stocks_df.iloc[start_idx:end_idx]
            results = {}
            
            for idx, row in stocks_to_fetch.iterrows():
                symbol = row['Symbol']
                self.log_bse(f"Fetching {symbol}...")
                self.update_bse_status(f"Fetching {symbol}...", "blue")
                
                data = self.bse_fetcher.fetch_stock_data(symbol, start_date, end_date)
                if data is not None:
                    self.bse_fetcher.save_stock_data_consolidated(symbol, data)
                    results[symbol] = {'status': 'success', 'records': len(data)}
                else:
                    results[symbol] = {'status': 'failed', 'records': 0}
            
            summary = self.bse_fetcher.get_fetch_summary(results)
            self.log_bse(summary)
            self.update_bse_status("Range fetch completed!", "green")
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.log_bse(error_msg)
            self.update_bse_status(error_msg, "red")
        finally:
            self.bse_progress.stop()
    
    def clear_nse_fields(self):
        """Clear NSE input fields"""
        self.nse_start_date.delete(0, tk.END)
        self.nse_start_date.insert(0, (self.ist_now() - timedelta(days=365*10)).strftime('%Y-%m-%d'))
        self.nse_end_date.delete(0, tk.END)
        self.nse_end_date.insert(0, self.ist_now().strftime('%Y-%m-%d'))
        self.nse_start_idx.delete(0, tk.END)
        self.nse_start_idx.insert(0, "0")
        self.nse_end_idx.delete(0, tk.END)
        self.nse_end_idx.insert(0, "0")
    
    def clear_bse_fields(self):
        """Clear BSE input fields"""
        self.bse_start_date.delete(0, tk.END)
        self.bse_start_date.insert(0, (self.ist_now() - timedelta(days=365*10)).strftime('%Y-%m-%d'))
        self.bse_end_date.delete(0, tk.END)
        self.bse_end_date.insert(0, self.ist_now().strftime('%Y-%m-%d'))
        self.bse_start_idx.delete(0, tk.END)
        self.bse_start_idx.insert(0, "0")
        self.bse_end_idx.delete(0, tk.END)
        self.bse_end_idx.insert(0, "0")
    
    def clear_all_logs(self):
        """Clear all log displays"""
        self.nse_log_text.delete(1.0, tk.END)
        self.bse_log_text.delete(1.0, tk.END)
    
    def refresh_log_files(self):
        """Refresh log files from disk"""
        self.log_nse("Refreshing log files...")
        self.log_bse("Refreshing log files...")
        
        log_dir = os.path.join(os.getcwd(), "logs")
        if os.path.exists(log_dir):
            nse_log_file = os.path.join(log_dir, "nse_fetch.log")
            bse_log_file = os.path.join(log_dir, "bse_fetch.log")
            
            if os.path.exists(nse_log_file):
                with open(nse_log_file, 'r') as f:
                    self.nse_log_text.delete(1.0, tk.END)
                    self.nse_log_text.insert(tk.END, f.read())
            
            if os.path.exists(bse_log_file):
                with open(bse_log_file, 'r') as f:
                    self.bse_log_text.delete(1.0, tk.END)
                    self.bse_log_text.insert(tk.END, f.read())


if __name__ == "__main__":
    root = tk.Tk()
    app = StockDataMiningUI(root)
    root.mainloop()

# === Remaining code unchanged ===
root.mainloop()