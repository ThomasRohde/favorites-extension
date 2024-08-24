import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import asyncio
import threading

class IntelligentFavoritesApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Intelligent Favorites Extension")
        self.geometry("900x600")
        self.configure(bg="#f0f0f0")

        self.api_base_url = "http://localhost:8000/api"

        self.create_widgets()

    def create_widgets(self):
        # Create a notebook (tabbed interface)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background="#f0f0f0")
        style.configure("TNotebook.Tab", padding=[10, 5], font=('Helvetica', 10))
        style.configure("TButton", padding=5, font=('Helvetica', 10))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # Create tabs
        self.favorites_tab = ttk.Frame(self.notebook)
        self.folders_tab = ttk.Frame(self.notebook)
        self.tags_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.favorites_tab, text="Favorites")
        self.notebook.add(self.folders_tab, text="Folders")
        self.notebook.add(self.tags_tab, text="Tags")

        # Favorites Tab
        self.create_favorites_tab()

        # Folders Tab
        self.create_folders_tab()

        # Tags Tab
        self.create_tags_tab()

    def create_favorites_tab(self):
        # Favorites List
        list_frame = ttk.Frame(self.favorites_tab)
        list_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.favorites_list = tk.Listbox(list_frame, width=80, font=('Helvetica', 10))
        self.favorites_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.favorites_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.favorites_list.configure(yscrollcommand=scrollbar.set)

        # Refresh Button
        refresh_button = ttk.Button(self.favorites_tab, text="Refresh Favorites", command=self.refresh_favorites)
        refresh_button.pack(pady=5)

        # Add Favorite Frame
        add_frame = ttk.Frame(self.favorites_tab)
        add_frame.pack(pady=10)

        ttk.Label(add_frame, text="URL:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.url_entry = ttk.Entry(add_frame, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(add_frame, text="Title:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.title_entry = ttk.Entry(add_frame, width=50)
        self.title_entry.grid(row=1, column=1, padx=5, pady=5)

        add_button = ttk.Button(add_frame, text="Add Favorite", command=self.add_favorite)
        add_button.grid(row=2, column=1, pady=10)

        # Status Label
        self.status_label = ttk.Label(self.favorites_tab, text="", font=('Helvetica', 10))
        self.status_label.pack(pady=5)

    def create_folders_tab(self):
        # Folders List
        list_frame = ttk.Frame(self.folders_tab)
        list_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.folders_list = tk.Listbox(list_frame, width=80, font=('Helvetica', 10))
        self.folders_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.folders_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.folders_list.configure(yscrollcommand=scrollbar.set)

        # Refresh Button
        refresh_button = ttk.Button(self.folders_tab, text="Refresh Folders", command=self.refresh_folders)
        refresh_button.pack(pady=5)

        # Add Folder Frame
        add_frame = ttk.Frame(self.folders_tab)
        add_frame.pack(pady=10)

        ttk.Label(add_frame, text="Name:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.folder_name_entry = ttk.Entry(add_frame, width=50)
        self.folder_name_entry.grid(row=0, column=1, padx=5, pady=5)

        add_button = ttk.Button(add_frame, text="Add Folder", command=self.add_folder)
        add_button.grid(row=1, column=1, pady=10)

    def create_tags_tab(self):
        # Tags List
        list_frame = ttk.Frame(self.tags_tab)
        list_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.tags_list = tk.Listbox(list_frame, width=80, font=('Helvetica', 10))
        self.tags_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tags_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tags_list.configure(yscrollcommand=scrollbar.set)

        # Refresh Button
        refresh_button = ttk.Button(self.tags_tab, text="Refresh Tags", command=self.refresh_tags)
        refresh_button.pack(pady=5)

        # Add Tag Frame
        add_frame = ttk.Frame(self.tags_tab)
        add_frame.pack(pady=10)

        ttk.Label(add_frame, text="Name:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.tag_name_entry = ttk.Entry(add_frame, width=50)
        self.tag_name_entry.grid(row=0, column=1, padx=5, pady=5)

        add_button = ttk.Button(add_frame, text="Add Tag", command=self.add_tag)
        add_button.grid(row=1, column=1, pady=10)

    def refresh_favorites(self):
        response = requests.get(f"{self.api_base_url}/favorites/")
        if response.status_code == 200:
            favorites = response.json()
            self.favorites_list.delete(0, tk.END)
            for favorite in favorites:
                self.favorites_list.insert(tk.END, f"{favorite['title']} - {favorite['url']}")
        else:
            messagebox.showerror("Error", "Failed to fetch favorites")

    def add_favorite(self):
        url = self.url_entry.get()
        title = self.title_entry.get()
        if url and title:
            try:
                response = requests.post(f"{self.api_base_url}/favorites/", json={"url": url, "title": title})
                response.raise_for_status()
                task_data = response.json()
                self.status_label.config(text="Adding favorite... Please wait.")
                threading.Thread(target=self.poll_task_status, args=(task_data['task_id'],)).start()
            except requests.RequestException as e:
                messagebox.showerror("Error", f"Failed to add favorite: {str(e)}")
        else:
            messagebox.showwarning("Warning", "Please enter both URL and title")

    def poll_task_status(self, task_id):
        max_attempts = 30  # Maximum number of attempts (30 seconds)
        attempt = 0
        while attempt < max_attempts:
            try:
                response = requests.get(f"{self.api_base_url}/favorites/task/{task_id}")
                response.raise_for_status()
                task_status = response.json()
                if task_status['status'] == 'completed':
                    self.status_label.config(text="Favorite added successfully!")
                    self.refresh_favorites()
                    self.url_entry.delete(0, tk.END)
                    self.title_entry.delete(0, tk.END)
                    break
                elif task_status['status'] == 'failed':
                    self.status_label.config(text=f"Failed to add favorite: {task_status.get('error', 'Unknown error')}")
                    break
                else:
                    self.status_label.config(text="Adding favorite... Please wait.")
            except requests.RequestException as e:
                self.status_label.config(text=f"Failed to check task status: {str(e)}")
                break
            
            self.update_idletasks()
            self.after(1000)  # Poll every second
            attempt += 1
        
        if attempt >= max_attempts:
            self.status_label.config(text="Timed out while adding favorite. Please try again.")

    def refresh_folders(self):
        response = requests.get(f"{self.api_base_url}/folders/")
        if response.status_code == 200:
            folders = response.json()
            self.folders_list.delete(0, tk.END)
            for folder in folders:
                self.folders_list.insert(tk.END, folder['name'])
        else:
            messagebox.showerror("Error", "Failed to fetch folders")

    def add_folder(self):
        name = self.folder_name_entry.get()
        if name:
            response = requests.post(f"{self.api_base_url}/folders/", json={"name": name})
            if response.status_code == 200:
                messagebox.showinfo("Success", "Folder added successfully")
                self.refresh_folders()
                self.folder_name_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", "Failed to add folder")
        else:
            messagebox.showwarning("Warning", "Please enter a folder name")

    def refresh_tags(self):
        response = requests.get(f"{self.api_base_url}/tags/")
        if response.status_code == 200:
            tags = response.json()
            self.tags_list.delete(0, tk.END)
            for tag in tags:
                self.tags_list.insert(tk.END, tag['name'])
        else:
            messagebox.showerror("Error", "Failed to fetch tags")

    def add_tag(self):
        name = self.tag_name_entry.get()
        if name:
            response = requests.post(f"{self.api_base_url}/tags/", json={"name": name})
            if response.status_code == 200:
                messagebox.showinfo("Success", "Tag added successfully")
                self.refresh_tags()
                self.tag_name_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", "Failed to add tag")
        else:
            messagebox.showwarning("Warning", "Please enter a tag name")

if __name__ == "__main__":
    app = IntelligentFavoritesApp()
    app.mainloop()