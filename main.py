# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pdf2image import convert_from_path
from PIL import Image, ImageFilter, ImageTk
import re
from tkinterdnd2 import TkinterDnD, DND_FILES
import threading
import os
import shutil
import time
import subprocess
import platform

class PDFWatermarkApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Watermark Tool")
        self.geometry("800x600")
        
        self.pdf_path = ""
        self.watermark_path = "wasserzeichen/wasserzeichen.png"
        self.watermark2_path = "wasserzeichen/wasserzeichen2.png"
        self.thumbnail_width, self.thumbnail_height = 403, 236
        self.output_folder = ""
        self.preview_images = []
        
        self.create_widgets()
    
    def create_widgets(self):
        self.label = tk.Label(self, text="PDF hierher ziehen oder Datei auswählen", pady=10)
        self.label.pack()
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_drop)
        
        self.open_button = tk.Button(self, text="PDF-Datei auswählen", command=self.load_pdf)
        self.open_button.pack(pady=10)
        
        self.watermark_label = tk.Label(self, text="Seiten für Wasserzeichen, z.B. ab Seite 2 bis Ende: 2-")
        self.watermark_label.pack()
        self.watermark_pages_entry = tk.Entry(self, width=30)
        self.watermark_pages_entry.insert(0, "2-")
        self.watermark_pages_entry.pack(pady=5)
        
        self.blur_label = tk.Label(self, text="Seiten für Unschärfe")
        self.blur_label.pack()
        self.blur_pages_entry = tk.Entry(self, width=30)
        self.blur_pages_entry.insert(0, "2-")
        self.blur_pages_entry.pack(pady=5)
        
        self.blur_strength_label = tk.Label(self, text="Unschärfestärke, keine ist 0")
        self.blur_strength_label.pack()
        self.blur_slider = tk.Scale(self, from_=0, to=10, orient="horizontal")
        self.blur_slider.set(5)
        self.blur_slider.pack()

        # Preview canvas with limited height and correctly positioned scrollbar
        preview_container = tk.Frame(self)
        preview_container.pack(fill="both", expand=True, pady=10)

        self.preview_canvas = tk.Canvas(preview_container, height=200)
        self.preview_canvas.pack(side="left", fill="both", expand=True)
        
        self.scrollbar = ttk.Scrollbar(preview_container, orient="vertical", command=self.preview_canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        
        self.preview_frame = tk.Frame(self.preview_canvas)
        self.preview_canvas.create_window((0, 0), window=self.preview_frame, anchor="nw")
        self.preview_frame.bind("<Configure>", lambda e: self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all")))
        self.preview_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.process_button = tk.Button(self, text="PDF verarbeiten", command=self.start_processing, state="disabled")
        self.process_button.pack(pady=10)

        self.loading_label = tk.Label(self, text="")
        self.loading_label.pack()

    def toggle_inputs(self, state):
        # Enable or disable all input fields and buttons
        self.watermark_pages_entry.config(state=state)
        self.blur_pages_entry.config(state=state)
        self.blur_slider.config(state=state)
        self.open_button.config(state=state)
        self.process_button.config(state=state)

    def load_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.pdf_path = file_path
            self.output_folder = os.path.splitext(os.path.basename(file_path))[0]

            if os.path.exists(self.output_folder):
                if messagebox.askyesno("Überschreiben?", "Der Ordner existiert bereits. Möchten Sie ihn überschreiben?"):
                    shutil.rmtree(self.output_folder)
                else:
                    return

            os.makedirs(self.output_folder, exist_ok=True)
            self.clear_preview_images()  # Löscht alte Vorschaubilder
            self.reset_inputs()
            self.label.config(text=f"Ausgewählte Datei: {self.pdf_path}")
            self.process_button.config(state="normal")
            threading.Thread(target=self.convert_pdf_to_images).start()

    def on_drop(self, event):
        self.pdf_path = event.data.strip("{}")
        self.output_folder = os.path.splitext(os.path.basename(self.pdf_path))[0]

        if os.path.exists(self.output_folder):
            if messagebox.askyesno("Überschreiben?", "Der Ordner existiert bereits. Möchten Sie ihn überschreiben?"):
                shutil.rmtree(self.output_folder)
            else:
                return

        os.makedirs(self.output_folder, exist_ok=True)
        self.clear_preview_images()  # Löscht alte Vorschaubilder
        self.reset_inputs()
        self.label.config(text=f"Ausgewählte Datei: {self.pdf_path}")
        self.process_button.config(state="normal")
        threading.Thread(target=self.convert_pdf_to_images).start()

        os.makedirs(self.output_folder, exist_ok=True)
        self.reset_inputs()
        self.label.config(text=f"Ausgewählte Datei: {self.pdf_path}")
        self.process_button.config(state="normal")
        threading.Thread(target=self.convert_pdf_to_images).start()

    def clear_preview_images(self):
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        self.preview_images.clear()

    def reset_inputs(self):
        self.watermark_pages_entry.delete(0, tk.END)
        self.watermark_pages_entry.insert(0, "2-")
        self.blur_pages_entry.delete(0, tk.END)
        self.blur_pages_entry.insert(0, "2-")
        self.blur_slider.set(5)

    def loading_animation(self, text):
        for _ in range(10):
            for symbol in "|/-\\":
                self.loading_label.config(text=f"{text} {symbol}")
                time.sleep(0.1)
                self.loading_label.update()

    def convert_pdf_to_images(self):
        threading.Thread(target=self.loading_animation, args=("PDF wird konvertiert...",)).start()
        images = convert_from_path(self.pdf_path)
        self.preview_images.clear()
        for i, image in enumerate(images, start=1):
            output_path = os.path.join(self.output_folder, f"page_{i:03d}_temp.png")
            image.save(output_path, "PNG")
            thumbnail = image.copy()
            thumbnail.thumbnail((100, 100))
            thumbnail_img = ImageTk.PhotoImage(thumbnail)
            self.preview_images.append(thumbnail_img)
            tk.Label(self.preview_frame, image=thumbnail_img).grid(row=i // 10, column=i % 10)  # 10 images per row
        self.loading_label.config(text="")
        self.update()

    def parse_page_input(self, input_str, total_pages):
        pages = set()
        parts = input_str.split(',')
        for part in parts:
            if '-' in part:
                start, end = part.split('-')
                start = int(start)
                end = int(end) if end else total_pages
                pages.update(range(start, end + 1))
            else:
                pages.add(int(part))
        return pages

    def start_processing(self):
        self.toggle_inputs("disabled")  
        threading.Thread(target=self.process_pdf).start()

    def process_pdf(self):
        if not self.pdf_path:
            messagebox.showwarning("Warnung", "Bitte eine PDF-Datei auswählen.")
            return

        watermark_pages_input = self.watermark_pages_entry.get()
        blur_pages_input = self.blur_pages_entry.get()
        blur_strength = self.blur_slider.get()

        try:
            images = convert_from_path(self.pdf_path)
            total_pages = len(images)
            watermark_pages = self.parse_page_input(watermark_pages_input, total_pages) if watermark_pages_input else set(range(1, total_pages + 1))
            blur_pages = self.parse_page_input(blur_pages_input, total_pages) if blur_pages_input else set()

            watermark1 = Image.open(self.watermark_path).convert("RGBA")
            watermark1.thumbnail((self.thumbnail_width, self.thumbnail_height))
            watermark2 = Image.open(self.watermark2_path).convert("RGBA")
            watermark2.thumbnail((self.thumbnail_width, self.thumbnail_height))

            self.loading_label.config(text="Bilder werden verarbeitet...")

            threads = []
            for i, image in enumerate(images, start=1):
                t = threading.Thread(target=self.process_page, args=(i, image, watermark1, watermark2, watermark_pages, blur_pages, blur_strength))
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            self.cleanup_temp_files()
            self.update_thumbnails(watermark_pages, blur_pages)
            self.show_success_dialog()
            self.toggle_inputs("normal")
                
        except Exception as e:
            self.toggle_inputs("normal")
            messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten: {e}")
        
        finally:
            self.loading_label.config(text="")

    def show_success_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Verarbeitung abgeschlossen")
        tk.Label(dialog, text="PDF wurde erfolgreich verarbeitet.").pack(pady=10)
        
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        open_folder_button = tk.Button(button_frame, text="Ordner öffnen", command=self.open_output_folder)
        open_folder_button.pack(side="left", padx=5)

        ok_button = tk.Button(button_frame, text="OK", command=dialog.destroy)
        ok_button.pack(side="right", padx=5)

    def open_output_folder(self):
        if platform.system() == "Windows":
            os.startfile(self.output_folder)
        elif platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", self.output_folder])
        else:  # Linux
            subprocess.Popen(["xdg-open", self.output_folder])


    def process_page(self, i, image, watermark1, watermark2, watermark_pages, blur_pages, blur_strength):
        if i in blur_pages and blur_strength > 0:
            image = image.filter(ImageFilter.GaussianBlur(radius=blur_strength))

        if i in watermark_pages:
            positions = self.generate_watermark_positions(image.size, watermark1.size)
            for x, y, watermark_path in positions:
                watermark = watermark1 if watermark_path == self.watermark_path else watermark2
                image.paste(watermark, (x, y), watermark)

        output_path = os.path.join(self.output_folder, f"Seite_{i:03d}.png")
        image.save(output_path, "PNG")

    def generate_watermark_positions(self, image_size, watermark_size):
        positions = []
        row_pattern = [[self.watermark_path, self.watermark2_path, None], 
                      [self.watermark2_path, None, self.watermark_path], 
                      [None, self.watermark_path, self.watermark2_path]]
        row_index = 0
        y = 0
        while y < image_size[1]:
            x = 0
            col_index = 0
            while x < image_size[0]:
                watermark_path = row_pattern[row_index % len(row_pattern)][col_index % len(row_pattern[0])]
                if watermark_path:
                    positions.append((x, y, watermark_path))
                x += watermark_size[0]
                col_index += 1
            y += watermark_size[1]
            row_index += 1
        return positions

    def update_thumbnails(self, watermark_pages, blur_pages):
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        for i, img in enumerate(self.preview_images, start=1):
            label = tk.Label(self.preview_frame, image=img)
            label.grid(row=i // 10, column=i % 10)
            if i in watermark_pages or i in blur_pages:
                label.config(borderwidth=2, relief="solid")

    def cleanup_temp_files(self):
        for file in os.listdir(self.output_folder):
            if file.endswith("_temp.png"):
                os.remove(os.path.join(self.output_folder, file))
        print("Temporäre Dateien wurden gelöscht.")
        self.loading_label.config(text="")

if __name__ == "__main__":
    app = PDFWatermarkApp()
    app.mainloop()
