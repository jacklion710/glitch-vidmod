"""
GUI interface for adjusting corruption parameters, previewing, and batch processing
"""

import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import glob
import sys

class ToolTip:
    """Create a tooltip for a widget"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<ButtonPress>', self.leave)
    
    def enter(self, event=None):
        self.schedule()
    
    def leave(self, event=None):
        self.unschedule()
        self.hidetip()
    
    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)
    
    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)
    
    def showtip(self):
        x, y, cx, cy = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#0f131a", foreground="#e9eef2",
                        relief=tk.SOLID, borderwidth=1,
                        font=("Arial", 9), padx=8, pady=4,
                        wraplength=300)
        label.pack(ipadx=1)
    
    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class FlatButton(tk.Canvas):
    """A custom-drawn button to avoid platform-native button theming overrides (macOS Tk)."""
    def __init__(
        self,
        parent,
        text,
        command,
        button_bg,
        hover_bg,
        border_color,
        hover_border_color=None,
        text_fg="white",
        font=("Arial", 12, "bold"),
        height=46,
        corner_pad=8,
        parent_bg=None,
    ):
        bg = parent_bg if parent_bg is not None else parent.cget("bg")
        super().__init__(parent, height=height, bg=bg, highlightthickness=0, bd=0)
        self._command = command
        self._button_bg = button_bg
        self._hover_bg = hover_bg
        self._border_color = border_color
        self._hover_border_color = hover_border_color if hover_border_color is not None else border_color
        self._text_fg = text_fg
        self._font = font
        self._corner_pad = corner_pad
        self._enabled = True

        self._rect_id = self.create_rectangle(
            0,
            0,
            1,
            1,
            fill=button_bg,
            outline=border_color,
            width=2,
        )
        self._text_id = self.create_text(0, 0, text=text, fill=text_fg, font=font)

        self.configure(cursor="hand2")
        self.bind("<Configure>", self._on_configure)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def set_enabled(self, enabled: bool):
        self._enabled = bool(enabled)
        if self._enabled:
            self.configure(cursor="hand2")
            self.itemconfig(self._text_id, fill=self._text_fg)
            self._set_bg(self._button_bg)
        else:
            self.configure(cursor="arrow")
            self.itemconfig(self._text_id, fill="#7f8897")
            self._set_bg("#242a33")

    def _set_bg(self, color: str):
        outline = self._border_color if self._enabled else "#3a4352"
        self.itemconfig(self._rect_id, fill=color, outline=outline)

    def _on_configure(self, event=None):
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        pad = self._corner_pad
        self.coords(self._rect_id, pad, pad, w - pad, h - pad)
        self.coords(self._text_id, w // 2, h // 2)

    def _on_enter(self, event=None):
        if self._enabled:
            self.itemconfig(self._rect_id, outline=self._hover_border_color)
            self._set_bg(self._hover_bg)

    def _on_leave(self, event=None):
        if self._enabled:
            self.itemconfig(self._rect_id, outline=self._border_color)
            self._set_bg(self._button_bg)

    def _on_click(self, event=None):
        if self._enabled and callable(self._command):
            self._command()

class VideoCorruptionInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Corruption Interface")
        self.root.geometry("700x950")
        self.root.minsize(700, 900)
        
        # Dark theme colors (inky + distinct accents)
        self.bg_color = "#0b0d10"
        self.frame_bg = "#141820"
        self.input_bg = "#1d2430"
        self.text_color = "#e9eef2"
        self.accent_color = "#9b7bff"   # violet (primary)
        self.success_color = "#2fc6b2"  # teal (preview)
        self.warning_color = "#d7a64a"  # amber (overwrite)
        
        # Configure root window
        self.root.configure(bg=self.bg_color)
        
        # Configure ttk styles
        self.setup_styles()
        
        # Default parameters
        self.keyint = tk.IntVar(value=10)
        self.keyint_min = tk.IntVar(value=10)
        self.noise_amount = tk.IntVar(value=3000)
        
        # Get video list
        self.video_extensions = ['*.mp4', '*.mov', '*.avi', '*.mkv', '*.m4v', '*.webm']
        self.videos = []
        self.load_video_list()
        
        # Selected video for preview
        self.selected_video = tk.StringVar()
        if self.videos:
            self.selected_video.set(self.videos[0])
        
        # Processing state
        self.is_processing = False

        # Viewer options
        self.auto_open_viewer_after_preview = tk.BooleanVar(value=True)
        self.last_preview_video = None
        
        # Button references for enabling/disabling
        self.preview_btn = None
        self.direct_batch_btn = None
        
        self.create_widgets()
    
    def setup_styles(self):
        """Configure ttk styles for dark theme"""
        style = ttk.Style()
        style.theme_use('clam')
        
        bg_color = self.bg_color
        frame_bg = self.frame_bg
        text_color = self.text_color
        
        # Configure LabelFrame
        style.configure('TLabelframe', background=bg_color, foreground=text_color, 
                       bordercolor=frame_bg, lightcolor=frame_bg, darkcolor=frame_bg)
        style.configure('TLabelframe.Label', background=bg_color, foreground=text_color)
        style.map('TLabelframe', background=[('active', bg_color), ('!active', bg_color)])
        
        # Configure Combobox
        input_bg = self.input_bg
        accent_color = self.accent_color
        style.configure('TCombobox', fieldbackground=input_bg, foreground=text_color,
                       background=input_bg, borderwidth=2, arrowcolor=text_color,
                       bordercolor=accent_color)
        style.map('TCombobox', 
                 fieldbackground=[('readonly', input_bg)],
                 background=[('readonly', input_bg)],
                 bordercolor=[('focus', accent_color)])
    
    def load_video_list(self):
        """Load list of video files from vids directory"""
        self.videos = []
        for ext in self.video_extensions:
            video_paths = glob.glob(f'vids/{ext}')
            for path in video_paths:
                self.videos.append(os.path.basename(path))
        self.videos = sorted(self.videos)
    
    def get_output_path(self, video_name):
        """Get output path for corrupted video"""
        base_name = os.path.splitext(video_name)[0]
        return f'out/{base_name}_corrupted.mp4'
    
    def build_ffmpeg_command(self, input_path, output_path):
        """Build ffmpeg command with current parameters"""
        keyint = self.keyint.get()
        keyint_min = self.keyint_min.get()
        noise_amount = self.noise_amount.get()
        
        x264_params = f'keyint={keyint}:keyint_min={keyint_min}:bframes=0'
        noise_filter = f'noise=amount={noise_amount}*not(key)'
        
        return [
            'ffmpeg', '-y', '-i', input_path,
            '-c:v', 'libx264',
            '-x264-params', x264_params,
            '-bsf:v', noise_filter,
            '-pix_fmt', 'yuv420p',
            output_path
        ]
    
    def create_widgets(self):
        """Create GUI widgets"""
        # Title
        title_label = tk.Label(self.root, text="Video Corruption Interface", 
                              font=("Arial", 18, "bold"),
                              bg=self.bg_color, fg=self.text_color)
        title_label.pack(pady=15)
        
        # Parameters frame
        params_frame = ttk.LabelFrame(self.root, text="Corruption Parameters", padding=15)
        params_frame.pack(fill=tk.X, padx=15, pady=8)
        params_frame.configure(style='TLabelframe')
        # Set frame background
        for widget in params_frame.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.configure(bg=self.frame_bg)
        
        # Keyint parameter
        keyint_frame = tk.Frame(params_frame, bg=self.frame_bg)
        keyint_frame.pack(fill=tk.X, pady=8)
        keyint_label = tk.Label(keyint_frame, text="Keyframe Interval (keyint):", 
                               bg=self.frame_bg, fg=self.text_color,
                               font=("Arial", 11))
        keyint_label.pack(side=tk.LEFT)
        keyint_spin = tk.Spinbox(keyint_frame, from_=1, to=300, textvariable=self.keyint, 
                                width=12, bg=self.input_bg, fg=self.text_color,
                                insertbackground=self.text_color,
                                buttonbackground=self.accent_color,
                                selectbackground=self.accent_color,
                                selectforeground="white",
                                font=("Arial", 11, "bold"),
                                relief=tk.FLAT, borderwidth=2,
                                highlightthickness=1, highlightbackground=self.accent_color)
        keyint_spin.pack(side=tk.RIGHT)
        ToolTip(keyint_label, "Controls the interval between keyframes in the encoded video.\n"
                              "Lower values create more keyframes, which can affect corruption patterns.\n"
                              "Range: 1-300 frames")
        ToolTip(keyint_spin, "Controls the interval between keyframes in the encoded video.\n"
                            "Lower values create more keyframes, which can affect corruption patterns.\n"
                            "Range: 1-300 frames")
        
        # Keyint_min parameter
        keyint_min_frame = tk.Frame(params_frame, bg=self.frame_bg)
        keyint_min_frame.pack(fill=tk.X, pady=8)
        keyint_min_label = tk.Label(keyint_min_frame, text="Min Keyframe Interval (keyint_min):", 
                                   bg=self.frame_bg, fg=self.text_color,
                                   font=("Arial", 11))
        keyint_min_label.pack(side=tk.LEFT)
        keyint_min_spin = tk.Spinbox(keyint_min_frame, from_=1, to=300, textvariable=self.keyint_min, 
                                    width=12, bg=self.input_bg, fg=self.text_color,
                                    insertbackground=self.text_color,
                                    buttonbackground=self.accent_color,
                                    selectbackground=self.accent_color,
                                    selectforeground="white",
                                    font=("Arial", 11, "bold"),
                                    relief=tk.FLAT, borderwidth=2,
                                    highlightthickness=1, highlightbackground=self.accent_color)
        keyint_min_spin.pack(side=tk.RIGHT)
        ToolTip(keyint_min_label, "Sets the minimum interval between keyframes.\n"
                                 "Must be less than or equal to keyint.\n"
                                 "Affects the minimum spacing of corruption artifacts.\n"
                                 "Range: 1-300 frames")
        ToolTip(keyint_min_spin, "Sets the minimum interval between keyframes.\n"
                                "Must be less than or equal to keyint.\n"
                                "Affects the minimum spacing of corruption artifacts.\n"
                                "Range: 1-300 frames")
        
        # Noise amount parameter
        noise_frame = tk.Frame(params_frame, bg=self.frame_bg)
        noise_frame.pack(fill=tk.X, pady=8)
        noise_label = tk.Label(noise_frame, text="Noise Amount:", 
                              bg=self.frame_bg, fg=self.text_color,
                              font=("Arial", 11))
        noise_label.pack(side=tk.LEFT)
        noise_spin = tk.Spinbox(noise_frame, from_=0, to=10000, textvariable=self.noise_amount, 
                               width=12, bg=self.input_bg, fg=self.text_color,
                               insertbackground=self.text_color,
                               buttonbackground=self.accent_color,
                               selectbackground=self.accent_color,
                               selectforeground="white",
                               font=("Arial", 11, "bold"),
                               relief=tk.FLAT, borderwidth=2,
                               highlightthickness=1, highlightbackground=self.accent_color)
        noise_spin.pack(side=tk.RIGHT)
        ToolTip(noise_label, "Controls the intensity of corruption noise applied to non-keyframes.\n"
                           "Higher values create more visible glitches and artifacts.\n"
                           "The noise is multiplied by 'not(key)' to only affect non-keyframe areas.\n"
                           "Range: 0-10000")
        ToolTip(noise_spin, "Controls the intensity of corruption noise applied to non-keyframes.\n"
                          "Higher values create more visible glitches and artifacts.\n"
                          "The noise is multiplied by 'not(key)' to only affect non-keyframe areas.\n"
                          "Range: 0-10000")
        
        # Video selection frame
        video_frame = ttk.LabelFrame(self.root, text="Video Selection", padding=15)
        video_frame.pack(fill=tk.X, padx=15, pady=8)
        video_frame.configure(style='TLabelframe')
        
        video_label = tk.Label(video_frame, text="Select video for preview:", 
                              bg=self.bg_color, fg=self.text_color,
                              font=("Arial", 11))
        video_label.pack(anchor=tk.W, pady=(0, 8))
        video_combo = ttk.Combobox(video_frame, textvariable=self.selected_video, 
                                   values=self.videos, state="readonly", width=50,
                                   font=("Arial", 10))
        video_combo.pack(fill=tk.X, pady=5)
        
        viewer_controls = tk.Frame(video_frame, bg=self.bg_color)
        viewer_controls.pack(fill=tk.X, pady=(10, 0))

        auto_open_check = tk.Checkbutton(
            viewer_controls,
            text="Auto-open viewer after preview",
            variable=self.auto_open_viewer_after_preview,
            bg=self.bg_color,
            fg=self.text_color,
            activebackground=self.bg_color,
            activeforeground=self.text_color,
            selectcolor=self.bg_color,
            font=("Arial", 10),
            padx=0,
            pady=0,
        )
        auto_open_check.pack(side=tk.LEFT)
        ToolTip(auto_open_check, "When enabled, the side-by-side viewer will open automatically after a preview finishes.")

        open_viewer_container = tk.Frame(video_frame, bg=self.bg_color)
        open_viewer_container.pack(fill=tk.X, pady=(10, 0))
        self.open_viewer_btn = FlatButton(
            open_viewer_container,
            text="Open Viewer for Selected Video",
            command=self.open_viewer_for_selected,
            button_bg="#000000",
            hover_bg="#111318",
            border_color=self.text_color,
            text_fg=self.text_color,
            font=("Arial", 12, "bold"),
            parent_bg=self.bg_color,
        )
        self.open_viewer_btn.pack(fill=tk.X)

        # Preview button container
        preview_container = tk.Frame(video_frame, bg=self.bg_color)
        preview_container.pack(fill=tk.X, pady=12)
        
        # Preview button
        self.preview_btn = FlatButton(
            preview_container,
            text="Preview on Selected Video",
            command=self.preview_video,
            button_bg="#000000",
            hover_bg="#111318",
            border_color=self.text_color,
            text_fg=self.text_color,
            font=("Arial", 12, "bold"),
            parent_bg=self.bg_color,
        )
        self.preview_btn.pack(fill=tk.X)
        
        # Batch processing frame
        batch_frame = ttk.LabelFrame(self.root, text="Batch Processing", padding=15)
        batch_frame.pack(fill=tk.X, padx=15, pady=8)
        batch_frame.configure(style='TLabelframe')
        
        # Direct batch button container
        direct_batch_container = tk.Frame(batch_frame, bg=self.bg_color)
        direct_batch_container.pack(fill=tk.X, pady=6)
        
        # Direct batch button
        self.direct_batch_btn = FlatButton(
            direct_batch_container,
            text="Process All Videos (Overwrite Existing)",
            command=self.direct_batch,
            button_bg="#000000",
            hover_bg="#111318",
            border_color=self.text_color,
            text_fg=self.text_color,
            font=("Arial", 12, "bold"),
            parent_bg=self.bg_color,
        )
        self.direct_batch_btn.pack(fill=tk.X)
        
        # Status/log frame
        log_frame = ttk.LabelFrame(self.root, text="Status Log", padding=15)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=8)
        log_frame.configure(style='TLabelframe')
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=18, wrap=tk.WORD,
                                                  bg=self.frame_bg, fg=self.text_color,
                                                  insertbackground=self.text_color,
                                                  selectbackground=self.accent_color,
                                                  selectforeground="white",
                                                  font=("Consolas", 9),
                                                  relief=tk.FLAT, borderwidth=2)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        self.log("Interface ready. Select a video and adjust parameters to get started.")
    
    def log(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def preview_video(self):
        """Preview corruption on selected video"""
        if not self.selected_video.get():
            messagebox.showerror("Error", "Please select a video")
            return
        
        if self.is_processing:
            messagebox.showwarning("Warning", "Processing in progress. Please wait.")
            return
        
        video_name = self.selected_video.get()
        input_path = f'vids/{video_name}'
        output_path = self.get_output_path(video_name)
        
        if not os.path.exists(input_path):
            messagebox.showerror("Error", f"Video not found: {input_path}")
            return
        
        self.log(f"Starting preview for: {video_name}")
        self.log(f"Parameters: keyint={self.keyint.get()}, keyint_min={self.keyint_min.get()}, noise={self.noise_amount.get()}")
        
        self.is_processing = True
        thread = threading.Thread(target=self.process_video_thread, 
                                 args=(input_path, output_path, video_name, True))
        thread.daemon = True
        thread.start()
    
    def process_video_thread(self, input_path, output_path, video_name, is_preview=False):
        """Process video in separate thread"""
        try:
            cmd = self.build_ffmpeg_command(input_path, output_path)
            self.log(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                if is_preview:
                    self.log(f"✓ Preview complete: {os.path.basename(output_path)}")
                    self.log("Opening the side-by-side viewer for this video (or use the Open Viewer button).")
                    self.last_preview_video = video_name
                    if self.auto_open_viewer_after_preview.get():
                        self.root.after(0, lambda: self.open_viewer_for_video(video_name))
                else:
                    self.log(f"✓ Processed: {video_name}")
            else:
                self.log(f"✗ Error processing {video_name}: {result.stderr}")
        except Exception as e:
            self.log(f"✗ Exception: {str(e)}")
        finally:
            self.is_processing = False

    def open_viewer_for_selected(self):
        video_name = self.selected_video.get()
        if not video_name:
            messagebox.showerror("Error", "Please select a video first.")
            return
        self.open_viewer_for_video(video_name)

    def open_viewer_for_video(self, video_name: str):
        """Launch the side-by-side viewer starting at the given video."""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            view_script = os.path.join(script_dir, "view.py")
            if not os.path.exists(view_script):
                messagebox.showerror("Error", f"Viewer script not found: {view_script}")
                return

            # Use the filename; view.py strips extension to match the pair base name.
            cmd = [sys.executable, view_script, "--video", video_name]
            subprocess.Popen(cmd, cwd=script_dir)
            self.log(f"Viewer opened for: {video_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open viewer: {e}")
    
    def direct_batch(self):
        """Directly process all videos without preview"""
        if self.is_processing:
            messagebox.showwarning("Warning", "Processing in progress. Please wait.")
            return
        
        response = messagebox.askyesno(
            "Confirm Direct Batch Process",
            f"Process all videos with current parameters?\n\n"
            f"Keyint: {self.keyint.get()}\n"
            f"Keyint Min: {self.keyint_min.get()}\n"
            f"Noise Amount: {self.noise_amount.get()}\n\n"
            f"This will DELETE and recreate all corrupted videos."
        )
        
        if response:
            self.process_all_videos(overwrite=True)
    
    def process_all_videos(self, overwrite=False):
        """Process all videos in batch"""
        if not self.videos:
            messagebox.showerror("Error", "No videos found in vids/ directory")
            return
        
        self.is_processing = True
        self.log(f"Starting batch process for {len(self.videos)} videos...")
        
        # Delete existing corrupted videos if overwrite
        if overwrite:
            for video_name in self.videos:
                output_path = self.get_output_path(video_name)
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                        self.log(f"Deleted existing: {os.path.basename(output_path)}")
                    except Exception as e:
                        self.log(f"Warning: Could not delete {output_path}: {e}")
        
        # Process each video
        def batch_thread():
            for i, video_name in enumerate(self.videos, 1):
                input_path = f'vids/{video_name}'
                output_path = self.get_output_path(video_name)
                
                if not os.path.exists(input_path):
                    self.log(f"✗ Skipping (not found): {video_name}")
                    continue
                
                self.log(f"[{i}/{len(self.videos)}] Processing: {video_name}")
                self.process_video_thread(input_path, output_path, video_name, False)
            
            self.log("✓ Batch processing complete!")
            self.is_processing = False
        
        thread = threading.Thread(target=batch_thread)
        thread.daemon = True
        thread.start()

def main():
    # Ensure output directory exists
    os.makedirs('out', exist_ok=True)
    
    root = tk.Tk()
    app = VideoCorruptionInterface(root)
    root.mainloop()

if __name__ == "__main__":
    main()

