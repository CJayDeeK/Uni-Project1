import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import threading
import time

# Data storage file
DATA_FILE = os.path.join(os.path.dirname(__file__), 'app_data.json')

class Assignment:
    def __init__(self, name, deadline, module, weight=0):
        self.name = name
        self.deadline = deadline  # datetime object
        self.module = module
        self.weight = weight  # percentage weight in module
        self.submitted = False
        self.grade = None

class Module:
    def __init__(self, name):
        self.name = name
        self.assignments = []
        self.target_grade = 70  # default target

    def add_assignment(self, assignment):
        self.assignments.append(assignment)

    def calculate_mean_grade(self):
        total_weight = 0
        weighted_sum = 0
        for ass in self.assignments:
            if ass.grade is not None:
                weighted_sum += ass.grade * (ass.weight / 100)
                total_weight += ass.weight
        if total_weight == 0:
            return None
        return weighted_sum / (total_weight / 100)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("University Assignment Tracker")
        self.root.geometry("800x600")

        self.modules = []
        self.load_data()

        self.create_widgets()
        self.update_modules_list()
        self.update_assignments_list()
        self.update_dashboard()

        # Start notification thread
        threading.Thread(target=self.check_notifications, daemon=True).start()

    def create_widgets(self):
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Dashboard tab
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text="Dashboard")
        self.create_dashboard()

        # Modules tab
        self.modules_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.modules_frame, text="Modules")
        self.create_modules_tab()

        # Assignments tab
        self.assignments_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.assignments_frame, text="Assignments")
        self.create_assignments_tab()

        # Settings tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        self.create_settings_tab()

    def create_dashboard(self):
        self.dashboard_text = tk.Text(self.dashboard_frame, wrap=tk.WORD)
        self.dashboard_text.pack(fill=tk.BOTH, expand=True)

    def create_modules_tab(self):
        # Listbox for modules
        self.modules_listbox = tk.Listbox(self.modules_frame)
        self.modules_listbox.pack(side=tk.LEFT, fill=tk.Y)
        self.modules_listbox.bind('<<ListboxSelect>>', self.on_module_select)

        # Frame for module details
        self.module_details_frame = ttk.Frame(self.modules_frame)
        self.module_details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Buttons
        btn_frame = ttk.Frame(self.modules_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Button(btn_frame, text="Add Module", command=self.add_module).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Delete Module", command=self.delete_module).pack(side=tk.LEFT)

    def create_assignments_tab(self):
        # Similar structure
        self.assignments_listbox = tk.Listbox(self.assignments_frame)
        self.assignments_listbox.pack(side=tk.LEFT, fill=tk.Y)

        self.assignment_details_frame = ttk.Frame(self.assignments_frame)
        self.assignment_details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(self.assignments_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Button(btn_frame, text="Add Assignment", command=self.add_assignment).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Mark Submitted", command=self.mark_submitted).pack(side=tk.LEFT)

    def create_settings_tab(self):
        # Email settings
        ttk.Label(self.settings_frame, text="Email for notifications:").pack()
        self.email_entry = ttk.Entry(self.settings_frame)
        self.email_entry.pack(fill=tk.X)

        ttk.Button(self.settings_frame, text="Save Settings", command=self.save_settings).pack()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                for mod_data in data.get('modules', []):
                    mod = Module(mod_data['name'])
                    for ass_data in mod_data.get('assignments', []):
                        deadline = datetime.fromisoformat(ass_data['deadline'])
                        ass = Assignment(ass_data['name'], deadline, mod, ass_data.get('weight', 0))
                        ass.submitted = ass_data.get('submitted', False)
                        ass.grade = ass_data.get('grade')
                        mod.add_assignment(ass)
                    self.modules.append(mod)
        else:
            # Sample data
            mod1 = Module("Computer Science")
            ass1 = Assignment("Project 1", datetime.now() + timedelta(days=7), mod1, 30)
            mod1.add_assignment(ass1)
            self.modules.append(mod1)

    def save_data(self):
        data = {'modules': []}
        for mod in self.modules:
            mod_data = {'name': mod.name, 'assignments': []}
            for ass in mod.assignments:
                ass_data = {
                    'name': ass.name,
                    'deadline': ass.deadline.isoformat(),
                    'weight': ass.weight,
                    'submitted': ass.submitted,
                    'grade': ass.grade
                }
                mod_data['assignments'].append(ass_data)
            data['modules'].append(mod_data)
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def update_dashboard(self):
        self.dashboard_text.delete(1.0, tk.END)
        self.dashboard_text.insert(tk.END, "Dashboard\n\n")

        for mod in self.modules:
            self.dashboard_text.insert(tk.END, f"Module: {mod.name}\n")
            mean = mod.calculate_mean_grade()
            if mean is not None:
                self.dashboard_text.insert(tk.END, f"Current Mean Grade: {mean:.2f}%\n")
            else:
                self.dashboard_text.insert(tk.END, "No grades yet\n")

            # Upcoming assignments
            upcoming = [ass for ass in mod.assignments if not ass.submitted and ass.deadline > datetime.now()]
            if upcoming:
                self.dashboard_text.insert(tk.END, "Upcoming Assignments:\n")
                for ass in sorted(upcoming, key=lambda x: x.deadline):
                    days_left = (ass.deadline - datetime.now()).days
                    status = "Green" if days_left > 7 else "Orange" if days_left > 3 else "Red"
                    self.dashboard_text.insert(tk.END, f"  {ass.name}: {ass.deadline.strftime('%Y-%m-%d')} ({status})\n")
            self.dashboard_text.insert(tk.END, "\n")

    def on_module_select(self, event):
        # Clear previous
        for widget in self.module_details_frame.winfo_children():
            widget.destroy()

        selection = self.modules_listbox.curselection()
        if selection:
            mod = self.modules[selection[0]]
            ttk.Label(self.module_details_frame, text=f"Module: {mod.name}").pack()
            mean = mod.calculate_mean_grade()
            if mean:
                ttk.Label(self.module_details_frame, text=f"Mean Grade: {mean:.2f}%").pack()

    def add_module(self):
        name = simpledialog.askstring("Add Module", "Module Name:")
        if name:
            self.modules.append(Module(name))
            self.update_modules_list()
            self.save_data()

    def delete_module(self):
        selection = self.modules_listbox.curselection()
        if selection:
            del self.modules[selection[0]]
            self.update_modules_list()
            self.save_data()
            self.update_assignments_list()

    def update_modules_list(self):
        self.modules_listbox.delete(0, tk.END)
        for mod in self.modules:
            self.modules_listbox.insert(tk.END, mod.name)

    def update_assignments_list(self):
        self.assignments_listbox.delete(0, tk.END)
        for mod in self.modules:
            for ass in mod.assignments:
                self.assignments_listbox.insert(tk.END, f"{ass.name} ({mod.name})")

    def add_assignment(self):
        # Simple dialog
        name = simpledialog.askstring("Add Assignment", "Assignment Name:")
        if not name:
            return
        deadline_str = simpledialog.askstring("Deadline", "Deadline (YYYY-MM-DD):")
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d")
        except:
            messagebox.showerror("Error", "Invalid date format")
            return
        weight = simpledialog.askfloat("Weight", "Weight (%):", minvalue=0, maxvalue=100)
        if weight is None:
            weight = 0

        # Assume first module for now
        if self.modules:
            ass = Assignment(name, deadline, self.modules[0], weight)
            self.modules[0].add_assignment(ass)
            self.save_data()
            self.update_dashboard()
            self.update_assignments_list()

    def mark_submitted(self):
        # Placeholder
        messagebox.showinfo("Info", "Feature not implemented yet")

    def save_settings(self):
        # Placeholder
        messagebox.showinfo("Info", "Settings saved")

    def check_notifications(self):
        while True:
            now = datetime.now()
            for mod in self.modules:
                for ass in mod.assignments:
                    if not ass.submitted:
                        days_left = (ass.deadline - now).days
                        if days_left == 1:
                            # Send notification
                            self.send_notification(f"Assignment {ass.name} due tomorrow!")
            time.sleep(3600)  # Check every hour

    def send_notification(self, message):
        # Placeholder for email
        print(f"Notification: {message}")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()

