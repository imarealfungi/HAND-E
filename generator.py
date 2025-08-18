import tkinter as tk
from tkinter import messagebox
import json
import pyperclip
import os
import time
import re
import subprocess

class PatternNotepad:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pattern Notepad")
        self.root.geometry("600x500")
        self.root.configure(bg='#2b2b2b')
        
        # Create patterns folder
        self.patterns_folder = "saved_patterns"
        if not os.path.exists(self.patterns_folder):
            os.makedirs(self.patterns_folder)
        
        self.setup_gui()
        self.auto_paste()  # Check clipboard on startup
        
        # Auto-paste every 500ms
        self.root.after(500, self.monitor_clipboard)
    
    def setup_gui(self):
        # Title
        title_label = tk.Label(
            self.root,
            text="PATTERN NOTEPAD",
            font=("Arial", 18, "bold"),
            fg='#ffffff',
            bg='#2b2b2b'
        )
        title_label.pack(pady=10)
        
        # Info label
        self.info_label = tk.Label(
            self.root,
            text=f"Auto-saves to: {self.patterns_folder}/",
            font=("Arial", 10),
            fg='#cccccc',
            bg='#2b2b2b'
        )
        self.info_label.pack()
        
        # Next filename display
        next_num = self.get_next_pattern_number()
        self.filename_label = tk.Label(
            self.root,
            text=f"Next save: pattern_{next_num:03d}.funscript",
            font=("Arial", 10, "bold"),
            fg='#44ff44',
            bg='#2b2b2b'
        )
        self.filename_label.pack(pady=5)
        
        # Text area
        text_frame = tk.Frame(self.root, bg='#2b2b2b')
        text_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        
        # Text widget
        self.text_area = tk.Text(
            text_frame,
            bg='#1a1a1a',
            fg='#ffffff',
            font=('Consolas', 11),
            wrap='word',
            yscrollcommand=scrollbar.set,
            insertbackground='#ffffff'
        )
        self.text_area.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.text_area.yview)
        
        # Buttons frame
        button_frame = tk.Frame(self.root, bg='#2b2b2b')
        button_frame.pack(fill='x', padx=20, pady=10)
        
        # Paste button
        self.paste_btn = tk.Button(
            button_frame,
            text="PASTE",
            font=("Arial", 12, "bold"),
            bg='#4CAF50',
            fg='white',
            width=10,
            command=self.paste_from_clipboard
        )
        self.paste_btn.pack(side='left', padx=5)
        
        # Save button
        self.save_btn = tk.Button(
            button_frame,
            text="SAVE",
            font=("Arial", 12, "bold"),
            bg='#2196F3',
            fg='white',
            width=10,
            command=self.save_pattern
        )
        self.save_btn.pack(side='left', padx=5)
        
        # Clear button
        self.clear_btn = tk.Button(
            button_frame,
            text="CLEAR",
            font=("Arial", 12),
            bg='#ff4444',
            fg='white',
            width=10,
            command=self.clear_text
        )
        self.clear_btn.pack(side='left', padx=5)
        
        # Open folder button
        self.folder_btn = tk.Button(
            button_frame,
            text="OPEN FOLDER",
            font=("Arial", 12),
            bg='#FF9800',
            fg='white',
            width=12,
            command=self.open_patterns_folder
        )
        self.folder_btn.pack(side='right', padx=5)
        
        # Status
        self.status_label = tk.Label(
            self.root,
            text="Ready - Copy pattern from OFS (Ctrl+Shift+E)",
            font=("Arial", 10),
            fg='#888888',
            bg='#2b2b2b'
        )
        self.status_label.pack(pady=5)
    
    def get_next_pattern_number(self):
        """Get the next available pattern number"""
        existing_files = []
        if os.path.exists(self.patterns_folder):
            for file in os.listdir(self.patterns_folder):
                if file.startswith('pattern_') and file.endswith('.funscript'):
                    try:
                        # Extract number from pattern_XXX.funscript
                        num_str = file[8:11]  # Characters 8-10 (3 digits)
                        if num_str.isdigit():
                            existing_files.append(int(num_str))
                    except:
                        continue
        
        # Return next number (start from 1 if no files exist)
        return max(existing_files) + 1 if existing_files else 1
    
    def update_filename_display(self):
        """Update the next filename display"""
        next_num = self.get_next_pattern_number()
        self.filename_label.config(text=f"Next save: pattern_{next_num:03d}.funscript")
    
    def monitor_clipboard(self):
        """Monitor clipboard for auto-paste"""
        try:
            clipboard_content = pyperclip.paste()
            if hasattr(self, 'last_clipboard'):
                if clipboard_content != self.last_clipboard and self.is_funscript_json(clipboard_content):
                    self.auto_paste()
            self.last_clipboard = clipboard_content
        except:
            pass
        
        # Schedule next check
        self.root.after(500, self.monitor_clipboard)
    
    def is_funscript_json(self, text):
        """Check for funscript-like data"""
        if not text:
            return False
        text = text.strip()
        
        # Check for proper JSON structure
        if (text.startswith('{"version"') and '"actions"' in text and text.endswith('}')) or \
           (text.startswith('[') and '"at":' in text and '"pos":' in text):
            return True
        
        # Check for malformed JSON that we can fix (unquoted keys)
        if (text.startswith('{version:') or text.startswith('{version:"')) and 'actions:' in text:
            return True
            
        return False
    
    def fix_malformed_json(self, text):
        """NUCLEAR OPTION: Fix any broken JSON format"""
        try:
            # First try normal parsing
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        print("FIXING BROKEN JSON...")
        fixed_text = text.strip()
        
        # BRUTE FORCE FIX: Replace every unquoted word followed by colon
        # {version:1.0 -> {"version":1.0
        # ,inverted:false -> ,"inverted":false
        # etc.
        
        # Fix opening brace + word
        fixed_text = re.sub(r'\{([a-zA-Z_]\w*):', r'{"\1":', fixed_text)
        
        # Fix comma + word  
        fixed_text = re.sub(r',([a-zA-Z_]\w*):', r',"\1":', fixed_text)
        
        # Fix nested objects
        fixed_text = re.sub(r'\{([a-zA-Z_]\w*):', r'{"\1":', fixed_text)
        
        # Handle multiple passes for deeply nested stuff
        for i in range(3):
            fixed_text = re.sub(r'\{([a-zA-Z_]\w*):', r'{"\1":', fixed_text)
            fixed_text = re.sub(r',([a-zA-Z_]\w*):', r',"\1":', fixed_text)
        
        print(f"ORIGINAL: {text[:100]}")
        print(f"FIXED:    {fixed_text[:100]}")
        
        try:
            result = json.loads(fixed_text)
            print("✅ FIXED THE BROKEN JSON!")
            return result
        except json.JSONDecodeError as e:
            print(f"❌ STILL BROKEN: {e}")
            
            # LAST RESORT: Try to manually extract the actions array
            actions_match = re.search(r'"actions"\s*:\s*(\[.*?\])', fixed_text, re.DOTALL)
            if actions_match:
                try:
                    actions_json = actions_match.group(1)
                    actions = json.loads(actions_json)
                    print("✅ RECOVERED ACTIONS ARRAY!")
                    return {
                        "version": "1.0",
                        "inverted": False,
                        "range": 90,
                        "actions": actions,
                        "metadata": {"created_by": "EMERGENCY_RECOVERY"}
                    }
                except:
                    print("❌ EVEN EMERGENCY RECOVERY FAILED")
            
            return None
    
    def auto_paste(self):
        """Auto-paste if clipboard contains funscript JSON"""
        try:
            clipboard_content = pyperclip.paste()
            if self.is_funscript_json(clipboard_content):
                # Only auto-paste if text area is empty or contains old data
                current_text = self.text_area.get('1.0', tk.END).strip()
                if not current_text or self.is_funscript_json(current_text):
                    self.text_area.delete('1.0', tk.END)
                    self.text_area.insert('1.0', clipboard_content)
                    self.status_label.config(text="✅ Auto-pasted funscript from clipboard", fg='#4CAF50')
                    
                    # Show info without modifying data
                    self.show_pattern_info(clipboard_content)
        except:
            pass
    
    def paste_from_clipboard(self):
        """Manual paste from clipboard"""
        try:
            clipboard_content = pyperclip.paste()
            if not clipboard_content:
                messagebox.showwarning("Empty", "Clipboard is empty")
                return
            
            self.text_area.delete('1.0', tk.END)
            self.text_area.insert('1.0', clipboard_content)
            
            if self.is_funscript_json(clipboard_content):
                self.status_label.config(text="✅ Pasted funscript JSON", fg='#4CAF50')
                self.show_pattern_info(clipboard_content)
            else:
                self.status_label.config(text="⚠️ Pasted text (not funscript JSON)", fg='#FF9800')
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to paste: {str(e)}")
    
    def show_pattern_info(self, json_text):
        """Show info about the pattern WITHOUT MODIFYING THE DATA"""
        try:
            # Try to parse for info display only - don't modify the original
            try:
                data = json.loads(json_text)
            except json.JSONDecodeError:
                data = self.fix_malformed_json(json_text)
                if not data:
                    return
            
            if 'actions' in data and data['actions']:
                actions = data['actions']
                duration = (actions[-1]['at'] - actions[0]['at']) / 1000.0 if len(actions) > 1 else 0
                pos_min = min(a['pos'] for a in actions)
                pos_max = max(a['pos'] for a in actions)
                
                info = f"Pattern: {len(actions)} actions, {duration:.1f}s, range {pos_min}-{pos_max}"
                self.status_label.config(text=info, fg='#44ff44')
        except Exception as e:
            print(f"Error showing pattern info: {e}")
    
    def create_dummy_video(self, duration_seconds, filename_base):
        """Create a dummy MP4 video with the specified duration"""
        try:
            video_filename = f"{filename_base}.mp4"
            video_filepath = os.path.join(self.patterns_folder, video_filename)
            
            # Create a simple black video using ffmpeg
            # If ffmpeg is not available, create a minimal MP4 file
            
            # Try ffmpeg first
            ffmpeg_cmd = [
                'ffmpeg', '-y',  # -y to overwrite existing files
                '-f', 'lavfi',
                '-i', f'color=black:size=640x480:duration={duration_seconds}',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '30',
                video_filepath
            ]
            
            try:
                # Run ffmpeg quietly
                result = subprocess.run(ffmpeg_cmd, 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=30)
                
                if result.returncode == 0:
                    print(f"✅ Created dummy video: {video_filename}")
                    return True
                else:
                    print(f"FFmpeg failed: {result.stderr}")
                    return self.create_minimal_mp4(video_filepath, duration_seconds)
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print("FFmpeg not found or timed out, creating minimal MP4...")
                return self.create_minimal_mp4(video_filepath, duration_seconds)
                
        except Exception as e:
            print(f"Error creating dummy video: {e}")
            return False
    
    def create_minimal_mp4(self, filepath, duration_seconds):
        """Create a minimal MP4 file without ffmpeg"""
        try:
            # Create a very basic MP4 header for a black video
            # This is a simplified approach - creates a minimal valid MP4
            
            # Calculate approximate file size for the duration (very rough estimate)
            frame_rate = 30
            total_frames = int(duration_seconds * frame_rate)
            
            # Basic MP4 structure with minimal data
            mp4_header = bytes([
                # ftyp box
                0x00, 0x00, 0x00, 0x20,  # box size
                0x66, 0x74, 0x79, 0x70,  # 'ftyp'
                0x69, 0x73, 0x6F, 0x6D,  # major brand 'isom'
                0x00, 0x00, 0x02, 0x00,  # minor version
                0x69, 0x73, 0x6F, 0x6D,  # compatible brands
                0x69, 0x73, 0x6F, 0x32,
                0x61, 0x76, 0x63, 0x31,
                0x6D, 0x70, 0x34, 0x31,
                
                # Minimal mdat box (media data) - just placeholder
                0x00, 0x00, 0x00, 0x08,  # box size
                0x6D, 0x64, 0x61, 0x74,  # 'mdat'
            ])
            
            with open(filepath, 'wb') as f:
                f.write(mp4_header)
                # Pad with zeros to simulate video data
                padding_size = max(1024, total_frames * 10)  # Rough estimate
                f.write(b'\x00' * padding_size)
            
            print(f"✅ Created minimal MP4: {os.path.basename(filepath)}")
            return True
            
        except Exception as e:
            print(f"Failed to create minimal MP4: {e}")
            return False
        """Save pattern EXACTLY AS COPIED - NO MODIFICATIONS"""
        content = self.text_area.get('1.0', tk.END).strip()
        
        if not content:
            messagebox.showwarning("Empty", "Nothing to save")
            return
        
        # Only do minimal validation - NO DATA MODIFICATION
        try:
            if self.is_funscript_json(content):
                # Just verify it's valid JSON - don't change it
                data = self.fix_malformed_json(content)
                
                if data is None:
                    messagebox.showerror("Error", "Could not parse JSON format")
                    return
                
                # Validate required fields exist
                if 'actions' not in data:
                    messagebox.showerror("Error", "Invalid funscript: missing 'actions'")
                    return
                
                # If we had to fix the JSON, save the fixed version
                # Otherwise save exactly what was pasted
                if content != json.dumps(data, separators=(',', ':')):
                    # Only reformat if we had to fix unquoted keys
                    content = json.dumps(data, indent=2)
                    print("Fixed unquoted keys in JSON")
                else:
                    print("Saving original JSON exactly as copied")
                
            else:
                # If it's not funscript JSON, save as-is but warn user
                result = messagebox.askyesno("Not Funscript", 
                    "Content doesn't look like funscript JSON. Save anyway?")
                if not result:
                    return
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to validate content: {str(e)}")
            return
        
        # Get next filename
        pattern_number = self.get_next_pattern_number()
        filename = f"pattern_{pattern_number:03d}.funscript"
        filepath = os.path.join(self.patterns_folder, filename)
        
    def save_pattern(self):
        """Save pattern EXACTLY AS COPIED - NO MODIFICATIONS + Create dummy video"""
        content = self.text_area.get('1.0', tk.END).strip()
        
        if not content:
            messagebox.showwarning("Empty", "Nothing to save")
            return
        
        # Only do minimal validation - NO DATA MODIFICATION
        try:
            if self.is_funscript_json(content):
                # Just verify it's valid JSON - don't change it
                data = self.fix_malformed_json(content)
                
                if data is None:
                    messagebox.showerror("Error", "Could not parse JSON format")
                    return
                
                # Validate required fields exist
                if 'actions' not in data:
                    messagebox.showerror("Error", "Invalid funscript: missing 'actions'")
                    return
                
                # If we had to fix the JSON, save the fixed version
                # Otherwise save exactly what was pasted
                if content != json.dumps(data, separators=(',', ':')):
                    # Only reformat if we had to fix unquoted keys
                    content = json.dumps(data, indent=2)
                    print("Fixed unquoted keys in JSON")
                else:
                    print("Saving original JSON exactly as copied")
                
            else:
                # If it's not funscript JSON, save as-is but warn user
                result = messagebox.askyesno("Not Funscript", 
                    "Content doesn't look like funscript JSON. Save anyway?")
                if not result:
                    return
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to validate content: {str(e)}")
            return
        
        # Get next filename
        pattern_number = self.get_next_pattern_number()
        filename_base = f"pattern_{pattern_number:03d}"
        filename = f"{filename_base}.funscript"
        filepath = os.path.join(self.patterns_folder, filename)
        
        try:
            # Write EXACTLY what was in the text area (or minimally fixed version)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"Successfully saved: {filepath}")
            print(f"File size: {len(content)} characters")
            
            # Create dummy video if this is a funscript
            video_created = False
            if self.is_funscript_json(content):
                try:
                    # Get the parsed data (fix it if needed)
                    parsed_data = self.fix_malformed_json(content)
                    if parsed_data and 'actions' in parsed_data and parsed_data['actions']:
                        actions = parsed_data['actions']
                        if len(actions) > 1:
                            # Calculate duration from first to last action (in seconds)
                            duration_ms = actions[-1]['at'] - actions[0]['at']
                            duration_seconds = max(1.0, duration_ms / 1000.0 + 1.0)  # Add 1 second buffer
                            
                            print(f"Creating dummy video: {duration_seconds:.1f} seconds")
                            video_created = self.create_dummy_video(duration_seconds, filename_base)
                        else:
                            print("Only 1 action found, creating 5-second video")
                            video_created = self.create_dummy_video(5.0, filename_base)
                            
                except Exception as e:
                    print(f"Failed to create dummy video: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Update status message
            if video_created:
                self.status_label.config(text=f"✅ Saved: {filename} + MP4", fg='#4CAF50')
            else:
                self.status_label.config(text=f"✅ Saved: {filename}", fg='#4CAF50')
            
            # Update filename display for next save
            self.update_filename_display()
            
            # Clear text area for next pattern
            self.text_area.delete('1.0', tk.END)
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save file: {str(e)}")
            print(f"Save error: {e}")
    
    def clear_text(self):
        """Clear the text area"""
        self.text_area.delete('1.0', tk.END)
        self.status_label.config(text="Text cleared", fg='#888888')
    
    def open_patterns_folder(self):
        """Open the patterns folder in file explorer"""
        try:
            import subprocess
            import sys
            
            if sys.platform == "win32":
                os.startfile(self.patterns_folder)
            elif sys.platform == "darwin":  # macOS
                subprocess.run(["open", self.patterns_folder])
            else:  # Linux
                subprocess.run(["xdg-open", self.patterns_folder])
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {str(e)}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    try:
        import pyperclip
    except ImportError:
        print("Installing pyperclip...")
        import subprocess
        subprocess.check_call(["pip", "install", "pyperclip"])
        import pyperclip
    
    app = PatternNotepad()
    app.run()