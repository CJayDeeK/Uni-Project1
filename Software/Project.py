import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import threading
import time

DATA_FILE = os.path.join(os.path.dirname(__file__), 'app_data.json')

class Assignment:
    def __init__(self, name, deadline, module, weight=0):
        self.name = name
        self.deadline = deadline
        self.module = module
        self.weight = weight
        self.submitted = False
        self.grade = None

class Module:
    def __init__(self, name):
        self.name = name
        self.assignments = []
        self.target_grade = 70

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
        self.root.bind('<F7>', lambda e: self.toggle_developer_mode())

        self.modules = []
        self.assignments = []
        self.developer_mode = False
        self.load_data()

        self.create_widgets()
        self.update_modules_list()
        self.update_assignments_list()
        self.update_dashboard()

        threading.Thread(target=self.check_notifications, daemon=True).start()

        self.root.after(60000, self.update_dashboard_loop)

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text="Dashboard")
        self.create_dashboard()

        self.modules_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.modules_frame, text="Modules")
        self.create_modules_tab()

        self.assignments_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.assignments_frame, text="Assignments")
        self.create_assignments_tab()

        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        self.create_settings_tab()

    def create_dashboard(self):
        self.dashboard_text = tk.Text(self.dashboard_frame, wrap=tk.WORD)
        self.dashboard_text.pack(fill=tk.BOTH, expand=True)
        self.dashboard_text.tag_configure("green", foreground="green")
        self.dashboard_text.tag_configure("orange", foreground="orange")
        self.dashboard_text.tag_configure("red", foreground="red")

    def create_modules_tab(self):
        self.modules_listbox = tk.Listbox(self.modules_frame, width=80, justify='center')
        self.modules_listbox.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(self.modules_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        ttk.Button(btn_frame, text="Add Module", command=self.add_module).grid(row=0, column=0)
        ttk.Button(btn_frame, text="Delete Module", command=self.delete_module).grid(row=0, column=1)

    def create_assignments_tab(self):
        self.assignments_listbox = tk.Listbox(self.assignments_frame, width=80, justify='center')
        self.assignments_listbox.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(self.assignments_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        btn_frame.grid_columnconfigure(2, weight=1)

        ttk.Button(btn_frame, text="Add Assignment", command=self.add_assignment).grid(row=0, column=0)
        ttk.Button(btn_frame, text="Mark Submitted", command=self.mark_submitted).grid(row=0, column=1)
        ttk.Button(btn_frame, text="Delete Assignment", command=self.delete_assignment).grid(row=0, column=2)

    def create_settings_tab(self):
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

            upcoming = [ass for ass in mod.assignments if not ass.submitted and ass.deadline > datetime.now()]
            if upcoming:
                self.dashboard_text.insert(tk.END, "Upcoming Assignments:\n")
                for ass in sorted(upcoming, key=lambda x: x.deadline):
                    days_left = (ass.deadline - datetime.now()).days
                    if days_left >= 14:
                        status = "Green"
                    elif days_left >= 4:
                        status = "Orange"
                    else:
                        status = "Red"
                    self.dashboard_text.insert(tk.END, f"  {ass.name}: {ass.deadline.strftime('%Y-%m-%d')}\n", status.lower())

            missed = [ass for ass in mod.assignments if not ass.submitted and ass.deadline < datetime.now()]
            if missed:
                self.dashboard_text.insert(tk.END, "Missed Assignments:\n")
                for ass in sorted(missed, key=lambda x: x.deadline):
                    self.dashboard_text.insert(tk.END, f"  {ass.name}: {ass.deadline.strftime('%Y-%m-%d')} - MISSED\n", "red")

            submitted = [ass for ass in mod.assignments if ass.submitted]
            if submitted:
                self.dashboard_text.insert(tk.END, "Completed Assignments:\n")
                for ass in sorted(submitted, key=lambda x: x.deadline):
                    grade_str = f"{ass.grade}%" if ass.grade is not None else "N/A"
                    self.dashboard_text.insert(tk.END, f"  {ass.name}: {ass.deadline.strftime('%Y-%m-%d')} - Submitted, Grade: {grade_str}\n")
            self.dashboard_text.insert(tk.END, "\n")

    def update_dashboard_loop(self):
        self.update_dashboard()
        self.root.after(60000, self.update_dashboard_loop)

    def toggle_developer_mode(self):
        self.developer_mode = not self.developer_mode
        status = "enabled" if self.developer_mode else "disabled"
        messagebox.showinfo("Developer Mode", f"Developer mode {status}.")

    def on_module_select(self, event):
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
            self.update_assignments_list()

    def delete_module(self):
        if not self.developer_mode:
            messagebox.showerror("Access Denied", "Developer mode required to delete modules.")
            return
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
        self.assignments = []
        for mod in self.modules:
            self.assignments_listbox.insert(tk.END, "-" * 50)
            self.assignments.append(None)
            self.assignments_listbox.insert(tk.END, f"Module: {mod.name}")
            self.assignments.append(None)
            self.assignments_listbox.insert(tk.END, "-" * 50)
            self.assignments.append(None)
            for ass in mod.assignments:
                self.assignments.append(ass)
                self.assignments_listbox.insert(tk.END, f"  {ass.name} - Percentage of Module Grade: {ass.weight}%")

    def add_assignment(self):
        if not self.modules:
            messagebox.showerror("Error", "No modules available. Add a module first.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Add Assignment")
        dialog.geometry("300x350")

        ttk.Label(dialog, text="Select Module:").pack(pady=5)
        module_var = tk.StringVar()
        module_combo = ttk.Combobox(dialog, textvariable=module_var, values=[mod.name for mod in self.modules])
        module_combo.pack(pady=5)
        module_combo.set(self.modules[0].name)

        ttk.Label(dialog, text="Assignment Name:").pack(pady=5)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var)
        name_entry.pack(pady=5)

        ttk.Label(dialog, text="Deadline (YYYY-MM-DD):").pack(pady=5)
        deadline_var = tk.StringVar()
        deadline_entry = ttk.Entry(dialog, textvariable=deadline_var)
        deadline_entry.pack(pady=5)

        ttk.Label(dialog, text="Percentage of Module Grade (%):").pack(pady=5)
        weight_var = tk.StringVar()
        weight_entry = ttk.Entry(dialog, textvariable=weight_var)
        weight_entry.pack(pady=5)

        def on_ok():
            module_name = module_var.get()
            name = name_var.get()
            deadline_str = deadline_var.get()
            weight_str = weight_var.get()

            if not name or not deadline_str:
                messagebox.showerror("Error", "Name and deadline are required")
                return

            try:
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d")
            except:
                messagebox.showerror("Error", "Invalid date format")
                return

            try:
                weight = float(weight_str) if weight_str else 0
            except:
                messagebox.showerror("Error", "Invalid weight")
                return

            mod = next((m for m in self.modules if m.name == module_name), None)
            if not mod:
                messagebox.showerror("Error", "Module not found")
                return

            ass = Assignment(name, deadline, mod, weight)
            mod.add_assignment(ass)
            self.save_data()
            self.update_dashboard()
            self.update_assignments_list()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)

    def mark_submitted(self):
        selection = self.assignments_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select an assignment to mark as submitted.")
            return
        ass = self.assignments[selection[0]]
        if ass is None:
            messagebox.showerror("Error", "Please select an assignment, not a module header.")
            return
        if ass.submitted:
            messagebox.showinfo("Info", "Assignment is already submitted.")
            return
        grade = simpledialog.askfloat("Grade", "Enter grade (0-100%):", minvalue=0, maxvalue=100)
        if grade is not None:
            ass.grade = grade
        ass.submitted = True
        self.save_data()
        self.update_dashboard()
        self.update_assignments_list()

    def delete_assignment(self):
        if not self.developer_mode:
            messagebox.showerror("Access Denied", "Developer mode required to delete assignments.")
            return
        selection = self.assignments_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select an assignment to delete.")
            return
        ass = self.assignments[selection[0]]
        if ass is None:
            messagebox.showerror("Error", "Please select an assignment, not a module header.")
            return
        if not messagebox.askyesno("Confirm", f"Delete assignment '{ass.name}'?"):
            return
        ass.module.assignments.remove(ass)
        self.save_data()
        self.update_dashboard()
        self.update_assignments_list()

    def save_settings(self):
        messagebox.showinfo("Info", "Settings saved")

    def check_notifications(self):
        while True:
            now = datetime.now()
            for mod in self.modules:
                for ass in mod.assignments:
                    if not ass.submitted:
                        days_left = (ass.deadline - now).days
                        if days_left == 1:
                            self.send_notification(f"Assignment {ass.name} due tomorrow!")
            time.sleep(3600)

    def send_notification(self, message):
        print(f"Notification: {message}")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()

