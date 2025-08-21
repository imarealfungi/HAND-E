import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
import os
import random
from collections import deque
import pygame
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter.simpledialog
import shutil
import uuid
try:
    from PyQt5.QtWidgets import QApplication, QSplashScreen, QLabel
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtGui import QPixmap, QPainter
    PYQT_AVAILABLE = True
except ImportError:
    print("⚠️ PyQt5 not installed. Install with: pip install PyQt5")
    PYQT_AVAILABLE = False


# Import your working device handler
from device_handler import IntifaceClient


class MoansManager:
    """Background moans audio manager with continuous playback"""
    
    def __init__(self):
        self.moans_folder = "moans"
        self.moans_files = []
        self.enabled = False
        self.volume = 0.8
        self.current_sound = None
        self.moans_channel = None
        
        # Initialize pygame mixer for moans (separate channel)
        try:
            # Use channel 1 for moans (channel 0 is for voice)
            self.moans_channel = pygame.mixer.Channel(1)
            print("🎵 Moans system initialized")
        except Exception as e:
            print(f"⚠️ Moans init failed: {e}")
        
        # Load moans files
        self.load_moans_files()
        
        # Start background thread
        self.running = False
        self.start_background_player()
    
    def load_moans_files(self):
        """Load all WAV files from moans folder"""
        self.moans_files = []
        
        if os.path.exists(self.moans_folder):
            for file in os.listdir(self.moans_folder):
                if file.lower().endswith('.wav'):
                    file_path = os.path.join(self.moans_folder, file)
                    self.moans_files.append(file_path)
        
        print(f"💕 Loaded {len(self.moans_files)} moans files")
    
    def set_enabled(self, enabled):
        """Enable/disable moans playback"""
        self.enabled = enabled
        if not enabled and self.moans_channel:
            self.moans_channel.stop()
        print(f"💕 Moans: {'ENABLED' if enabled else 'DISABLED'}")
    
    def set_volume(self, volume):
        """Set moans volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        if self.current_sound:
            self.current_sound.set_volume(self.volume)
    
    def start_background_player(self):
        """Start background moans player thread"""
        self.running = True
        threading.Thread(target=self._background_loop, daemon=True).start()
    
    def stop_background_player(self):
        """Stop background player"""
        self.running = False
        if self.moans_channel:
            self.moans_channel.stop()
    
    def _background_loop(self):
        """Background loop that plays moans continuously"""
        while self.running:
            try:
                if (self.enabled and 
                    self.moans_files and 
                    self.moans_channel and 
                    not self.moans_channel.get_busy()):
                    
                    # Pick random moans file
                    moans_file = random.choice(self.moans_files)
                    
                    # Load and play
                    try:
                        self.current_sound = pygame.mixer.Sound(moans_file)
                        self.current_sound.set_volume(self.volume)
                        self.moans_channel.play(self.current_sound)
                        print(f"💕 Playing: {os.path.basename(moans_file)}")
                    except Exception as e:
                        print(f"⚠️ Error playing moans: {e}")
                
                # Check every 100ms
                time.sleep(0.1)
                
            except Exception as e:
                print(f"⚠️ Moans loop error: {e}")
                time.sleep(1)

class VideoGallery:
    """Enhanced Video gallery manager with thumbnail generation"""
    
    def __init__(self):
        self.videos = []
        self.current_index = 0
        self.gallery_page = 0
        self.videos_per_page = 5
        self.gallery_folder = "gallery"
        
        # Thumbnail settings - MUCH BIGGER!
        self.thumbnail_size = (400, 300)  # MUCH BIGGER thumbnails!  
        
        # Create gallery folders
        self.ensure_gallery_folders()
        
        # Load existing gallery
        self.load_gallery()
    
    def ensure_gallery_folders(self):
        """Create gallery folders if they don't exist"""
        folders = [
            self.gallery_folder,
            os.path.join(self.gallery_folder, "videos"),
            os.path.join(self.gallery_folder, "thumbnails")
        ]
        
        for folder in folders:
            if not os.path.exists(folder):
                os.makedirs(folder)
                print(f"📁 Created folder: {folder}")
    
    def generate_thumbnail(self, video_path, output_path):
        """Generate thumbnail from video file"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"❌ Could not open video: {video_path}")
                return False
            
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Seek to middle of video for thumbnail
            middle_frame = total_frames // 2
            cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                print(f"❌ Could not read frame from video: {video_path}")
                return False
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Create PIL Image and resize
            pil_image = Image.fromarray(frame_rgb)
            pil_image = pil_image.resize(self.thumbnail_size, Image.Resampling.LANCZOS)
            
            # Save thumbnail
            pil_image.save(output_path, "PNG")
            print(f"✅ Generated thumbnail: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Thumbnail generation error: {e}")
            return False
    
    def load_gallery(self):
        """Load gallery from JSON file"""
        try:
            gallery_file = os.path.join(self.gallery_folder, "gallery.json")
            if os.path.exists(gallery_file):
                with open(gallery_file, 'r') as f:
                    data = json.load(f)
            
                # Handle both old and new format
                if isinstance(data, list):
                    # Old format - just videos list
                    self.videos = data
                    self.current_index = 0
                    self.gallery_page = 0
                else:
                    # New format - with saved positions
                    self.videos = data.get('videos', [])
                    self.current_index = data.get('current_index', 0)
                    self.gallery_page = data.get('gallery_page', 0)
                
                    # Validate indices
                    if self.current_index >= len(self.videos):
                        self.current_index = 0
            
                print(f"📚 Loaded {len(self.videos)} videos from gallery")
            
                # Regenerate missing thumbnails
                self.check_and_regenerate_thumbnails()
            else:
                self.videos = []
                self.current_index = 0
                self.gallery_page = 0
        except Exception as e:
            print(f"⚠️ Error loading gallery: {e}")
            self.videos = []
            self.current_index = 0
            self.gallery_page = 0
    
    def check_and_regenerate_thumbnails(self):
        """Check for missing thumbnails and regenerate them"""
        for video in self.videos:
            thumbnail_path = video.get('thumbnail_path')
            if not thumbnail_path or not os.path.exists(thumbnail_path):
                # Generate new thumbnail
                video_file = video.get('file_path')
                if video_file and os.path.exists(video_file):
                    thumbnail_filename = f"thumb_{video['id']}.png"
                    thumbnail_path = os.path.join(self.gallery_folder, "thumbnails", thumbnail_filename)
                    
                    if self.generate_thumbnail(video_file, thumbnail_path):
                        video['thumbnail_path'] = thumbnail_path
                        print(f"🔄 Regenerated thumbnail for: {video['name']}")
        
        # Save updated gallery
        self.save_gallery()
    
    def save_gallery(self):
        """Save gallery to JSON file"""
        try:
            gallery_file = os.path.join(self.gallery_folder, "gallery.json")
            gallery_data = {
                'videos': self.videos,
                'current_index': self.current_index,    # ADD THIS LINE
                'gallery_page': self.gallery_page       # ADD THIS LINE TOO
            }
            with open(gallery_file, 'w') as f:
                json.dump(gallery_data, f, indent=2)
            print(f"💾 Saved gallery with {len(self.videos)} videos")
        except Exception as e:
            print(f"⚠️ Error saving gallery: {e}")
    
    def add_video(self, video_path, name, direction, invert):
        """Add a new video to the gallery with thumbnail generation"""
        video_id = str(uuid.uuid4())[:8]
        filename = f"video_{video_id}.mp4"
        thumbnail_filename = f"thumb_{video_id}.png"
        
        try:
            # Copy video to gallery folder
            dest_path = os.path.join(self.gallery_folder, "videos", filename)
            shutil.copy2(video_path, dest_path)
            
            # Generate thumbnail
            thumbnail_path = os.path.join(self.gallery_folder, "thumbnails", thumbnail_filename)
            thumbnail_generated = self.generate_thumbnail(video_path, thumbnail_path)
            
            # Create video entry
            video_entry = {
                'id': video_id,
                'name': name,
                'file_path': dest_path,
                'original_path': video_path,
                'direction': direction,
                'invert': invert,
                'created': time.strftime("%Y-%m-%d %H:%M:%S"),
                'thumbnail_path': thumbnail_path if thumbnail_generated else None
            }
            
            self.videos.append(video_entry)
            self.save_gallery()
            
            print(f"✅ Saved video: {name} (with thumbnail: {thumbnail_generated})")
            return True
            
        except Exception as e:
            print(f"❌ Error saving video: {e}")
            return False
    
    def delete_video(self, video_id):
        """Delete a video from gallery including thumbnail"""
        try:
            video = next((v for v in self.videos if v['id'] == video_id), None)
            if video:
                # Delete video file
                if os.path.exists(video['file_path']):
                    os.remove(video['file_path'])
                
                # Delete thumbnail file
                thumbnail_path = video.get('thumbnail_path')
                if thumbnail_path and os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
                
                # Remove from list
                self.videos.remove(video)
                
                # Adjust current index
                if self.current_index >= len(self.videos):
                    self.current_index = max(0, len(self.videos) - 1)
                
                self.save_gallery()
                print(f"🗑️ Deleted video and thumbnail: {video['name']}")
                return True
        except Exception as e:
            print(f"❌ Error deleting video: {e}")
        return False
    
    def get_thumbnail_image(self, video_id, default_size=(200, 150)):
        """Get PIL Image for thumbnail, with fallback - BIGGER SIZE"""
        try:
            video = next((v for v in self.videos if v['id'] == video_id), None)
            if not video:
                return self.create_placeholder_thumbnail("Not Found", default_size)
            
            thumbnail_path = video.get('thumbnail_path')
            if thumbnail_path and os.path.exists(thumbnail_path):
                # Load existing thumbnail
                thumbnail = Image.open(thumbnail_path)
                # Ensure correct size
                if thumbnail.size != default_size:
                    thumbnail = thumbnail.resize(default_size, Image.Resampling.LANCZOS)
                return thumbnail
            else:
                # Try to regenerate thumbnail
                video_file = video.get('file_path')
                if video_file and os.path.exists(video_file):
                    thumbnail_filename = f"thumb_{video['id']}.png"
                    thumbnail_path = os.path.join(self.gallery_folder, "thumbnails", thumbnail_filename)
                    
                    if self.generate_thumbnail(video_file, thumbnail_path):
                        video['thumbnail_path'] = thumbnail_path
                        self.save_gallery()
                        
                        thumbnail = Image.open(thumbnail_path)
                        if thumbnail.size != default_size:
                            thumbnail = thumbnail.resize(default_size, Image.Resampling.LANCZOS)
                        return thumbnail
                
                # Fallback to placeholder
                return self.create_placeholder_thumbnail(video['name'][:10], default_size)
                
        except Exception as e:
            print(f"⚠️ Error loading thumbnail: {e}")
            return self.create_placeholder_thumbnail("Error", default_size)
    
    def create_placeholder_thumbnail(self, text, size=(200, 150)):
        """Create a placeholder thumbnail with text - BIGGER SIZE"""
        try:
            from PIL import ImageDraw, ImageFont
            
            # Create dark image
            image = Image.new('RGB', size, (68, 68, 68))  # Dark gray
            draw = ImageDraw.Draw(image)
            
            # Try to load a font - BIGGER for bigger thumbnails
            try:
                font = ImageFont.truetype("arial.ttf", 16)  # Increased from 12
            except:
                font = ImageFont.load_default()
            
            # Draw text centered
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (size[0] - text_width) // 2
            y = (size[1] - text_height) // 2
            
            draw.text((x, y), text, fill=(200, 200, 200), font=font)
            
            # Draw border
            draw.rectangle([0, 0, size[0]-1, size[1]-1], outline=(100, 100, 100), width=1)
            
            return image
            
        except Exception as e:
            print(f"⚠️ Error creating placeholder: {e}")
            # Return solid color image as last resort
            return Image.new('RGB', size, (68, 68, 68))
    
    # ... (keep all other existing methods like get_current_video, next_video, etc.)
    def get_current_video(self):
        """Get currently selected video"""
        if 0 <= self.current_index < len(self.videos):
            return self.videos[self.current_index]
        return None
    
    def get_visible_videos(self):
        """Get videos visible in current gallery page"""
        start_idx = self.gallery_page * self.videos_per_page
        end_idx = start_idx + self.videos_per_page
        return self.videos[start_idx:end_idx]
    
    def next_video(self):
        """Navigate to next video"""
        if self.videos and self.current_index < len(self.videos) - 1:
            self.current_index += 1
            return True
        return False
    
    def prev_video(self):
        """Navigate to previous video"""
        if self.videos and self.current_index > 0:
            self.current_index -= 1
            return True
        return False
    
    def next_gallery_page(self):
        """Navigate to next gallery page"""
        max_page = (len(self.videos) - 1) // self.videos_per_page
        if self.gallery_page < max_page:
            self.gallery_page += 1
            return True
        return False
    
    def prev_gallery_page(self):
        """Navigate to previous gallery page"""
        if self.gallery_page > 0:
            self.gallery_page -= 1
            return True
        return False
    
class EnhancedAudioManager:
    """Enhanced Audio manager with smart cooldowns"""
    
    def __init__(self):
        self.audio_enabled = False
        self.volume = 0.7
        self.base_audio_folder = "processed_voices"
        self.current_voice = "PIPER"
        self.available_voices = []
        
        # Cooldown tracking
        self.last_trigger_time = {}
        self.last_position = 50.0
        self.last_speed = 1.0
        
        # Initialize pygame mixer
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(8)
            print("🔊 Enhanced audio system initialized")
        except Exception as e:
            print(f"⚠️ Audio init failed: {e}")
            self.audio_enabled = False
        
        # All trigger mappings (your 88 triggers)
        self.trigger_mappings = {
            'device_connect': 'device_connect',
            'device_disconnect': 'device_disconnect', 
            'device_scanning': 'device_scanning',
            'start_playback': 'start_playback',
            'stop_playback': 'stop_playback',
            'emergency_stop': 'emergency_stop',
            'manual_start': 'manual_start',
            'manual_stop': 'manual_stop',
            'speed_change_manual': 'speed_change_manual',
            'speed_change_joystick': 'speed_change_joystick',
            'buildup_start': 'buildup_start',
            'buildup_stop': 'buildup_stop',
            'buildup_complete': 'buildup_complete',
            'video_loaded': 'video_loaded',
            'video_save': 'video_save',
            'video_delete': 'video_delete',
            'pattern_skip': 'pattern_skip',
            'joystick_config_applied': 'joystick_config_applied',
            'joystick_detection_success': 'joystick_detection_success',
            'joystick_detection_failed': 'joystick_detection_failed',
            'error_playback': 'error_playback',
            'error_joystick': 'error_joystick',
            'patterns_loaded': 'patterns_loaded',
            'app_startup': 'app_startup',
            'voice_changed': 'voice_changed',
            'category_change': 'category_change',
            'manual_position_update': 'manual_position_update',
            'sticker_added': 'sticker_added',
            'sticker_deleted': 'sticker_deleted',
            'gallery_next': 'gallery_next',
            'gallery_prev': 'gallery_prev'
            # Add more as needed
        }
        
        self.loaded_sounds = {}
        self.scan_available_voices()
        self.load_voice_sounds()
    
    def can_play(self, trigger):
        """Simple cooldown check - prevents spam"""
        import time
        current_time = time.time()
        last_time = self.last_trigger_time.get(trigger, 0)
        
        # Basic cooldowns
        cooldowns = {
            'speed_change_manual': 1.5,
            'speed_change_joystick': 1.5,
            'manual_position_update': 3.0,
            'video_save': 2.0,
            'category_change': 3.0
        }
        
        cooldown = cooldowns.get(trigger, 0.5)  # Default 0.5s
        return (current_time - last_time) >= cooldown
    
    def scan_available_voices(self):
        """Scan for available voice folders"""
        self.available_voices = []
        
        if os.path.exists(self.base_audio_folder):
            for item in os.listdir(self.base_audio_folder):
                voice_path = os.path.join(self.base_audio_folder, item)
                if os.path.isdir(voice_path):
                    self.available_voices.append(item)
        
        if not self.available_voices:
            self.available_voices = ["default"]
        
        print(f"🎭 Found voices: {self.available_voices}")
    
    def set_voice(self, voice_name):
        """Set the current voice"""
        if voice_name in self.available_voices:
            self.current_voice = voice_name
            self.load_voice_sounds()
            self.play('voice_changed', force=True)
            print(f"🎭 Voice changed to: {voice_name}")
            return True
        return False
    
    def load_voice_sounds(self):
        """Load sounds for current voice"""
        self.loaded_sounds = {}
        
        if self.current_voice == "default":
            print("🔇 Using default voice (no audio)")
            return
        
        voice_path = os.path.join(self.base_audio_folder, self.current_voice)
        if not os.path.exists(voice_path):
            print(f"❌ Voice folder not found: {voice_path}")
            return
        
        loaded_count = 0
        for trigger_key, folder_name in self.trigger_mappings.items():
            folder_path = os.path.join(voice_path, folder_name)
            
            if os.path.exists(folder_path):
                wav_files = [f for f in os.listdir(folder_path) if f.endswith('.wav')]
                
                if wav_files:
                    trigger_sounds = []
                    for wav_file in wav_files:
                        try:
                            sound_path = os.path.join(folder_path, wav_file)
                            sound = pygame.mixer.Sound(sound_path)
                            sound.set_volume(self.volume)
                            trigger_sounds.append(sound)
                            loaded_count += 1
                        except Exception as e:
                            print(f"❌ Failed to load {wav_file}: {e}")
                    
                    if trigger_sounds:
                        self.loaded_sounds[trigger_key] = trigger_sounds
        
        print(f"✅ Loaded {loaded_count} audio files for voice '{self.current_voice}'")
    
    def play(self, trigger, force=False):
        """Play audio for trigger"""
        if not self.audio_enabled or self.current_voice == "default":
            return
        
        # Check cooldowns unless forced
        if not force and not self.can_play(trigger):
            return
        
        if trigger in self.loaded_sounds:
            try:
                sounds = self.loaded_sounds[trigger]
                if sounds:
                    sound = random.choice(sounds) if len(sounds) > 1 else sounds[0]
                    sound.play()
                    
                    # Update last trigger time
                    import time
                    self.last_trigger_time[trigger] = time.time()
                    
                    print(f"🔊 Playing: {trigger}")
            except Exception as e:
                print(f"❌ Audio play error: {e}")
    
    def set_volume(self, volume):
        """Set volume for all sounds"""
        self.volume = max(0.0, min(1.0, volume))
        for trigger_sounds in self.loaded_sounds.values():
            for sound in trigger_sounds:
                sound.set_volume(self.volume)
    
    def toggle_enabled(self):
        """Toggle audio on/off"""
        self.audio_enabled = not self.audio_enabled
        return self.audio_enabled
    
    def get_available_voices(self):
        """Get list of available voices"""
        return self.available_voices

class AudioDeviceManager:
    """Manages audio output device selection with real device names"""
    
    def __init__(self):
        self.available_devices = []
        self.current_device = None
        self.scan_audio_devices()
    
    def scan_audio_devices(self):
        """Scan for available audio output devices with real names"""
        try:
            self.available_devices = ["Default System Output"]  # Always have default
            
            if os.name == 'nt':  # Windows
                self._scan_windows_devices()
            else:  # Linux/Mac
                self._scan_unix_devices()
            
            print(f"🔊 Found {len(self.available_devices)} audio devices")
            for i, device in enumerate(self.available_devices):
                print(f"  {i}: {device}")
                
        except Exception as e:
            print(f"⚠️ Audio device scan failed: {e}")
            self.available_devices = ["Default System Output"]
    
    def _scan_windows_devices(self):
        """Scan Windows audio devices using WMI"""
        try:
            # Method 1: Try WMI (most accurate)
            import subprocess
            result = subprocess.run([
                'powershell', '-Command',
                'Get-CimInstance -ClassName Win32_SoundDevice | Select-Object Name'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[3:]  # Skip headers
                for line in lines:
                    device_name = line.strip()
                    if device_name and device_name != "----":
                        self.available_devices.append(device_name)
                        
        except Exception as e:
            print(f"⚠️ WMI scan failed: {e}")
            
        try:
            # Method 2: Try Windows Registry for more devices
            import winreg
            
            # Common audio device registry paths
            paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render",
                r"SYSTEM\CurrentControlSet\Control\Class\{4d36e96c-e325-11ce-bfc1-08002be10318}"
            ]
            
            for path in paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            subkey = winreg.OpenKey(key, subkey_name)
                            
                            # Try to get device description
                            try:
                                name, _ = winreg.QueryValueEx(subkey, "DeviceDesc")
                                if name and name not in self.available_devices:
                                    # Clean up the name
                                    clean_name = name.split(';')[-1] if ';' in name else name
                                    self.available_devices.append(clean_name)
                            except:
                                pass
                                
                            winreg.CloseKey(subkey)
                            i += 1
                        except WindowsError:
                            break
                    winreg.CloseKey(key)
                except:
                    continue
                    
        except Exception as e:
            print(f"⚠️ Registry scan failed: {e}")
        
        # Method 3: Try DirectSound enumeration
        try:
            # Add some common device patterns if nothing else worked
            if len(self.available_devices) <= 1:
                common_devices = [
                    "Realtek High Definition Audio",
                    "Conexant HD Audio",
                    "VIA HD Audio",
                    "Creative Sound Blaster",
                    "USB Audio Device",
                    "Bluetooth Audio",
                    "HDMI Audio"
                ]
                self.available_devices.extend(common_devices)
                
        except Exception as e:
            print(f"⚠️ Fallback device detection failed: {e}")
    
    def _scan_unix_devices(self):
        """Scan Linux/Mac audio devices"""
        try:
            if os.path.exists('/proc/asound/cards'):  # Linux ALSA
                with open('/proc/asound/cards', 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if ':' in line and not line.strip().startswith('#'):
                            parts = line.split(':', 1)
                            if len(parts) > 1:
                                device_name = parts[1].strip()
                                if device_name:
                                    self.available_devices.append(f"ALSA: {device_name}")
            
            # Try PulseAudio
            try:
                import subprocess
                result = subprocess.run(['pactl', 'list', 'short', 'sinks'], 
                                      capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            parts = line.split('\t')
                            if len(parts) > 1:
                                self.available_devices.append(f"PulseAudio: {parts[1]}")
            except:
                pass
                
            # Mac CoreAudio (basic)
            if os.uname().sysname == 'Darwin':
                self.available_devices.extend([
                    "Built-in Output",
                    "Built-in Speakers", 
                    "Built-in Headphones",
                    "AirPods",
                    "USB Audio"
                ])
                
        except Exception as e:
            print(f"⚠️ Unix device scan failed: {e}")
    
    def set_device(self, device_name):
        """Set the current audio output device"""
        if device_name in self.available_devices:
            self.current_device = device_name
            print(f"🔊 Audio output: {device_name}")
            
            # For now, just reinitialize pygame mixer
            # Real device switching would require platform-specific APIs
            try:
                pygame.mixer.quit()
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                pygame.mixer.set_num_channels(8)
                return True
            except Exception as e:
                print(f"⚠️ Failed to reinitialize audio: {e}")
                return False
        return False
    
    def get_available_devices(self):
        """Get list of available devices"""
        return self.available_devices

class JoystickController:
    """Universal joystick controller with invert, half-axis support, and video navigation"""
    
    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        
        self.device = None
        self.running = False
        
        # Configuration - INCLUDING NEW VIDEO BUTTONS
        self.speed_axis = -1
        self.manual_axis = -1
        self.manual_override_button = -1
        self.skip_pattern_button = -1
        self.play_pause_button = -1
        self.next_video_button = -1      # 🔧 NEW
        self.prev_video_button = -1      # 🔧 NEW
        
        # Enhanced options
        self.axis_invert = False
        self.manual_axis_invert = False
        self.speed_axis_mode = "full_range"  # full_range, half_positive, half_negative, trigger
        self.manual_axis_mode = "full_range"
        self.deadzone = 0.02
        
        # State tracking
        self.current_speed_multiplier = 1.0
        self.manual_override_active = False
        self.manual_position = 0.5
        
        # Button states for edge detection - INCLUDING NEW VIDEO BUTTONS
        self.last_manual_button = False
        self.last_skip_button = False
        self.last_play_pause_button = False
        self.last_next_video_button = False    # ✅ FIXED: Added missing variable
        self.last_prev_video_button = False    # ✅ FIXED: Added missing variable
        
        # Callbacks - INCLUDING NEW VIDEO CALLBACKS
        self.speed_callback = None
        self.manual_override_callback = None
        self.skip_pattern_callback = None
        self.play_pause_callback = None
        self.next_video_callback = None        # 🔧 NEW
        self.prev_video_callback = None        # 🔧 NEW
        
        # Available devices
        self.available_devices = []
        self.refresh_devices()
        
    def refresh_devices(self):
        """Refresh list of available joystick devices"""
        self.available_devices = []
        
        pygame.joystick.quit()
        pygame.joystick.init()
        
        device_count = pygame.joystick.get_count()
        print(f"🎮 Found {device_count} joystick device(s)")
        
        for i in range(device_count):
            device = pygame.joystick.Joystick(i)
            device.init()
            
            device_info = {
                'id': i,
                'name': device.get_name(),
                'axes': device.get_numaxes(),
                'buttons': device.get_numbuttons(),
                'device': device
            }
            
            self.available_devices.append(device_info)
            print(f"Joystick {i}: {device.get_name()} (Axes: {device.get_numaxes()}, Buttons: {device.get_numbuttons()})")
        
        return self.available_devices
    
    def select_device(self, device_id):
        """Select joystick device by ID"""
        if 0 <= device_id < len(self.available_devices):
            if self.device:
                self.device.quit()
            
            self.device = self.available_devices[device_id]['device']
            print(f"✅ Selected joystick: {self.device.get_name()}")
            return True
        return False
    
    def configure(self, speed_axis, manual_axis, manual_button, skip_button, play_pause_button, 
                 next_video_button, prev_video_button,  # 🔧 NEW PARAMETERS
                 axis_invert=False, manual_axis_invert=False, 
                 speed_mode="full_range", manual_mode="full_range"):
        """Configure joystick controls with invert, half-axis, and video navigation"""
        self.speed_axis = speed_axis
        self.manual_axis = manual_axis
        self.manual_override_button = manual_button
        self.skip_pattern_button = skip_button
        self.play_pause_button = play_pause_button
        self.next_video_button = next_video_button        # 🔧 NEW
        self.prev_video_button = prev_video_button        # 🔧 NEW
        self.axis_invert = axis_invert
        self.manual_axis_invert = manual_axis_invert
        self.speed_axis_mode = speed_mode
        self.manual_axis_mode = manual_mode
        
        print(f"🎮 Config - Speed: Axis{speed_axis} (invert:{axis_invert}, mode:{speed_mode})")
        print(f"🎮 Config - Manual: Axis{manual_axis} (invert:{manual_axis_invert}, mode:{manual_mode})")
        print(f"🎮 Config - Buttons: Manual:{manual_button}, Skip:{skip_button}, Play/Pause:{play_pause_button}")
        print(f"🎮 Config - Video: Next:{next_video_button}, Previous:{prev_video_button}")  # 🔧 NEW
    
    def _map_axis_value(self, raw_value, mode="full_range", invert=False):
        """Map axis value with invert and half-axis modes - FIXED"""
        # Apply inversion
        if invert:
            raw_value = -raw_value

        # Apply deadzone
        if abs(raw_value) < self.deadzone:
            raw_value = 0.0

        # Map based on mode
        if mode == "half_positive":
            # FIXED: For your control - neutral=100%, pull=0%
            if raw_value >= 0:
                return 1.0 - raw_value  # 0 → 1.0 (100%), +1 → 0.0 (0%)
            else:
                return 1.0  # Any negative input = 100%
            
        elif mode == "half_negative":
            # Only negative: 0 to -1 maps to 0.0 to 1.0, positive stays at 0.0
            if raw_value <= 0:
                return abs(raw_value)  # 0 → 0.0, -1 → 1.0
            else:
                return 0.0  # Any positive input = shallowest
            
        elif mode == "trigger":
            # Trigger mode: Neutral (-1) = 0%, Fully pressed (+1) = 100%
            return (raw_value + 1.0) / 2.0  # -1 → 0.0, +1 → 1.0
        
        else:
            # Full range: -1 to +1 maps to 0.0 to 1.0
            return (raw_value + 1.0) / 2.0
    
    def set_callbacks(self, speed_callback=None, manual_callback=None, skip_callback=None, 
                     play_pause_callback=None, next_video_callback=None, prev_video_callback=None):  # 🔧 NEW PARAMS
        """Set callback functions"""
        self.speed_callback = speed_callback
        self.manual_override_callback = manual_callback
        self.skip_pattern_callback = skip_callback
        self.play_pause_callback = play_pause_callback
        self.next_video_callback = next_video_callback      # 🔧 NEW
        self.prev_video_callback = prev_video_callback      # 🔧 NEW
    
    def start(self):
        """Start joystick monitoring"""
        if not self.device:
            print("⚠️ No joystick device selected!")
            return False
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_joystick, daemon=True)
        self.monitor_thread.start()
        print("🎮 Joystick monitoring started")
        return True
    
    def stop(self):
        """Stop joystick monitoring"""
        self.running = False
        if self.device:
            self.device.quit()
    
    def get_current_speed_multiplier(self):
        """Get current smoothed speed multiplier"""
        return self.current_speed_multiplier
    
    def is_manual_override_active(self):
        """Check if manual override is currently active"""
        return self.manual_override_active
    
    def get_manual_position(self):
        """Get current manual control position (0.0-1.0)"""
        return self.manual_position
    
    def _monitor_joystick(self):
        """Monitor joystick input - FIXED VERSION with no duplicates"""
        print(f"🎮 Starting joystick monitoring: {self.device.get_name()}")

        while self.running:
            try:
                # CRITICAL: Update pygame events first
                pygame.event.pump()
    
                if not self.device:
                    time.sleep(0.01)
                    continue
    
                # Play/pause button detection
                if self.play_pause_button >= 0 and self.play_pause_button < self.device.get_numbuttons():
                    current_play_pause = self.device.get_button(self.play_pause_button)
                    if current_play_pause and not self.last_play_pause_button:
                        print("🎮 PLAY/PAUSE PRESSED!")
                        if self.play_pause_callback:
                            self.play_pause_callback()
                    self.last_play_pause_button = current_play_pause

                # ✅ FIXED: Next video button detection (remove duplicate)
                if self.next_video_button >= 0 and self.next_video_button < self.device.get_numbuttons():
                    current_next_video = self.device.get_button(self.next_video_button)
                    if current_next_video and not self.last_next_video_button:
                        print("🎬 NEXT VIDEO PRESSED!")
                        if self.next_video_callback:
                            self.next_video_callback()
                    self.last_next_video_button = current_next_video

                # ✅ FIXED: Previous video button detection (remove duplicate)
                if self.prev_video_button >= 0 and self.prev_video_button < self.device.get_numbuttons():
                    current_prev_video = self.device.get_button(self.prev_video_button)
                    if current_prev_video and not self.last_prev_video_button:
                        print("🎬 PREVIOUS VIDEO PRESSED!")
                        if self.prev_video_callback:
                            self.prev_video_callback()
                    self.last_prev_video_button = current_prev_video

                # Manual override button detection
                if self.manual_override_button >= 0 and self.manual_override_button < self.device.get_numbuttons():
                    current_manual = self.device.get_button(self.manual_override_button)
        
                    if current_manual != self.last_manual_button:
                        if current_manual:
                            self.manual_override_active = True
                            print("🎮 MANUAL OVERRIDE ACTIVE")
                            if self.manual_override_callback:
                                self.manual_override_callback(True, self.manual_position)
                        else:
                            self.manual_override_active = False
                            print("🎮 MANUAL OVERRIDE RELEASED")
                            if self.manual_override_callback:
                                self.manual_override_callback(False, self.manual_position)
        
                    self.last_manual_button = current_manual
    
                # Skip pattern button detection
                if self.skip_pattern_button >= 0 and self.skip_pattern_button < self.device.get_numbuttons():
                    current_skip = self.device.get_button(self.skip_pattern_button)
                    if current_skip and not self.last_skip_button:
                        print("⭐ SKIP PATTERN PRESSED")
                        if self.skip_pattern_callback:
                            self.skip_pattern_callback()
                    self.last_skip_button = current_skip
    
                # Speed axis control (existing code)
                if not self.manual_override_active and self.speed_axis >= 0 and self.speed_axis < self.device.get_numaxes():
                    raw_speed_axis = self.device.get_axis(self.speed_axis)
            
                    if abs(raw_speed_axis) > 0.2:
                        mapped_value = self._map_axis_value(raw_speed_axis, self.speed_axis_mode, self.axis_invert)
                
                        if self.speed_axis_mode in ["half_positive", "half_negative"]:
                            new_speed = 0.1 + (mapped_value * 1.4)
                        else:
                            if mapped_value <= 0.5:
                                new_speed = 0.1 + (mapped_value * 1.4)
                            else:
                                new_speed = 0.8 + ((mapped_value - 0.5) * 1.4)
                
                        new_speed = max(0.1, min(1.5, new_speed))
                
                        if self.speed_callback:
                            self.speed_callback(new_speed, raw_speed_axis)
    
                # Manual position axis (existing code)
                if self.manual_override_active and self.manual_axis >= 0 and self.manual_axis < self.device.get_numaxes():
                    raw_manual_axis = self.device.get_axis(self.manual_axis)
        
                    self.manual_position = self._map_axis_value(raw_manual_axis, self.manual_axis_mode, self.manual_axis_invert)
                    self.manual_position = max(0.0, min(1.0, self.manual_position))
        
                    if self.manual_override_callback:
                       self.manual_override_callback(True, self.manual_position)
    
                # 200Hz polling rate
                time.sleep(0.005)
    
            except Exception as e:
               print(f"⚠️ Joystick error: {e}")
               time.sleep(0.1)

               
class PatternSequencer:
    """AI-driven pattern sequencer - FIXED TRANSITION PAUSES"""
    
    def __init__(self):
        self.pattern_database = {}
        
        # FIXED motion stream - NO GAPS
        self.motion_stream = deque()
        self.stream_target_duration = 8000  # 8 seconds buffer
        self.last_command_time = 0
        
        # Manual override state
        self.manual_override_active = False
        self.manual_return_position = 0.5
        
        # Speed control
        self.base_speed = 0.75
        self.joystick_speed_multiplier = 1.0
        
        # Build-up mode
        self.buildup_mode = False
        self.buildup_duration = 300
        self.buildup_start_time = None
        self.buildup_start_speed = 0.3
        self.buildup_end_speed = 2.0
        self.buildup_cycles = 1
        self.current_buildup_cycle = 0

        self.cycle_folders = False
        self.trigger_type = "time" 
        self.interval_value = "2:00"
        self.folder_change_counter = 0
        self.last_folder_change = time.time()
        
        # Pattern tracking
        self.current_pattern = None
        self.pattern_history = deque(maxlen=5)
        
        # Load patterns
        self.load_patterns("BLOWJOB")

        # ADD THESE CHAOS MODE VARIABLES
        self.chaos_mode = False
        self.chaos_speed_target = 1.0
        self.chaos_current_speed = 1.0
        self.chaos_speed_change_rate = 0.05  # Moderate speed changes
        self.chaos_last_speed_change = time.time()
        self.chaos_last_folder_change = time.time()
        self.chaos_last_pattern_skip = time.time()
        self.chaos_speed_change_interval = 3.0  # Change speed every 2-6 seconds
        self.chaos_folder_change_interval = 15.0  # Change folder every 12-25 seconds
        self.chaos_pattern_skip_interval = 5.0   # Skip patterns every 4-8 seconds
    
        # Available chaos categories (exclude current)
        self.chaos_categories = []
        self.chaos_current_category = "BLOWJOB"
    
    def load_patterns(self, category_folder="BLOWJOB"):
        """Load patterns from specified category folder"""
        print(f"Loading patterns from funscripts/{category_folder}/...")
        self.pattern_database = {}
    
        category_path = os.path.join("funscripts", category_folder)
        if os.path.exists(category_path):
            for file in os.listdir(category_path):
                if file.endswith('.funscript'):
                    try:
                        file_path = os.path.join(category_path, file)
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            actions = data['actions']
                    
                        if len(actions) >= 3:
                            pattern_id = f"{category_folder}_{file}"
                            pattern_info = {
                                'file': file,
                                'category': category_folder,
                                'pattern_id': pattern_id,
                                'funscript_actions': actions,
                                'start_pos': actions[0]['pos'],
                                'end_pos': actions[-1]['pos'],
                                'total_duration': actions[-1]['at'] - actions[0]['at']
                            }
                        
                            self.pattern_database[pattern_id] = pattern_info
                
                    except Exception as e:
                        print(f"⚠️ Error loading {file}: {e}")

    def set_chaos_mode(self, enabled):
        """Enable/disable chaos mode"""
        self.chaos_mode = enabled
        if enabled:
            print("🌪️ CHAOS MODE ACTIVATED - Bot takes control!")
            self.chaos_current_speed = self.base_speed
            self.chaos_speed_target = self.base_speed
            self.chaos_last_speed_change = time.time()
            self.chaos_last_folder_change = time.time()
            # Load available categories for chaos
            self.update_chaos_categories()
        else:
            print("🛑 Chaos mode deactivated")

    def update_chaos_categories(self):
        """Update available categories for chaos mode"""
        all_categories = self.get_available_categories()
        # Exclude current category for more variety
        self.chaos_categories = [cat for cat in all_categories if cat != self.chaos_current_category]
        print(f"🌪️ Chaos categories: {self.chaos_categories}")

    def update_chaos_control(self, base_speed):
        """Update chaos mode control - BALANCED CHAOS VERSION"""
        if not self.chaos_mode:
            return base_speed
        
        current_time = time.time()
    
        # FREQUENT BUT NOT MANIC SPEED TRANSITIONS (2-6 seconds)
        if current_time - self.chaos_last_speed_change > self.chaos_speed_change_interval:
            # Pick new random speed target with some bias towards extremes
            if random.random() < 0.3:  # 30% chance for extreme speeds
                if random.random() < 0.5:
                    self.chaos_speed_target = random.uniform(0.1, 0.3)  # Very slow
                else:
                    self.chaos_speed_target = random.uniform(1.2, 1.5)  # Very fast
            else:  # 70% chance for normal range
                self.chaos_speed_target = random.uniform(0.4, 1.1)
        
            # Moderate interval for next change (2-6 seconds)
            self.chaos_speed_change_interval = random.uniform(2.0, 6.0)
            self.chaos_last_speed_change = current_time
        
            print(f"🌪️ CHAOS SPEED: {self.chaos_current_speed:.2f}x → {self.chaos_speed_target:.2f}x (next in {self.chaos_speed_change_interval:.1f}s)")
    
        # SMOOTH BUT NOTICEABLE INTERPOLATION to target speed
        speed_diff = self.chaos_speed_target - self.chaos_current_speed
        if abs(speed_diff) > 0.01:
            self.chaos_current_speed += speed_diff * self.chaos_speed_change_rate
            if abs(self.chaos_speed_target - self.chaos_current_speed) < 0.01:
                self.chaos_current_speed = self.chaos_speed_target
    
        # REGULAR FOLDER SWITCHING (12-25 seconds)
        if (current_time - self.chaos_last_folder_change > self.chaos_folder_change_interval and 
            self.chaos_categories):
        
            new_category = random.choice(self.chaos_categories)
            print(f"🌪️ CHAOS FOLDER: {self.chaos_current_category} → {new_category}")
        
            if hasattr(self, 'chaos_folder_callback') and self.chaos_folder_callback:
                self.chaos_folder_callback(new_category)
        
            self.chaos_current_category = new_category
            self.update_chaos_categories()
        
            # Moderate folder changes (12-25 seconds)
            self.chaos_folder_change_interval = random.uniform(12.0, 25.0)
            self.chaos_last_folder_change = current_time
    
        # OCCASIONAL PATTERN SKIPPING (4-8 seconds)
        if current_time - self.chaos_last_pattern_skip > self.chaos_pattern_skip_interval:
            # Skip to next pattern for variety
            self.skip_to_next_pattern()
        
            # Moderate skip interval (4-8 seconds)
            self.chaos_pattern_skip_interval = random.uniform(4.0, 8.0)
            self.chaos_last_pattern_skip = current_time
        
            print(f"🌪️ CHAOS SKIP PATTERN (next in {self.chaos_pattern_skip_interval:.1f}s)")
    
        return self.chaos_current_speed                        
    

    def get_available_categories(self):
        """Get list of available pattern categories"""
        categories = []
        funscripts_dir = "funscripts"
        if os.path.exists(funscripts_dir):
            for item in os.listdir(funscripts_dir):
                item_path = os.path.join(funscripts_dir, item)
                if os.path.isdir(item_path):
                    # Check if folder contains .funscript files
                    funscript_files = [f for f in os.listdir(item_path) if f.endswith('.funscript')]
                    if funscript_files:
                        categories.append(item)
        return sorted(categories) if categories else ["bj"]  # fallback to bj
    
    def initialize_seamless_stream(self, speed=1.0):
        """Initialize the seamless motion stream - FIXED"""
        print("🌊 Initializing SEAMLESS stream...")
        
        self.motion_stream.clear()
        self.last_command_time = time.time() * 1000
        self.base_speed = speed
        
        self.build_seamless_stream(speed)
        
        print(f"✅ Stream ready: {len(self.motion_stream)} commands")
    
    def build_seamless_stream(self, speed=1.0):
        """Build continuous motion stream - ZERO GAPS"""
        pattern_count = 0
        max_patterns = 8
        
        while self._get_stream_duration() < self.stream_target_duration and pattern_count < max_patterns:
            next_pattern = self.select_next_pattern()
            if not next_pattern:
                break
                
            self._integrate_pattern_seamlessly(next_pattern, speed)
            pattern_count += 1
    
    def _get_stream_duration(self):
        """Get current stream duration - FIXED"""
        if not self.motion_stream:
            return 0
        
        current_time = time.time() * 1000
        future_commands = [cmd for cmd in self.motion_stream if cmd['timestamp'] > current_time]
        
        if not future_commands:
            return 0
            
        return future_commands[-1]['timestamp'] - current_time
    
    def _integrate_pattern_seamlessly(self, pattern, speed):
        """Integrate pattern into stream - ABSOLUTELY SEAMLESS WITH SPEED"""
        actions = pattern.get('funscript_actions', [])
        if not actions:
            return
            
        # Get start time - SEAMLESS CONTINUATION
        if not self.motion_stream:
            start_time = time.time() * 1000
        else:
            # Start EXACTLY where last command is scheduled - NO GAPS
            start_time = self.motion_stream[-1]['timestamp']
        
        # FIXED: Apply speed properly to duration
        base_duration = 250  # Base 180ms
        speed_adjusted_duration = base_duration / max(0.3, min(3.0, speed))
        actual_duration = max(80, min(400, int(speed_adjusted_duration)))
        
        current_time = start_time
        
        # Add ALL actions with perfect timing AND speed consideration
        for action in actions:
            stream_action = {
                'timestamp': current_time,
                'pos': action['pos'],
                'duration': actual_duration,
                'pattern_id': pattern['pattern_id'],
                'speed_used': speed
            }
            self.motion_stream.append(stream_action)
            current_time += actual_duration  # PERFECT SPACING WITH SPEED
        
        self.pattern_history.append(pattern)
        self.current_pattern = pattern
    
    def select_next_pattern(self):
        """Select next pattern - random selection"""
        if not self.pattern_database:
            return None
        
        available_patterns = list(self.pattern_database.values())
        recent_ids = {p['pattern_id'] for p in self.pattern_history if p}
        
        candidates = [p for p in available_patterns if p['pattern_id'] not in recent_ids]
        
        if len(candidates) < 3:
            candidates = available_patterns
        
        return random.choice(candidates) if candidates else None
    
    def get_next_motion_command(self, speed=1.0):
        """Get next motion command - ZERO PAUSE TRANSITIONS WITH SPEED"""
        # Manual override mode
        if self.manual_override_active:
            position = int(self.manual_return_position * 100)
            return position, 50, "manual_override"
        
        # Get CURRENT speed including build-up
        current_speed = self.get_current_speed(speed)
        
        # Initialize stream if needed
        if not self.motion_stream:
            self.initialize_seamless_stream(current_speed)
            
        # AGGRESSIVE refill to prevent ANY gaps - with current speed
        if self._get_stream_duration() < self.stream_target_duration * 0.7:
            self.build_seamless_stream(current_speed)
        
        # Get next command
        if not self.motion_stream:
            return 50, 150, "fallback"
        
        # Remove old commands
        current_time = time.time() * 1000
        while self.motion_stream and self.motion_stream[0]['timestamp'] <= current_time:
            self.motion_stream.popleft()
        
        if not self.motion_stream:
            # Emergency fallback - immediate rebuild with current speed
            self.initialize_seamless_stream(current_speed)
            if not self.motion_stream:
                return 50, 150, "emergency"
        
        command = self.motion_stream.popleft()
        
        # APPLY CURRENT SPEED TO DURATION
        base_duration = command.get('duration', 250)
        speed_ratio = current_speed / command.get('speed_used', 1.0)
        adjusted_duration = max(80, min(400, int(base_duration / speed_ratio)))
        
        position = command['pos']
        action_type = f"stream_{command.get('pattern_id', 'unknown')}"
        
        return position, adjusted_duration, action_type
    
    def set_joystick_speed_multiplier(self, multiplier):
        """Set joystick speed multiplier"""
        self.joystick_speed_multiplier = multiplier
    
    def start_manual_override(self, position):
        """Start manual override"""
        if not self.manual_override_active:
            self.manual_override_active = True
            self.manual_return_position = position
            print(f"🎮 Manual override started at {position*100:.1f}%")
    
    def update_manual_position(self, position):
        """Update manual position"""
        if self.manual_override_active:
            self.manual_return_position = position
    
    def end_manual_override(self):
        """End manual override"""
        if self.manual_override_active:
            self.manual_override_active = False
            print("🎮 Manual override ended")
    
    def skip_to_next_pattern(self):
        """Skip to next pattern"""
        if not self.manual_override_active:
            print("⭐ Skipping to next pattern...")
            # Clear and rebuild for immediate skip
            self.motion_stream.clear()
            self.build_seamless_stream(self.base_speed)

    # Add this method to your PatternSequencer class

    def start_buildup_mode(self, duration_seconds, cycles=1, start_speed=0.1, end_speed=1.5,
                          cycle_folders=False, trigger_type="time", interval_value="2:00"):
        """Start build-up mode with FIXED speed limits"""
        self.buildup_mode = True
        self.buildup_duration = duration_seconds
        self.buildup_start_time = time.time()
        self.buildup_start_speed = start_speed  # Now starts at 0.1x
        self.buildup_end_speed = end_speed      # Now max 1.5x
        self.buildup_cycles = max(1, cycles)
        self.current_buildup_cycle = 0
    
        # Store folder cycling settings
        self.cycle_folders = cycle_folders
        self.trigger_type = trigger_type
        self.interval_value = interval_value
        self.folder_change_counter = 0
        self.last_folder_change = time.time()

        print(f"🚀 Build-up: {start_speed}x → {end_speed}x, {cycles} cycles, {duration_seconds}s")
        if cycle_folders:
            print(f"📁 Folder cycling enabled: {trigger_type} every {interval_value}")            
    
    
    def stop_buildup_mode(self):
        """Stop build-up mode"""
        self.buildup_mode = False
        self.buildup_start_time = None
        print("ℹ️ Build-up stopped")
    
    def get_current_speed(self, manual_speed):
        """Get current speed with build-up and joystick multipliers - FIXED RANGE 0.1-1.5"""
        base_speed = manual_speed          # keep pattern timing stable
        effective_speed = base_speed       # what we'll actually return

        if self.buildup_mode and self.buildup_start_time:
            elapsed = time.time() - self.buildup_start_time
            total_dur = max(0.001, float(self.buildup_duration))
            cycles = max(1, int(self.buildup_cycles))

            cycle_dur = total_dur / cycles
            cycle_idx = min(cycles - 1, int(elapsed // cycle_dur))
            cycle_elapsed = elapsed - (cycle_idx * cycle_dur)
            cycle_progress = min(1.0, cycle_elapsed / cycle_dur)

            self.current_buildup_cycle = cycle_idx

            # FIXED: Better milestone tracking to prevent spam
            current_cycle_key = f"cycle_{cycle_idx}"
    
            # Only fire milestone sounds once per cycle
            if cycle_progress >= 0.25:
                milestone_key = f"{current_cycle_key}_25"
                if not getattr(self, f"_fired_{milestone_key}", False):
                    setattr(self, f"_fired_{milestone_key}", True)
                    if hasattr(self, "audio_manager"):
                        self.audio_manager.play("buildup_progress_25")
                
            if cycle_progress >= 0.50:
                milestone_key = f"{current_cycle_key}_50"
                if not getattr(self, f"_fired_{milestone_key}", False):
                    setattr(self, f"_fired_{milestone_key}", True)
                    if hasattr(self, "audio_manager"):
                        self.audio_manager.play("buildup_progress_50")
                
            if cycle_progress >= 0.75:
                milestone_key = f"{current_cycle_key}_75"
                if not getattr(self, f"_fired_{milestone_key}", False):
                    setattr(self, f"_fired_{milestone_key}", True)
                    if hasattr(self, "audio_manager"):
                        self.audio_manager.play("buildup_progress_75")

            # Ramp speed (applied only to effective_speed)
            eased_progress = cycle_progress * cycle_progress
            effective_speed = self.buildup_start_speed + eased_progress * (
                self.buildup_end_speed - self.buildup_start_speed
            )

                # FIXED: Build-up complete - only fire once per build-up session
            if cycle_idx == (cycles - 1) and cycle_progress >= 1.0:
                effective_speed = self.buildup_end_speed
        
                # Only fire completion sound once
                if not getattr(self, "_buildup_completed", False):
                    self._buildup_completed = True
                    if hasattr(self, "audio_manager"):
                        self.audio_manager.play("buildup_complete")
                    self.stop_buildup_mode()
                    self.play_climax_patterns()
        # 🌪️ ADD CHAOS MODE CONTROL HERE - BEFORE THE RETURN!
        if self.chaos_mode:
            effective_speed = self.update_chaos_control(effective_speed)            
                             

        # Apply joystick multiplier + clamp to NEW RANGE
        final_speed = effective_speed * self.joystick_speed_multiplier
        return round(max(0.1, min(1.5, final_speed)), 2)  # 🔧 NEW LIMITS: 0.1-1.5

        

    def play_climax_patterns(self):
        """Switch to climax folder and start playing patterns - FIXED"""
        import os, random, json
    
        # FIXED: Look in root directory, not inside funscripts
        climax_folder = "climax"  # Root level folder
    
        if not os.path.isdir(climax_folder):
            print(f"⚠️ Climax folder not found: {climax_folder}")
            print("💡 Make sure 'climax' folder exists in the same directory as your script")
            return

        # Get all .funscript files from climax folder
        scripts = []
        for file in os.listdir(climax_folder):
            if file.endswith(".funscript"):
                scripts.append(os.path.join(climax_folder, file))
    
        if not scripts:
            print("⚠️ No funscripts found in climax folder!")
            return

        # Choose a random climax script
        chosen_script = random.choice(scripts)
        print(f"🔥 Playing climax script: {os.path.basename(chosen_script)}")

        try:
            # Load the climax script
            with open(chosen_script, 'r') as f:
                data = json.load(f)
                actions = data.get('actions', [])
        
            if not actions:
                print("⚠️ No actions found in climax script")
                return
        
            # Clear current stream and load climax patterns
            self.motion_stream.clear()
        
            # Create climax pattern entry
            climax_pattern = {
                'file': os.path.basename(chosen_script),
                'category': 'climax',
                'pattern_id': f"climax_{os.path.basename(chosen_script)}",
                'funscript_actions': actions,
                'start_pos': actions[0]['pos'],
                'end_pos': actions[-1]['pos'],
                'total_duration': actions[-1]['at'] - actions[0]['at']
            }    
        
            # Integrate the climax pattern with high speed
            climax_speed = 1.5  # Max speed for climax
            self._integrate_pattern_seamlessly(climax_pattern, climax_speed)
        
            # Add to pattern history
            self.current_pattern = climax_pattern
            self.pattern_history.append(climax_pattern)
        
            print(f"✅ Climax pattern loaded: {len(actions)} actions at {climax_speed}x speed")
        
            # Play audio notification
            if hasattr(self, "audio_manager"):
                self.audio_manager.play("buildup_complete")
        
        except Exception as e:
            print(f"❌ Error loading climax script: {e}")
            import traceback
            traceback.print_exc()

            



class MouseWheelEntry(tk.Entry):
    """Entry widget with mouse wheel support for time input"""
    
    def __init__(self, parent, increment=0.1, min_value=0.1, max_value=1.5, **kwargs):  # CHANGED DEFAULTS
        super().__init__(parent, **kwargs)
        self.increment = increment
        self.min_value = min_value
        self.max_value = max_value
        
        # Bind mouse wheel events
        self.bind("<MouseWheel>", self._on_mouse_wheel)
        self.bind("<Button-4>", self._on_mouse_wheel)  # Linux
        self.bind("<Button-5>", self._on_mouse_wheel)  # Linux
        
        # Make it focused when clicked
        self.bind("<Button-1>", lambda e: self.focus_set())
    
    def _on_mouse_wheel(self, event):
        """Handle mouse wheel scrolling with different formats"""
        try:
            current_value = self.get()
        
            # Check if current value contains ":" (time format)
            if ":" in current_value:
                # Handle time format
                parts = current_value.split(":")
                current_seconds = int(parts[0]) * 60 + int(parts[1])
            
                if event.delta > 0 or event.num == 4:
                    new_seconds = current_seconds + self.increment
                else:
                    new_seconds = current_seconds - self.increment
            
                new_seconds = max(self.min_value, min(self.max_value, new_seconds))
            
                # Display as MM:SS
                minutes = new_seconds // 60
                seconds = new_seconds % 60
                self.delete(0, tk.END)
                self.insert(0, f"{minutes}:{seconds:02d}")
            
            elif current_value == "25%":
                # Don't change 25% - it's fixed
                return
            
            else:
                # Handle plain numbers (strokes, patterns)
                try:
                    current_number = int(current_value)
                except:
                    current_number = self.min_value
            
                if event.delta > 0 or event.num == 4:
                    new_number = current_number + self.increment
                else:
                    new_number = current_number - self.increment
            
                new_number = max(self.min_value, min(self.max_value, new_number))
            
                # Display as plain number
                self.delete(0, tk.END)
                self.insert(0, str(new_number))
            
        except Exception as e:
            print(f"Mouse wheel error: {e}")
    
        self.select_range(0, tk.END)
        
class DecimalMouseWheelEntry(tk.Entry):
    """Entry widget with mouse wheel support for decimal values"""
    
    def __init__(self, parent, increment=0.1, min_value=0.3, max_value=3.0, **kwargs):
        super().__init__(parent, **kwargs)
        self.increment = increment
        self.min_value = min_value
        self.max_value = max_value
        
        self.bind("<MouseWheel>", self._on_mouse_wheel)
        self.bind("<Button-4>", self._on_mouse_wheel)
        self.bind("<Button-5>", self._on_mouse_wheel)
        self.bind("<Button-1>", lambda e: self.focus_set())
    
    def _on_mouse_wheel(self, event):
        try:
            current_value = float(self.get())
        except ValueError:
            current_value = 2.0
        
        if event.delta > 0 or event.num == 4:
            new_value = current_value + self.increment
        else:
            new_value = current_value - self.increment
        
        new_value = max(self.min_value, min(self.max_value, new_value))
        
        self.delete(0, tk.END)
        self.insert(0, f"{new_value:.1f}")
        self.select_range(0, tk.END)


class VideoVisualizer:
    """Video stroke visualizer - no voice/audio features"""
    
    def __init__(self, parent_frame, status_file="manual_position.json"):
        self.parent_frame = parent_frame
        self.status_file = status_file
        
        # Video data
        self.video_frames = []
        self.total_frames = 0
        self.video_path = ""
        self.fps = 30
        
        # Settings
        self.direction = "0_to_100"
        self.current_position = 50.0
        self.current_frame_index = 0
        self.current_speed = 1.0
        
        # Position interpolation for smooth movement
        self.target_position = 50.0
        self.interpolation_speed = 10.0
        
        # UI elements (will be created later)
        self.video_label = None
        self.invert_var = None
        self.test_mode_var = None
        self.test_slider = None
        
        # Start smooth interpolation
        self.start_smooth_interpolation()

    def toggle_fullscreen(self):
        """Toggle fullscreen mode - IMPROVED VERSION"""
        if hasattr(self, 'fullscreen_window') and self.fullscreen_window:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self):
        """Enter fullscreen mode with proper sizing and controls"""
        if not self.video_frames:
            print("❌ No video loaded for fullscreen")
            return
    
        try:
            # Create fullscreen window
            self.fullscreen_window = tk.Toplevel()
            self.fullscreen_window.title("Video Fullscreen - Press ESC or click X to exit")
            self.fullscreen_window.configure(bg='#000000')
        
            # Set fullscreen attributes
            self.fullscreen_window.attributes('-fullscreen', True)
            self.fullscreen_window.attributes('-topmost', True)
        
            # Create main container
            main_container = tk.Frame(self.fullscreen_window, bg='#000000')
            main_container.pack(fill='both', expand=True)
        
            # Create exit button in corner - SMALLER so video can be FULL SIZE
            exit_button = tk.Button(
                main_container,
                text="X",
                font=("Arial", 16, "bold"),
                bg='#ff0000',
                fg='#ffffff',
                command=self.exit_fullscreen,
                relief='raised',
                bd=3,
                cursor='hand2',
                width=3,
                height=1
            )
            exit_button.place(relx=0.98, rely=0.02, anchor='ne')
        
            # Create large video label with proper sizing
            self.fullscreen_label = tk.Label(
                main_container,
                bg='#000000',
                bd=0,
                highlightthickness=0
            )
            self.fullscreen_label.pack(expand=True, fill='both')
        
            # Bind multiple exit methods
            self.fullscreen_window.bind('<Escape>', lambda e: self.exit_fullscreen())
            self.fullscreen_window.bind('<q>', lambda e: self.exit_fullscreen())
            self.fullscreen_window.bind('<Q>', lambda e: self.exit_fullscreen())
            self.fullscreen_window.bind('<Alt-F4>', lambda e: self.exit_fullscreen())
        
            # Handle window close button (X button)
            self.fullscreen_window.protocol("WM_DELETE_WINDOW", self.exit_fullscreen)
        
            # Focus window to receive key events
            self.fullscreen_window.focus_set()
            self.fullscreen_window.grab_set()  # Modal behavior
        
            # Show current frame in fullscreen with proper sizing
            self.update_fullscreen_display()
        
            print("🖥️ Entered fullscreen mode - Press ESC, click X, or click EXIT button")
        
        except Exception as e:
            print(f"❌ Fullscreen enter error: {e}")
            if hasattr(self, 'fullscreen_window'):
                try:
                    self.fullscreen_window.destroy()
                except:
                    pass
                self.fullscreen_window = None

    def exit_fullscreen(self):
        """Exit fullscreen mode safely"""
        try:
            if hasattr(self, 'fullscreen_window') and self.fullscreen_window:
                print("🚪 Exiting fullscreen mode")
            
                # Release grab
                try:
                    self.fullscreen_window.grab_release()
                except:
                    pass
            
                # Destroy window
                self.fullscreen_window.destroy()
                self.fullscreen_window = None
            
                print("✅ Fullscreen mode exited")
            
        except Exception as e:
            print(f"⚠️ Error exiting fullscreen: {e}")
            # Force cleanup
            self.fullscreen_window = None

    def update_fullscreen_display(self):
        """Update fullscreen display with proper image scaling - FIXED VERSION"""
        if not (hasattr(self, 'fullscreen_window') and 
                self.fullscreen_window and 
                hasattr(self, 'fullscreen_label') and
                0 <= self.current_frame_index < len(self.video_frames)):
            return
    
        try:
            # Get current frame (it's already a PhotoImage)
            current_frame = self.video_frames[self.current_frame_index]
        
            # Get screen dimensions
            screen_width = self.fullscreen_window.winfo_screenwidth()
            screen_height = self.fullscreen_window.winfo_screenheight()
        
            # Get the original PIL image from the PhotoImage
            # We need to recreate the PIL image from the video source
            if hasattr(self, 'display_width') and hasattr(self, 'display_height'):
                # Use the stored display dimensions to calculate scaling
                orig_width = self.display_width
                orig_height = self.display_height
            
                # Calculate proper fullscreen scaling - USE 100% OF SCREEN
                scale_x = screen_width / orig_width
                scale_y = screen_height / orig_height
                scale = min(scale_x, scale_y) * 1.0  # 100% FULL SCREEN
            
                # Calculate new size - MUCH BIGGER
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)
            
                print(f"📺 FULL SCREEN scaling: {orig_width}x{orig_height} -> {new_width}x{new_height} (100% SCREEN)")
            
                # We need to recreate the frame at the larger size
                # Get the frame from video source again
                if hasattr(self, 'video_path') and self.video_path:
                    try:
                        import cv2
                        cap = cv2.VideoCapture(self.video_path)
                        cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_index)
                        ret, frame = cap.read()
                        cap.release()
                    
                        if ret:
                            # Convert and resize for fullscreen
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
                        
                            from PIL import Image, ImageTk
                            pil_image = Image.fromarray(frame_resized)
                            fullscreen_photo = ImageTk.PhotoImage(pil_image)
                        
                            # Update display
                            self.fullscreen_label.config(image=fullscreen_photo)
                            self.fullscreen_label.image = fullscreen_photo  # Keep reference
                        
                            print(f"✅ Fullscreen frame updated: {new_width}x{new_height}")
                            return
                    except Exception as e:
                        print(f"⚠️ Error recreating fullscreen frame: {e}")
        
            # Fallback - use original frame (will be smaller)
            self.fullscreen_label.config(image=current_frame)
            print("⚠️ Using original frame size (fallback)")
        
        except Exception as e:
            print(f"⚠️ Fullscreen display update error: {e}")
            # Last resort fallback
            try:
                if hasattr(self, 'video_frames') and self.video_frames:
                    self.fullscreen_label.config(image=self.video_frames[self.current_frame_index])
            except:
                pass
            
    def update_video_display(self):
        """Update video display (both normal and fullscreen) - IMPROVED VERSION"""
        current_time = time.time()
        if hasattr(self, '_last_update') and current_time - self._last_update < 0.016:
            return
        self._last_update = current_time

        if not self.video_frames or not self.video_label:
            return

        if hasattr(self, '_last_frame') and self._last_frame == self.current_frame_index:
            return

        if 0 <= self.current_frame_index < len(self.video_frames):
            # Update normal display
            self.video_label.config(image=self.video_frames[self.current_frame_index])

            # 🔧 ALSO update fullscreen if active - IMPROVED
            if (hasattr(self, 'fullscreen_window') and 
                self.fullscreen_window and 
                hasattr(self, 'fullscreen_label')):
            
                try:
                    # Use our improved fullscreen update method
                    self.update_fullscreen_display()
                except Exception as e:
                    print(f"⚠️ Fullscreen update error: {e}")

            self._last_frame = self.current_frame_index
    
    def load_video(self, file_path):
        """Load video and create frames - IMPROVED VERSION"""
        if not file_path or not os.path.exists(file_path):
            print(f"❌ Video file not found: {file_path}")
            return
        
        print(f"📹 Loading video: {file_path}")
    
    def load_video(self, file_path):
        """Load video and create frames - IMPROVED VERSION"""
        if not file_path or not os.path.exists(file_path):
            print(f"❌ Video file not found: {file_path}")
            return
        
        print(f"📹 Loading video: {file_path}")
    
        def load_video_thread():
            try:
                cap = cv2.VideoCapture(file_path)
                if not cap.isOpened():
                    raise Exception("Could not open video file")
            
                self.fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
                # Calculate display size
                max_width, max_height = 800, 600
                aspect_ratio = width / height
            
                if aspect_ratio > 1:
                    self.display_width = min(max_width, width // 2)
                    self.display_height = int(self.display_width / aspect_ratio)
                else:
                    self.display_height = min(max_height, height // 2)
                    self.display_width = int(self.display_height * aspect_ratio)
            
                # Extract frames
                new_video_frames = []
                frame_count = 0
            
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_resized = cv2.resize(frame_rgb, (self.display_width, self.display_height))
                
                    pil_image = Image.fromarray(frame_resized)
                    photo = ImageTk.PhotoImage(pil_image)
                    new_video_frames.append(photo)
                
                    frame_count += 1
            
                cap.release()
            
                # Update on main thread
                def update_gui():
                    self.video_frames = new_video_frames
                    self.total_frames = len(self.video_frames)
                    self.video_path = file_path

                    # Set initial position and display first frame
                    self.current_position = 50.0
                    self.target_position = 50.0
                    frame_index = self.calculate_frame_index(50.0)
                    self.current_frame_index = frame_index
                    self.update_video_display()

                    print(f"✅ Video loaded: {self.total_frames} frames, showing frame {frame_index}")
            
                if hasattr(self.parent_frame, 'after'):
                    self.parent_frame.after(0, update_gui)
            
            except Exception as e:
                print(f"❌ Video load error: {e}")
                def show_error():
                    if hasattr(self, 'video_label') and self.video_label:
                        self.video_label.config(
                            text=f"Error loading video:\n{os.path.basename(file_path)}\n{str(e)[:50]}...",
                            fg='#ff4444'
                    )
                if hasattr(self.parent_frame, 'after'):
                    self.parent_frame.after(0, show_error)
    
        # Start loading in background
        threading.Thread(target=load_video_thread, daemon=True).start()
    
    def calculate_frame_index(self, position):
        """Calculate frame index from position"""
        if self.total_frames == 0:
            return 0
        
        if self.invert_var and self.invert_var.get():
            position = 100 - position
        
        if self.direction == "0_to_100":
            frame_index = int(position * (self.total_frames - 1) / 100)
        else:
            frame_index = int((100 - position) * (self.total_frames - 1) / 100)
        
        return max(0, min(self.total_frames - 1, frame_index))
    
    def update_video_display(self):
        """Update video display (both normal and fullscreen)"""
        current_time = time.time()
        if hasattr(self, '_last_update') and current_time - self._last_update < 0.016:
            return
        self._last_update = current_time

        if not self.video_frames or not self.video_label:
            return

        if hasattr(self, '_last_frame') and self._last_frame == self.current_frame_index:
            return

        if 0 <= self.current_frame_index < len(self.video_frames):
            # Update normal display
            self.video_label.config(image=self.video_frames[self.current_frame_index])
        
            # 🔧 ALSO update fullscreen if active
            self.update_fullscreen_display()
        
            self._last_frame = self.current_frame_index
    
    def update_position(self, position):
        """Update target position for smooth interpolation"""
        if abs(position - self.target_position) > 0.1:
            self.target_position = position
    
    def start_smooth_interpolation(self):
        """Start smooth interpolation thread"""
        def interpolation_loop():
            while True:
                try:
                    if not (self.test_mode_var and self.test_mode_var.get()):
                        position_diff = self.target_position - self.current_position
                        
                        if abs(position_diff) > 0.1:
                            move_amount = position_diff * self.interpolation_speed * 0.016
                            self.current_position += move_amount
                            
                            frame_index = self.calculate_frame_index(self.current_position)
                            self.current_frame_index = frame_index
                            
                            if self.video_label and 0 <= frame_index < len(self.video_frames):
                                if hasattr(self.parent_frame, 'after'):
                                    self.parent_frame.after(0, self.update_video_display)
                    
                    time.sleep(0.033)  # 60fps
                    
                except Exception as e:
                    time.sleep(0.1)
        
        threading.Thread(target=interpolation_loop, daemon=True).start()
    
    def on_direction_change(self, event=None):
        """Handle direction change"""
        self.update_video_display()
    
    def on_test_position_change(self, value):
        """Handle test slider change"""
        if self.test_mode_var and self.test_mode_var.get():
            self.current_position = float(value)
            frame_index = self.calculate_frame_index(self.current_position)
            self.current_frame_index = frame_index
            self.update_video_display()


class SimpleStickers:
    """
    FIXED Sticker system with proper startup loading
    """

    def __init__(self, parent, default_long_side=512):
        self.parent = parent
        self.stickers = []
        self.default_long_side = int(default_long_side)

        # --- anchor paths to the script folder ---
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir  = os.path.join(base_dir, "stickers")
        self.presets_dir = os.path.join(base_dir, "presets")
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(self.presets_dir, exist_ok=True)

        print(f"🔧 Stickers initialized - Assets: {self.assets_dir}, Presets: {self.presets_dir}")

        # Drag state
        self._drag = {"x": 0, "y": 0}
        
        # FIXED: Don't auto-load here - wait for explicit call
        self._startup_complete = False
        
    def startup_load_when_ready(self):
        """Call this ONCE when the main GUI is fully ready"""
        if self._startup_complete:
            print("⚠️ Startup already completed, skipping")
            return
            
        self._startup_complete = True
        print("🚀 Starting sticker startup load...")
        self._startup_load()

    def _startup_load(self):
        """Load presets/autostart.json if present; else do nothing."""
        path = os.path.join(self.presets_dir, "autostart.json")
        if not os.path.exists(path):
            print("ℹ️ Startup: no autostart.json found")
            return
        try:
            with open(path, "r") as f:
                preset = json.load(f)
            layout = preset.get("layout", [])
            print(f"↩ Startup: loading autostart.json (items={len(layout)})")
            self._rebuild_from_layout_async(layout, auto_lock=True)
        except Exception as e:
            print(f"❌ autostart load error: {e}")
            import traceback
            traceback.print_exc()

    def hide_all(self):
        """Hide all stickers and remember their positions"""
        for s in self.stickers:
            try:
                # ONLY update hidden position if sticker is currently visible
                if s.winfo_viewable():
                    s._hidden_x = s.winfo_x()
                    s._hidden_y = s.winfo_y()
                s.place_forget()
            except Exception as e:
                print(f"⚠️ Hide sticker error: {e}")

    def show_all(self):
        """Show all stickers at their correct positions"""
        for s in self.stickers:
            try:
                # Use the original loaded position, NOT the hidden position
                # Hidden positions are only for temporary tab switching
                if hasattr(s, '_original_x') and hasattr(s, '_original_y'):
                    x, y = s._original_x, s._original_y
                else:
                    # Fallback to current position or default
                    x = getattr(s, '_hidden_x', s.winfo_x() if s.winfo_x() > 0 else 200)
                    y = getattr(s, '_hidden_y', s.winfo_y() if s.winfo_y() > 0 else 200)
            
                s.place(x=x, y=y)
            
                # Handle background stickers
                if getattr(s, '_background', False):
                    s.lower()
                else:
                    s.lift()
                
            except Exception as e:
                print(f"⚠️ Show sticker error: {e}")

    def bring_stickers_to_front(self):
        """Bring all non-background stickers to front"""
        for s in self.stickers:
            try:
                if not getattr(s, '_background', False) and s.winfo_viewable():
                    s.lift()
            except Exception as e:
                print(f"⚠️ Lift sticker error: {e}")

    def save_stickers(self):
        """Lightweight saver - update autostart.json if it exists"""
        try:
            auto = os.path.join(self.presets_dir, "autostart.json")
            if not os.path.exists(auto):
                return  # no autostart yet; silently skip
            preset = {
                "name": "autostart",
                "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "assets_dir": self.assets_dir,
                "layout": self._current_layout_data(),
            }
            with open(auto, "w") as f:
                json.dump(preset, f, indent=2)
        except Exception as e:
            print(f"⚠️ save_stickers error: {e}") 

    def save_as_startup(self):
        """Save current layout to presets/autostart.json"""
        try:
            os.makedirs(self.presets_dir, exist_ok=True)
            path = os.path.join(self.presets_dir, "autostart.json")
            preset = {
                "name": "autostart",
                "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "assets_dir": self.assets_dir,
                "layout": self._current_layout_data(),
            }
            with open(path, "w") as f:
                json.dump(preset, f, indent=2)
            print(f"💾 Saved startup layout: {path} (items={len(preset['layout'])})")
            messagebox.showinfo("Success", f"Saved {len(preset['layout'])} stickers as startup layout!")
            return True
        except Exception as e:
            print(f"❌ Could not save startup layout: {e}")
            messagebox.showerror("Error", f"Failed to save startup: {e}")
            return False

    def load_startup_now(self):
        """Manual button to reload autostart.json right now"""
        print("🔄 Manual startup load requested...")
        self._startup_load()

    def add_sticker(self):
        """Add new sticker - starts UNLOCKED for immediate editing"""
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Select Sticker PNG",
            filetypes=[("PNG files", "*.png"), ("Image files", "*.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            ext = os.path.splitext(path)[1].lower() or ".png"
            new_name = f"sticker_{uuid.uuid4().hex[:8]}{ext}"
            dest_path = os.path.join(self.assets_dir, new_name)
            shutil.copy2(path, dest_path)

            sticker = tk.Label(
                self.parent,
                bd=0,
                highlightthickness=0,
                cursor="hand2"
            )
            
            # Core attributes
            sticker.file_path = dest_path
            sticker.locked = False  # New stickers start unlocked
            sticker._base_img = Image.open(dest_path).convert("RGBA")
            sticker._angle = 0
            sticker._flip_h = False
            sticker._flip_v = False
            sticker._long_side = self.default_long_side
            sticker._background = False

            self._render_sticker(sticker)
            sticker.place(x=200, y=200)

            self.bind_sticker_events(sticker)  # Bind all events including right-click
            self.stickers.append(sticker)
            self.save_stickers()
            print(f"✅ Added NEW sticker (unlocked): {dest_path}")

        except Exception as e:
            print(f"❌ Error adding sticker: {e}")
            messagebox.showerror("Error", f"Failed to add sticker: {e}")

    def toggle_lock_all(self):
        """Lock/unlock every sticker."""
        if not self.stickers:
            print("No stickers to lock/unlock")
            messagebox.showinfo("Info", "No stickers to lock/unlock")
            return
            
        all_locked = all(getattr(s, 'locked', False) for s in self.stickers)
        
        for s in self.stickers:
            if all_locked:
                # unlock
                s.locked = False
                self.bind_sticker_events(s)
                s.config(cursor="hand2")
            else:
                # lock
                s.locked = True
                self._unbind_edit_events(s)
                s.config(cursor="arrow")
                
        self.save_stickers()
        status = "🔓 All unlocked" if all_locked else "🔒 All locked"
        print(status)
        messagebox.showinfo("Success", status)

    def clear_all(self):
        """Remove all stickers from the UI and memory."""
        if not self.stickers:
            messagebox.showinfo("Info", "No stickers to clear")
            return
            
        result = messagebox.askyesno("Clear All", f"Delete all {len(self.stickers)} stickers?")
        if not result:
            return
            
        for s in self.stickers[:]:
            try:
                s.destroy()
            except:
                pass
        self.stickers.clear()
        self.save_stickers()
        print("🧹 All stickers cleared")
        messagebox.showinfo("Success", "All stickers cleared!")

    def _current_layout_data(self):
        """Get current layout data for saving"""
        data = []
        for s in self.stickers:
            try:
                data.append({
                    'file': s.file_path,
                    'x': s.winfo_x(),
                    'y': s.winfo_y(),
                    'long_side': int(getattr(s, "_long_side", self.default_long_side)),
                    'angle': int(getattr(s, "_angle", 0)) % 360,
                    'flip_h': bool(getattr(s, "_flip_h", False)),
                    'flip_v': bool(getattr(s, "_flip_v", False)),
                    'locked': bool(getattr(s, 'locked', False)),
                    'background': bool(getattr(s, "_background", False))
                })
            except Exception as e:
                print(f"⚠️ Error getting sticker data: {e}")
        return data

    def _rebuild_from_layout_async(self, layout, batch_size=3, auto_lock=True):
        """Clear and rebuild layout - ALWAYS lock by default on startup"""
        print(f"🔄 Rebuilding from layout: {len(layout)} items (auto_lock={auto_lock})")
        
        # Clear current
        for s in self.stickers[:]:
            try:
                s.destroy()
            except:
                pass
        self.stickers.clear()

        queue = list(layout)
        
        def step():
            batch_count = 0
            while queue and batch_count < batch_size:
                item = queue.pop(0)
                batch_count += 1
                
                fp = item.get('file')
                if not fp or not os.path.exists(fp):
                    print(f"⚠️ Missing asset (skipping): {fp}")
                    continue
                    
                try:
                    s = tk.Label(
                        self.parent,
                        bg=self.parent.cget('bg'),
                        bd=0,
                        highlightthickness=0,
                        cursor="arrow"  # Start with locked cursor
                    )
                    s.file_path = fp
                    s._base_img = Image.open(fp).convert("RGBA")
                    s._long_side = int(item.get('long_side', self.default_long_side))
                    s._angle = int(item.get('angle', 0)) % 360
                    s._flip_h = bool(item.get('flip_h', False))
                    s._flip_v = bool(item.get('flip_v', False))
                    s._background = bool(item.get('background', False))

                    # FORCE LOCKED on startup (ignore saved lock state)
                    s.locked = True  # Always start locked

                    self._render_sticker(s)
                    s.place(x=item['x'], y=item['y'])
                    s._original_x = item['x']  # Remember the loaded position
                    s._original_y = item['y']

                    # ALWAYS bind right-click menu (even for locked stickers)
                    s.bind("<Button-3>", lambda e, sticker=s: self.show_sticker_menu(e, sticker))

                    self.stickers.append(s)

                    if s._background:
                        s.lower()
                    else:
                        s.lift()

                except Exception as e:
                    print(f"❌ Load item error: {e}")

            if queue:
                self.parent.after(10, step)
            else:
                self.save_stickers()
                print(f"✅ Loaded {len(self.stickers)} stickers - ALL LOCKED BY DEFAULT")

        # Start the loading process
        if queue:
            step()

    # ... (rest of the methods remain the same: bind_sticker_events, _render_sticker, etc.)
    
    def bind_sticker_events(self, sticker):
        """Bind drag/resize/menu events - ALWAYS bind right-click menu"""
        # ALWAYS bind right-click menu (even for locked stickers)
        sticker.bind("<Button-3>", lambda e: self.show_sticker_menu(e, sticker))
        
        # Only bind editing events if unlocked
        if not getattr(sticker, "locked", False):
            # Drag
            sticker.bind("<Button-1>", lambda e: self.start_drag(e, sticker))
            sticker.bind("<B1-Motion>", lambda e: self.on_drag(e, sticker))

            # Resize (Ctrl/Alt + Wheel)
            sticker.bind("<Control-MouseWheel>", lambda e: self.resize(sticker, e.delta > 0))
            sticker.bind("<Alt-MouseWheel>",     lambda e: self.resize(sticker, e.delta > 0))
            sticker.bind("<Control-Button-4>",   lambda e: self.resize(sticker, True))
            sticker.bind("<Control-Button-5>",   lambda e: self.resize(sticker, False))
            sticker.bind("<Alt-Button-4>",       lambda e: self.resize(sticker, True))
            sticker.bind("<Alt-Button-5>",       lambda e: self.resize(sticker, False))

    def _unbind_edit_events(self, sticker):
        """Unbind editing events but KEEP right-click menu"""
        try:
            sticker.unbind("<Button-1>")
            sticker.unbind("<B1-Motion>")
            sticker.unbind("<Control-MouseWheel>")
            sticker.unbind("<Alt-MouseWheel>")
            sticker.unbind("<Control-Button-4>")
            sticker.unbind("<Control-Button-5>")
            sticker.unbind("<Alt-Button-4>")
            sticker.unbind("<Alt-Button-5>")
            # DON'T unbind right-click - keep it for locked stickers
        except:
            pass

    def start_drag(self, event, sticker):
        if getattr(sticker, "locked", False): return
        self._drag["x"] = event.x
        self._drag["y"] = event.y

    def on_drag(self, event, sticker):
        if getattr(sticker, "locked", False): return
        dx = event.x - self._drag["x"]
        dy = event.y - self._drag["y"]
        sticker.place(x=sticker.winfo_x() + dx, y=sticker.winfo_y() + dy)
        self.save_stickers()

    def resize(self, sticker, bigger: bool):
        """Resize by adjusting the longest side (keeps AR)."""
        if getattr(sticker, "locked", False): return
        current = int(getattr(sticker, "_long_side", self.default_long_side))
        new_long = int(current * (1.1 if bigger else 0.9))
        new_long = max(32, min(4096, new_long))
        self._render_sticker(sticker, target_long_side=new_long)
        self.save_stickers()

    def _render_sticker(self, sticker, target_long_side=None):
        """Apply transforms (flip/rotate) and resize with transparent corners."""
        base = getattr(sticker, "_base_img", None)
        if base is None:
            base = Image.open(sticker.file_path).convert("RGBA")
            sticker._base_img = base
        img = base.copy().convert("RGBA")

        # Flips
        if getattr(sticker, "_flip_h", False):
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if getattr(sticker, "_flip_v", False):
            img = img.transpose(Image.FLIP_TOP_BOTTOM)

        # Rotate with alpha
        angle = int(getattr(sticker, "_angle", 0)) % 360
        if angle:
            try:
                img = img.rotate(angle, expand=True, resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))
            except TypeError:
                rot = img.rotate(angle, expand=True, resample=Image.BICUBIC)
                transparent = Image.new("RGBA", rot.size, (0, 0, 0, 0))
                transparent.paste(rot, (0, 0), rot)
                img = transparent

        # Scale (keep AR, longest side = long_side)
        long_side = int(target_long_side or getattr(sticker, "_long_side", self.default_long_side))
        w, h = img.size
        scale = long_side / max(w, h) if max(w, h) else 1.0
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Force proper transparency handling
        if img.mode == 'RGBA':
            # Create a background that matches the parent
            parent_bg = self.parent.cget("bg")
            # Convert hex color to RGB tuple
            if parent_bg.startswith('#'):
                hex_color = parent_bg.lstrip('#')
                bg_rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            else:
                bg_rgb = (0, 0, 0)  # Default black

            # Create background and paste image with alpha
            background = Image.new('RGB', img.size, bg_rgb)
            background.paste(img, (0, 0), img)  # Use img as its own alpha mask
            tk_img = ImageTk.PhotoImage(background)
        else:
            tk_img = ImageTk.PhotoImage(img)

        # FIXED: These lines must be OUTSIDE the if/else block
        sticker.config(image=tk_img)
        sticker.image = tk_img
        sticker._long_side = long_side
            
    def show_sticker_menu(self, event, sticker):
        """Show right-click context menu for sticker"""
        menu = tk.Menu(self.parent, tearoff=0, bg='#330033', fg='#ff66cc')

        # Transforms
        menu.add_command(label="↶ Rotate Left 90°",  command=lambda: self.rotate_sticker(sticker, -90))
        menu.add_command(label="↷ Rotate Right 90°", command=lambda: self.rotate_sticker(sticker,  90))
        menu.add_command(label="⇋ Flip Horizontal",  command=lambda: self.flip_horizontal(sticker))
        menu.add_command(label="⇅ Flip Vertical",    command=lambda: self.flip_vertical(sticker))
        menu.add_separator()

        # Wallpaper pin
        if getattr(sticker, "_background", False):
            menu.add_command(label="📌 Unpin from Wallpaper", command=lambda: self.unpin_wallpaper(sticker))
        else:
            menu.add_command(label="📌 Pin as Wallpaper (Back)", command=lambda: self.pin_as_wallpaper(sticker))
        menu.add_separator()

        # Lock / layer / delete
        lock_text = "🔓 Unlock This" if getattr(sticker, 'locked', False) else "🔒 Lock This"
        menu.add_command(label=lock_text, command=lambda: self._toggle_individual_lock(sticker))
        menu.add_command(label="⬆️ Bring to Front", command=lambda: sticker.lift())
        menu.add_command(label="⬇️ Send to Back",   command=lambda: sticker.lower())
        menu.add_command(label="🗑️ Delete This",    command=lambda: self.delete_individual_sticker(sticker))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def rotate_sticker(self, sticker, degrees=90):
        """Rotate by exact ±90 (snaps current to nearest 90 first)."""
        if getattr(sticker, "locked", False): return
        cur = int(getattr(sticker, "_angle", 0)) % 360
        cur = (round(cur / 90) * 90) % 360
        step = 90 if degrees >= 0 else -90
        sticker._angle = (cur + step) % 360
        self._render_sticker(sticker)
        self.save_stickers()

    def flip_horizontal(self, sticker):
        if getattr(sticker, "locked", False): return
        sticker._flip_h = not getattr(sticker, "_flip_h", False)
        self._render_sticker(sticker)
        self.save_stickers()

    def flip_vertical(self, sticker):
        if getattr(sticker, "locked", False): return
        sticker._flip_v = not getattr(sticker, "_flip_v", False)
        self._render_sticker(sticker)
        self.save_stickers()

    def pin_as_wallpaper(self, sticker):
        """Make this sticker 'wallpaper': send back + lock."""
        sticker._background = True
        sticker.locked = True
        self._unbind_edit_events(sticker)
        sticker.config(cursor="arrow")
        sticker.lower()
        self.save_stickers()

    def unpin_wallpaper(self, sticker):
        """Return sticker to normal editing layer."""
        sticker._background = False
        sticker.locked = False
        self.bind_sticker_events(sticker)
        sticker.config(cursor="hand2")
        sticker.lift()
        self.save_stickers()

    def delete_individual_sticker(self, sticker):
        try:
            self.stickers.remove(sticker)
        except ValueError:
            pass
        try:
            sticker.destroy()
        except:
            pass
        self.save_stickers()
        print("🗑️ Deleted sticker")

    def _toggle_individual_lock(self, sticker):
        """Toggle lock state and update events accordingly"""
        sticker.locked = not getattr(sticker, 'locked', False)
        
        if sticker.locked:
            # Lock: remove edit events but keep right-click
            self._unbind_edit_events(sticker)
            sticker.config(cursor="arrow")
            print("🔒 Locked sticker")
        else:
            # Unlock: bind all events including editing
            self.bind_sticker_events(sticker)
            sticker.config(cursor="hand2")
            print("🔓 Unlocked sticker")
            
        self.save_stickers()
     
class AIPatternSequencerGUI:
    """Main GUI"""
    
    def __init__(self):
        """Initialize with improved UI"""
        self.device_client = IntifaceClient("http://localhost:8080")
        self.device_client.set_connection_callback(self.on_connection_change)
        self._ui_ready = False
        self.load_custom_fonts()
        # 3090 + Good CPU Performance Mode
        import os, psutil
        os.environ['PYTHONUNBUFFERED'] = '1'
        psutil.Process().nice(psutil.HIGH_PRIORITY_CLASS if os.name == 'nt' else -10)
        self.root = tk.Tk()
        self.root.title("DARK DESIRES - GOTHIC PATTERN SEQUENCER")
        self.root.geometry("1600x900")  # Larger default size
        self.root.configure(bg='#000000')
        

        self.stroke_direction = None  # Track if we're going up or down
        self.stroke_peak_detected = False  # Track if we've hit a peak
    
        # Initialize audio manager and other components
        self.audio_device_manager = AudioDeviceManager()
        self.audio_manager = EnhancedAudioManager()
        self.moans_manager = MoansManager()
        self.stickers = SimpleStickers(self.root)
        self.pattern_sequencer = PatternSequencer()
        self.pattern_sequencer.audio_manager = self.audio_manager  # ADD THIS LINE
        self.current_category = "BLOWJOB"
        self.joystick_controller = JoystickController()
        self.engine_manager = None
        # Initialize video gallery BEFORE setup_gui()
        self.video_gallery = VideoGallery()

        self.device_client.set_connection_callback(self.on_connection_change)
        self.joystick_controller.set_callbacks(
            speed_callback=self.on_joystick_speed_change,
            manual_callback=self.on_manual_override,
            skip_callback=self.on_skip_pattern,
            play_pause_callback=self.on_play_pause_button
        )

        # C# Intiface server client
        # (optional) keep your connection-status UI in sync
        if hasattr(self.device_client, "set_connection_callback"):
            self.device_client.set_connection_callback(self.on_connection_change)
        
        # State variables
        self.arousal = 0.75
        self.running = False
        self.last_json_write_time = 0
        self.json_write_interval = 0.05


        # ADD THESE MISSING AUTO-SWITCHER VARIABLES:
        self.last_position = 50.0  # For stroke detection
        self.stroke_count = 0
        self.stroke_threshold = 15.0  # Minimum position change to count as stroke
        self.random_timer = None  # For time-based switching
        self.stroke_direction = None  # Track if we're going up or down
        self.stroke_peak_detected = False  # Track if we've hit a peak
        self._last_direction = None  # ADD THIS LINE
        self._stroke_start_pos = 50.0  # ADD THIS LINE TOO
        # Detection state
        self.detecting_input = False
        self.detection_type = None
        self.detection_timeout = None
    
        # Detected config
        self.detected_speed_axis = -1
        self.detected_manual_axis = -1
        self.detected_manual_btn_button = -1
        self.detected_skip_button = -1
        self.detected_play_pause_button = -1
        self.detected_next_video_button = -1     # ✅ FIXED: Added missing variable
        self.detected_prev_video_button = -1 
    
        
        self.setup_gui()
             
        self.root.after(3000, self.fix_sticker_layers)

        # FIXED: Single delayed call for sticker startup
        self.root.after(3000, self._ensure_sticker_visibility)  # 3 seconds delay
        self.root.after(3500, self.fix_sticker_layers)         # Then fix layers
        self._startup_complete = True
        self.root.after(5000, lambda: setattr(self, '_ui_ready', True))  # 5 seconds instead of 2

    

        # Detection state
        self.detecting_input = False
        self.detection_type = None
        self.detection_timeout = None

        # Detected config - ADD THE NEW VIDEO BUTTON VARIABLES
        self.detected_speed_axis = -1
        self.detected_manual_axis = -1
        self.detected_manual_btn_button = -1
        self.detected_skip_button = -1
        self.detected_next_video_button = -1     # 🔧 NEW
        self.detected_prev_video_button = -1     # 🔧 NEW

        # Set up callbacks - ADD VIDEO CALLBACKS
        self.joystick_controller.set_callbacks(
            speed_callback=self.on_joystick_speed_change,
            manual_callback=self.on_manual_override,
            skip_callback=self.on_skip_pattern,
            play_pause_callback=self.on_play_pause_button,
            next_video_callback=self.on_joystick_next_video,    # 🔧 NEW
            prev_video_callback=self.on_joystick_prev_video     # 🔧 NEW
        )
        # Detected config
        self.detected_speed_axis = -1
        self.detected_manual_axis = -1
        self.detected_manual_btn_button = -1
        
        self.detected_next_video_button = -1     # ADD THIS
        self.detected_prev_video_button = -1     # ADD THIS
        
        self.pattern_sequencer.chaos_folder_callback = self.on_chaos_folder_change

        



    def load_custom_fonts(self):
        """Load TTF fonts from fonts folder"""
        try:
            fonts_dir = os.path.join(os.path.dirname(__file__), "fonts")
        
            if os.path.exists(fonts_dir):
                for font_file in os.listdir(fonts_dir):
                    if font_file.endswith('.ttf') or font_file.endswith('.otf'):
                        font_path = os.path.join(fonts_dir, font_file)
                    
                        # Windows method
                        if os.name == 'nt':
                            import ctypes
                            from ctypes import wintypes
                            gdi32 = ctypes.windll.gdi32
                            gdi32.AddFontResourceW(font_path)
                        
                        print(f"✅ Loaded font: {font_file}")
            else:
                print("📁 Fonts folder not found")
            
        except Exception as e:
            print(f"⚠️ Font loading error: {e}")        

    def fix_sticker_layers(self):
        """Fix sticker layering issues"""
        if hasattr(self, "stickers") and self.stickers:
            # Small delay then bring stickers to front
            self.root.after(100, self.stickers.bring_stickers_to_front)

    def toggle_chaos_mode(self):
        """Toggle chaos mode on/off"""
        enabled = self.chaos_mode_var.get()
        self.pattern_sequencer.set_chaos_mode(enabled)
    
        if enabled:
            self.chaos_status_label.config(
                text="🌪️ CHAOS ACTIVE - Balanced mayhem! 🎯",
                fg='#ff6666'
            )
            self.audio_manager.play('buildup_start')  # Dramatic sound
            # Start status updates
            self.update_chaos_status_display()
        else:
            self.chaos_status_label.config(
                text="Chaos Mode: Inactive",
                fg='#888888'
            )
            self.audio_manager.play('buildup_stop')

    def on_chaos_folder_change(self, new_category):
        """Handle chaos mode folder changes"""
        try:
            print(f"🌪️ Chaos folder change: {self.current_category} → {new_category}")
        
            # Stop playback temporarily
            was_running = self.running
            if was_running:
                self.running = False  # Temporary stop
        
            # Change category
            self.current_category = new_category
            self.category_combo.set(new_category)
        
            # Reload patterns
            self.pattern_sequencer.load_patterns(new_category)
        
            # Clear motion stream for immediate effect
            self.pattern_sequencer.motion_stream.clear()
        
            # Resume playback
            if was_running:
                self.running = True
        
            print(f"✅ Chaos folder changed to: {new_category}")
        
        except Exception as e:
            print(f"❌ Chaos folder change error: {e}")

    def update_chaos_status_display(self):
        """Update chaos mode status display"""
        if self.pattern_sequencer.chaos_mode:
            current_speed = self.pattern_sequencer.chaos_current_speed
            target_speed = self.pattern_sequencer.chaos_speed_target
            folder = self.pattern_sequencer.chaos_current_category
        
            self.chaos_status_label.config(
                text=f"🌪️ CHAOS: {current_speed:.2f}x→{target_speed:.2f}x | {folder}",
                fg='#ff6666'
            )
        
            # Schedule next update
            self.root.after(1000, self.update_chaos_status_display)            

    def toggle_voice_audio(self):
        """Toggle voice audio on/off"""
        enabled = self.voice_enabled_var.get()
        self.audio_manager.audio_enabled = enabled
        print(f"🔊 Voice audio: {'ON' if enabled else 'OFF'}")

    def toggle_moans_audio(self):
        """Toggle moans audio on/off"""
        enabled = self.moans_enabled_var.get()
        self.moans_manager.set_enabled(enabled)
        print(f"💕 Moans audio: {'ON' if enabled else 'OFF'}")


    def on_moans_volume_change(self, value):
        """Handle moans volume change"""
        volume = float(value)
        self.moans_manager.set_volume(volume)
        self.moans_vol_label.config(text=f"{int(volume * 100)}%")
        print(f"💕 Moans volume: {int(volume * 100)}%")
     
    def _ensure_sticker_visibility(self):
        """FIXED sticker visibility - called once after full GUI initialization"""
        try:
            print("🎯 FINAL sticker visibility check...")
        
            # Trigger the actual startup load NOW
            if hasattr(self, "stickers") and self.stickers:
                print("🚀 Triggering startup load...")
                self.stickers.startup_load_when_ready()
        
            # Handle current tab - respect tab behavior
            current_tab_index = self.notebook.index(self.notebook.select())
            if current_tab_index == 0:  # Main control tab
                print("🟢 Main tab - showing stickers")
                if hasattr(self, "stickers") and self.stickers:
                    # Small delay to ensure stickers are loaded first
                    self.root.after(500, self.stickers.show_all)
            else:
                print("🔴 Other tab - hiding stickers")
                if hasattr(self, "stickers") and self.stickers:
                    self.stickers.hide_all()
                
        except Exception as e:
            print(f"⚠️ Sticker visibility error: {e}")
        
    def setup_gui(self):
        """Set up the main GUI with improved layout"""
    
        # Set minimum window size and make it resizable
        self.root.minsize(1400, 800)
        self.root.state('zoomed')  # Start maximized on Windows
    
        # Main container with better padding
        main_container = tk.Frame(self.root, bg='#000000')
        main_container.pack(fill='both', expand=True, padx=15, pady=15)
    
        # Left panel for video (60% width)
        video_container = tk.Frame(main_container, bg='#000000', relief='ridge', bd=2)
        video_container.pack(side=tk.LEFT, fill='both', expand=True, padx=(0, 15))
    
        # Right panel for controls (40% width, fixed)
        controls_container = tk.Frame(main_container, bg='#110011', width=900, relief='ridge', bd=2)
        controls_container.pack(side=tk.RIGHT, fill='y')
        controls_container.pack_propagate(False)  # Maintain fixed width
   
        # Setup notebook with better styling
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background='#220022', borderwidth=0)
        style.configure('TNotebook.Tab', background='#440044', foreground='#ff66cc', 
                       padding=[20, 10], font=('Gothic', 11, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', '#660066')], 
                  foreground=[('selected', '#ffffff')])
    
        self.notebook = ttk.Notebook(controls_container, style='TNotebook')
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
    
        # Create tabs with improved frames
        self.main_frame = tk.Frame(self.notebook, bg='#220022')
        self.joystick_frame = tk.Frame(self.notebook, bg='#220022')
       
    
        self.notebook.add(self.main_frame, text='♠ DARK CONTROL ♠')
        self.notebook.add(self.joystick_frame, text='♦ CONTROLLER ♦')
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # Setup all tabs
        self.setup_main_tab_fixed()
        self.setup_joystick_tab_fixed()
        self.setup_video_panel_fixed(video_container)

    def _on_tab_change(self, event):
        """Handle tab changes - hide stickers on non-main tabs"""
        current_tab_index = self.notebook.index(self.notebook.select())
        print(f"📂 Tab changed to index {current_tab_index}")
    
        if current_tab_index == 0:  # Main control tab
            print("🟢 Main tab - SHOWING stickers")
            if hasattr(self, "stickers") and self.stickers:
                self.stickers.show_all()
        else:
            print("🔴 Other tab - HIDING stickers so user can see settings")
            if hasattr(self, "stickers") and self.stickers:
                self.stickers.hide_all()
    
    def setup_main_tab_fixed(self):
        """Set up main control tab with better spacing and layout"""

        # Create scrollable frame for main content - WITH WORKING MOUSEWHEEL
        canvas = tk.Canvas(self.main_frame, bg='#220022', highlightthickness=0)
        scrollable_frame = tk.Frame(canvas, bg='#220022')
    
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
    
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
    
        scrollable_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.pack(fill="both", expand=True)
    
        # Bind mousewheel to canvas - FIXED VERSION
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)

        # Status section with better organization
        self.setup_status_section(scrollable_frame)

        # Speed control section
        self.setup_speed_section(scrollable_frame)

        # Build-up section
        self.setup_buildup_section(scrollable_frame)

        # Main controls
        self.setup_main_controls(scrollable_frame)

    def setup_status_section(self, parent):
        """Setup status section with compact audio controls"""
        status_container = tk.LabelFrame(
            parent, 
            text="♦ SYSTEM STATUS ♦", 
            font=("Gothic", 12, "bold"),
            fg='#ff66cc', 
            bg='#220022',
            labelanchor='n'
        )
        status_container.pack(pady=10, padx=20, fill='x')

        # Title and compact audio controls in red section
        title_audio_frame = tk.Frame(status_container, bg='#220022', relief='ridge', bd=2)
        title_audio_frame.pack(pady=10, padx=10, fill='x')

        # Main title
        tk.Label(
            title_audio_frame,
            text="sounds",
            font=("who asks satan", 24, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).pack(pady=(5, 2))

        # Compact audio controls - ENHANCED WITH DEVICE SELECTION
        audio_controls_frame = tk.Frame(title_audio_frame, bg='#220022')
        audio_controls_frame.pack(pady=(2, 8))

        # AUDIO DEVICE SELECTION - NEW!
        device_frame = tk.Frame(audio_controls_frame, bg='#220022')
        device_frame.pack(padx=20, pady=2)

        tk.Label(device_frame, text="Output:", font=("Gothic", 9, "bold"), 
                 fg='#ff66cc', bg='#220022').pack(side=tk.LEFT)

        self.audio_device_combo = ttk.Combobox(
            device_frame,
            width=20,
            state="readonly", 
            font=("Gothic", 8),
            values=self.audio_device_manager.get_available_devices()
        )
        self.audio_device_combo.set("Default System Output")
        self.audio_device_combo.pack(side=tk.LEFT, padx=5)
        self.audio_device_combo.bind("<<ComboboxSelected>>", self.on_audio_device_change)

        # Refresh device button
        tk.Button(
            device_frame,
            text="🔄",
            font=("Gothic", 8),
            bg='#444400',
            fg='#ffff66',
            width=3,
            command=self.refresh_audio_devices
        ).pack(side=tk.LEFT, padx=2)

        # Moans controls
        moans_frame = tk.Frame(audio_controls_frame, bg='#220022')
        moans_frame.pack(padx=20, pady=2)

        tk.Label(moans_frame, text="Moans:", font=("Gothic", 9, "bold"), 
                 fg='#ff66cc', bg='#220022').pack(side=tk.LEFT)

        # Moans checkbox
        self.moans_enabled_var = tk.BooleanVar(value=False)
        moans_check = tk.Checkbutton(
            moans_frame, 
            variable=self.moans_enabled_var,
            fg='#ff66cc', 
            bg='#220022', 
            selectcolor='#333333',
            command=self.toggle_moans_audio
        )
        moans_check.pack(side=tk.LEFT, padx=2)

        # Moans volume slider
        self.moans_volume_scale = tk.Scale(
            moans_frame,
            from_=0.0,
            to=1.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            length=80,
            bg='#220022',
           fg='#ff66cc',
            highlightthickness=0,
            troughcolor='#440044',
            activebackground='#ff66cc',
            font=("Gothic", 7),
            showvalue=False,
            command=self.on_moans_volume_change
        )
        self.moans_volume_scale.set(0.8)
        self.moans_volume_scale.pack(side=tk.LEFT, padx=2)

        # Moans volume label
        self.moans_vol_label = tk.Label(moans_frame, text="80%", font=("Gothic", 8), 
                                   fg='#ff66cc', bg='#220022')
        self.moans_vol_label.pack(side=tk.LEFT, padx=2)
    
        # Voice controls
        voice_frame = tk.Frame(audio_controls_frame, bg='#220022')
        voice_frame.pack(padx=20, pady=2)

        tk.Label(voice_frame, text="Voice:", font=("Gothic", 9, "bold"), 
                 fg='#ff66cc', bg='#220022').pack(side=tk.LEFT)

        # Voice checkbox
        self.voice_enabled_var = tk.BooleanVar(value=False)
        voice_check = tk.Checkbutton(
            voice_frame, 
            variable=self.voice_enabled_var,
            fg='#ff66cc', 
            bg='#220022', 
            selectcolor='#333333',
            command=self.toggle_voice_audio
        )
        voice_check.pack(side=tk.LEFT, padx=2)

        # Voice dropdown
        self.voice_combo = ttk.Combobox(
            voice_frame,
            width=10,
            state="readonly",
            font=("Gothic", 8),
            values=self.audio_manager.get_available_voices()
        )
        self.voice_combo.set(self.audio_manager.current_voice)
        self.voice_combo.pack(side=tk.LEFT, padx=2)
        self.voice_combo.bind("<<ComboboxSelected>>", self.on_voice_change)

        # Voice volume slider
        self.voice_volume_scale = tk.Scale(
            voice_frame,
            from_=0.0,
            to=1.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            length=80,
            bg='#220022',
            fg='#ff66cc',
            highlightthickness=0,
            troughcolor='#440044',
            activebackground='#ff66cc',
            font=("Gothic", 7),
            showvalue=False,
            command=self.on_voice_volume_change
        )
        self.voice_volume_scale.set(0.7)
        self.voice_volume_scale.pack(side=tk.LEFT, padx=2)

        # Voice volume label
        self.voice_vol_label = tk.Label(voice_frame, text="70%", font=("Gothic", 8), 
                                       fg='#ff66cc', bg='#220022')
        self.voice_vol_label.pack(side=tk.LEFT, padx=2)

        # Grid layout for status items (existing code)
        status_grid = tk.Frame(status_container, bg='#220022')
        status_grid.pack(pady=15, padx=15, fill='x')

        self.connection_label = tk.Label(
            status_grid,
            text="♦ Device: Connecting...",
            font=("Gothic", 11),
            fg='#ff99cc',
            bg='#220022'
        )
        self.connection_label.grid(row=0, column=0, sticky='w', pady=5)

        self.joystick_status_label = tk.Label(
            status_grid,
            text="♠ Controller: Not Connected",
            font=("Gothic", 11),
            fg='#cc3366',
            bg='#220022'
        )
        self.joystick_status_label.grid(row=1, column=0, sticky='w', pady=5)

        pattern_count = len(self.pattern_sequencer.pattern_database)
        tk.Label(
            status_grid,
            text=f"🎵 Patterns: {pattern_count} loaded",
            font=("Gothic", 11),
            fg='#66ff66' if pattern_count > 0 else '#ff4444',
            bg='#220022'
        ).grid(row=2, column=0, sticky='w', pady=5)

        # Add this after the pattern count label
        category_frame = tk.Frame(status_grid, bg='#220022')
        category_frame.grid(row=4, column=0, sticky='w', pady=5)

        tk.Label(
            category_frame,
            text="♦ Category:",
            font=("Gothic", 11, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).pack(side=tk.LEFT)

        self.category_combo = ttk.Combobox(
            category_frame,
            width=12,
            state="readonly",
            font=("Gothic", 9),
            values=self.pattern_sequencer.get_available_categories()
        )
        self.category_combo.set(self.current_category)
        self.category_combo.pack(side=tk.LEFT, padx=10)
        self.category_combo.bind("<<ComboboxSelected>>", self.on_category_change)

        self.manual_status_label = tk.Label(
            status_grid,
            text="♦ Manual Override: Inactive",
            font=("Gothic", 11, "bold"),
            fg='#888888',
            bg='#220022'
        )
        self.manual_status_label.grid(row=3, column=0, sticky='w', pady=5)


    def on_category_change(self, event=None):
        """Handle category selection change"""
        new_category = self.category_combo.get()
        if new_category != self.current_category:
            self.current_category = new_category
        
            # Stop playback if running
            was_running = self.running
            if was_running:
                self.stop_playback()
        
            # Reload patterns from new category
            self.pattern_sequencer.load_patterns(new_category)
            self.audio_manager.play('category_change')
        
            # Update pattern count display
            pattern_count = len(self.pattern_sequencer.pattern_database)
            # Find and update your pattern count label (you'll need to make this a self. variable)
        
            # Restart if was running
            if was_running:
                self.start_playback()
        
            print(f"🔄 Switched to category: {new_category} ({pattern_count} patterns)")        
    
    def setup_speed_section(self, parent):
        """Setup speed control section with FIXED range: 0.1x to 1.5x (1x in middle)"""
        speed_container = tk.LabelFrame(
            parent,
            text="(SPEED)",
            font=("honey cute", 14,),
            fg='#ff66cc',
            bg='#220022',
            labelanchor='n'
        )
        speed_container.pack(pady=15, padx=20, fill='x')

        # Speed labels frame - UPDATED LABELS
        labels_frame = tk.Frame(speed_container, bg='#220022')
        labels_frame.pack(pady=(15, 5), padx=20, fill='x')

        tk.Label(
            labels_frame, 
            text="Slow (0.1x)", 
            font=("Gothic", 10), 
            fg='#44ff88', 
            bg='#220022'
        ).pack(side=tk.LEFT)

        tk.Label(
            labels_frame, 
            text="Fast (1.5x)", 
            font=("Gothic", 10), 
            fg='#cc3366', 
            bg='#220022'
        ).pack(side=tk.RIGHT)

        # Speed slider with FIXED range
        slider_frame = tk.Frame(speed_container, bg='#220022')
        slider_frame.pack(pady=10, padx=20)

        # 🔧 FIXED: Create slider with NEW range 0.1 to 1.5, 1.0 as default
        self.arousal_scale = tk.Scale(
            slider_frame,
            from_=0.1,        # CHANGED: minimum 0.1x
            to=1.5,           # CHANGED: maximum 1.5x  
            resolution=0.1,   # UNCHANGED: 0.1 increments
            orient=tk.HORIZONTAL,
            length=400,
            bg='#220022',
            fg='#ff66cc',
            highlightthickness=0,
            troughcolor='#440044',
            activebackground='#ff66cc',
            font=("Gothic", 10)
            # 🔧 NO COMMAND HERE DURING CREATION
        )

        # 🔧 Set default to 1.0x (middle of new range) BEFORE setting up callback
        self.arousal_scale.set(1.0)
        self.arousal = 1.0  # Set the value directly

        # 🔧 NOW attach the callback AFTER setting the initial value
        self.arousal_scale.config(command=self.on_speed_change)

        self.arousal_scale.pack()

        # Current speed display
        self.speed_display_label = tk.Label(
            speed_container,
            text="Current Speed: 1.00x",
            font=("Gothic", 12, "bold"),
            fg='#ff99cc',
            bg='#220022'
        )
        self.speed_display_label.pack(pady=(5, 15))

    def setup_buildup_section(self, parent):
        """Setup build-up section with FIXED speed limits"""
        buildup_container = tk.LabelFrame(
            parent,
            text="♥ BUILD-UP MODE ♥",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022',
            labelanchor='n'
        )
        buildup_container.pack(pady=15, padx=20, fill='x')

        # Input controls in a grid
        inputs_frame = tk.Frame(buildup_container, bg='#220022')
        inputs_frame.pack(pady=15, padx=15, fill='x')

        # Time input
        tk.Label(
            inputs_frame,
            text="Time (seconds):",
            font=("Gothic", 10, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).grid(row=0, column=0, padx=10, pady=5, sticky='w')

        self.buildup_time_entry = MouseWheelEntry(
            inputs_frame,
            increment=30,
            min_value=30,
            max_value=3600,
            width=10,
            font=("Gothic", 11),
            bg='#440044',
            fg='#ff66cc',
            insertbackground='#ffffff',
            justify='center'
        )
        self.buildup_time_entry.grid(row=1, column=0, padx=10, pady=5)
        self.buildup_time_entry.insert(0, "60")  # Plain seconds format

        # Cycles input
        tk.Label(
            inputs_frame,
            text="Build-ups:",
            font=("Gothic", 10, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).grid(row=0, column=1, padx=10, pady=5, sticky='w')

        self.buildup_cycles_entry = MouseWheelEntry(
           inputs_frame,
            increment=1,
            min_value=1,
            max_value=50,
            width=8,
            font=("Gothic", 11),
            bg='#440044',
            fg='#ff66cc',
            insertbackground='#ffffff',
            justify='center'
        )
        self.buildup_cycles_entry.grid(row=1, column=1, padx=10, pady=5)
        self.buildup_cycles_entry.insert(0, "1")

        # Max Speed input - FIXED LIMITS
        tk.Label(
            inputs_frame,
            text="Max Speed:",
            font=("Gothic", 10, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).grid(row=0, column=2, padx=10, pady=5, sticky='w')

        self.buildup_max_speed_entry = DecimalMouseWheelEntry(
            inputs_frame,
            increment=0.1,
            min_value=0.1,    # CHANGED: minimum 0.1x
            max_value=1.5,    # CHANGED: maximum 1.5x
            width=8,
            font=("Gothic", 11),
            bg='#440044',
            fg='#ff66cc',
            insertbackground='#ffffff',
            justify='center'
        )
        self.buildup_max_speed_entry.grid(row=1, column=2, padx=10, pady=5)
        self.buildup_max_speed_entry.insert(0, "1.5")  # CHANGED: default to max
        # Folder cycling controls - ADD THIS ENTIRE SECTION
        folder_cycling_frame = tk.Frame(inputs_frame, bg='#220022')
        folder_cycling_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky='w')

        self.folder_cycling_var = tk.BooleanVar()
        # ... more UI code ...
        self.change_interval_entry = MouseWheelEntry(
            folder_cycling_frame,
            increment=30,
            min_value=30,
            max_value=600,
            width=8,
            font=("Gothic", 10),
            bg='#440044',
            fg='#ff66cc'
        )
        tk.Checkbutton(
            folder_cycling_frame,
            text="Cycle Folders During Build-up",
            variable=self.folder_cycling_var,
            fg='#ff66cc',
            bg='#220022',
            selectcolor='#333333',
            font=("Gothic", 10, "bold")
        ).pack(side=tk.LEFT)

        tk.Label(folder_cycling_frame, text="Change:", font=("Gothic", 10), 
                 fg='#ff66cc', bg='#220022').pack(side=tk.LEFT, padx=(20,5))

        self.change_trigger_combo = ttk.Combobox(
            folder_cycling_frame,
            width=20,
            state="readonly",
            font=("Gothic", 9),
            values=["Change every X min:sec", "Change every X strokes", "Change every 25%", "Change every X patterns"]
        )
        self.change_trigger_combo.set("Change every X min:sec")
        self.change_trigger_combo.pack(side=tk.LEFT, padx=5)
        self.change_trigger_combo.set("Change every X min:sec")
        self.change_trigger_combo.pack(side=tk.LEFT, padx=5)
        self.on_trigger_type_change()  # ADD THIS LINE - calls it once on startup

        self.change_interval_entry = MouseWheelEntry(
            folder_cycling_frame,
            increment=30,
            min_value=30,
            max_value=600,
            width=8,
            font=("Gothic", 10),
            bg='#440044',
            fg='#ff66cc'
        )
        self.change_interval_entry.pack(side=tk.LEFT, padx=5)
        self.change_interval_entry.insert(0, "2:00")

        # ADD THESE TWO LINES AT THE END:
        self.change_trigger_combo.bind("<<ComboboxSelected>>", self.on_trigger_type_change)
        self.on_trigger_type_change()  # Call once to set initial state

        # Buttons frame
        buttons_frame = tk.Frame(buildup_container, bg='#220022')
        buttons_frame.pack(pady=15)

        self.buildup_start_button = tk.Button(
            buttons_frame,
            text="♠ START BUILD-UP ♠",
            font=("Gothic", 11, "bold"),
            bg='#004400',
            fg='#66ff66',
            width=18,
            height=2,
            command=self.start_buildup_mode
        )
        self.buildup_start_button.pack(side=tk.LEFT, padx=10)

        self.buildup_stop_button = tk.Button(
            buttons_frame,
            text="♦ STOP BUILD-UP ♦",
            font=("Gothic", 11, "bold"),
            bg='#440000',
            fg='#ff6666',
            width=18,
            height=2,
            command=self.stop_buildup_mode,
            state='disabled'
        )
        self.buildup_stop_button.pack(side=tk.LEFT, padx=10)

        # Status label
        self.buildup_status_label = tk.Label(
            buildup_container,
            text="Build-up: Inactive",
            font=("Gothic", 10),
            fg='#888888',
            bg='#220022'
        )
        self.buildup_status_label.pack(pady=(0, 15))

    def on_fullscreen_button_click(self):
        """Handle fullscreen button click"""
        try:
            if hasattr(self, 'video_visualizer') and self.video_visualizer:
                if not self.video_visualizer.video_frames:
                    messagebox.showwarning("No Video", "Please load a video first!")
                    return
            
                print("🖥️ Toggling fullscreen mode...")
                self.video_visualizer.toggle_fullscreen()
            else:
                messagebox.showerror("Error", "Video system not initialized!")
        except Exception as e:
            print(f"❌ Fullscreen button error: {e}")
            messagebox.showerror("Error", f"Failed to toggle fullscreen: {e}")        

    def setup_main_controls(self, parent):
        """Setup main control buttons with better layout"""
        self.play_button = tk.Button(
            parent,
            text="PLAY",
            font=("Gothic", 16, "bold"),
            bg='#004400',
            fg='#66ff66',
        width=20,
            height=3,
            command=self.toggle_playback,
            state='disabled'
        )
        self.play_button.pack(pady=10)

        # 🌪️ ADD THIS CHAOS MODE SECTION
        chaos_frame = tk.LabelFrame(
            parent,
            text="🌪️ CHAOS MODE 🌪️",
            font=("Gothic", 12, "bold"),
            fg='#ff6666',
            bg='#220022',
            labelanchor='n'
        )
        chaos_frame.pack(pady=15, padx=20, fill='x')
    
        # Chaos checkbox with description
        chaos_control_frame = tk.Frame(chaos_frame, bg='#220022')
        chaos_control_frame.pack(pady=15, padx=15)
    
        self.chaos_mode_var = tk.BooleanVar()
        chaos_checkbox = tk.Checkbutton(
            chaos_control_frame,
            text="🤖 BOT TAKES CONTROL",
            variable=self.chaos_mode_var,
            font=("Gothic", 14, "bold"),
            fg='#ff6666',
            bg='#220022',
            selectcolor='#660000',
            activeforeground='#ff9999',
            activebackground='#330011',
            command=self.toggle_chaos_mode
        )
        chaos_checkbox.pack(pady=5)
    
        # Chaos description
        chaos_desc = tk.Label(
            chaos_control_frame,
            text="Speed changes every 2-6s | Folders every 12-25s | Patterns every 4-8s\nChaotic but not manic - perfect chaos balance!",
            font=("Gothic", 10),
            fg='#ff6666',
            bg='#220022',
            justify='center'
        )
        chaos_desc.pack(pady=(0, 10))
    
        # Chaos status display
        self.chaos_status_label = tk.Label(
            chaos_frame,
            text="Chaos Mode: Inactive",
            font=("Gothic", 11, "bold"),
            fg='#888888',
            bg='#220022'
        )
        self.chaos_status_label.pack(pady=(0, 15))
    
      
    
        # Status display
        status_display_frame = tk.Frame(parent, bg='#220022')
        status_display_frame.pack(pady=(15, 20), padx=15, fill='x')
    
        self.status_label = tk.Label(
            status_display_frame,
            text="Waiting for device connection...",
            font=("Gothic", 11),
            fg='#888888',
            bg='#220022',
            wraplength=350
        )
        self.status_label.pack(pady=5)
    
        self.pattern_display = tk.Label(
            status_display_frame,
            text="Stream: Ready | Position: -- | Mode: Pattern",
            font=("Gothic", 10),
            fg='#66ff66',
            bg='#220022',
            wraplength=350
        )
        self.pattern_display.pack(pady=5)

    def setup_video_panel_fixed(self, video_container):
       """Setup video panel with better proportions and spacing"""
   
       # Title with better styling
       title_frame = tk.Frame(video_container, bg='#000000')
       title_frame.pack(pady=15, fill='x')
   
       tk.Label(
           title_frame, 
           text="♠ VIDEO DARK VISUALIZER ♠", 
           font=("Gothic", 16, "bold"), 
           fg='#ff66cc', 
           bg='#000000'
       ).pack()
   
       # Controls section with better organization
       controls_section = tk.Frame(video_container, bg='#110011', relief='ridge', bd=1)
       controls_section.pack(pady=10, padx=15, fill='x')
   
       # Top controls row
       top_controls = tk.Frame(controls_section, bg='#110011')
       top_controls.pack(pady=10, fill='x')
   
       # Open video button
       tk.Button(
           top_controls, 
           text="♦ OPEN VIDEO ♦", 
           font=("Gothic", 11, "bold"), 
           bg='#004400', 
           fg='#66ff66', 
           width=15,
           height=2,
           command=self.open_video
       ).pack(side=tk.LEFT, padx=10)
   
       # Direction controls in a frame
       direction_frame = tk.LabelFrame(
           top_controls, 
           text="Direction", 
           font=("Gothic", 9, "bold"),
           fg='#ff66cc', 
           bg='#110011'
       )
       direction_frame.pack(side=tk.LEFT, padx=20)
   
       self.direction_var = tk.StringVar(value="0_to_100")
       direction_combo = ttk.Combobox(
           direction_frame, 
           textvariable=self.direction_var, 
           values=["0_to_100", "100_to_0"], 
           state="readonly", 
           width=12,
           font=("Gothic", 9)
       )
       direction_combo.pack(pady=5, padx=5)
       direction_combo.bind("<<ComboboxSelected>>", self.on_video_direction_change)
   
       self.video_invert_var = tk.BooleanVar()
       tk.Checkbutton(
           direction_frame, 
           text="Invert", 
           variable=self.video_invert_var, 
           fg='#ff66cc', 
           bg='#110011', 
           selectcolor='#333333',
           font=("Gothic", 9),
           command=self.on_video_direction_change
       ).pack(pady=2)
   
       # Test controls
       test_frame = tk.LabelFrame(
           top_controls, 
           text="Test Mode", 
           font=("Gothic", 9, "bold"),
           fg='#ff66cc', 
           bg='#110011'
       )
       test_frame.pack(side=tk.LEFT, padx=20)
   
       self.test_mode_var = tk.BooleanVar()
       tk.Checkbutton(
           test_frame, 
           text="Enable Test", 
           variable=self.test_mode_var, 
           fg='#ff66cc', 
           bg='#110011', 
           selectcolor='#333333',
           font=("Gothic", 9)
       ).pack(pady=5)
   
       self.test_slider = tk.Scale(
           test_frame, 
           from_=0, 
           to=100, 
           resolution=1, 
           orient=tk.HORIZONTAL, 
           length=150, 
           bg='#110011', 
           fg='#ff66cc', 
           highlightthickness=0, 
           troughcolor='#440044', 
           activebackground='#ff66cc',
           font=("Gothic", 8),
           command=self.on_test_position_change
       )
       self.test_slider.set(50)
       self.test_slider.pack(pady=5)

       # Sticker controls
       sticker_frame = tk.LabelFrame(
           top_controls,
           text="Stickers",
           font=("Gothic", 9, "bold"),
           fg='#ff66cc',
           bg='#110011'
       )
       sticker_frame.pack(side=tk.LEFT, padx=20)
       
       sticker_btn_frame = tk.Frame(sticker_frame, bg='#110011')
       sticker_btn_frame.pack(pady=5, padx=5)

       tk.Button(
           sticker_btn_frame,
           text="➕ ADD",
           font=("Gothic", 8, "bold"),
           bg='#004400',
           fg='#66ff66',
           width=8,
           command=self.stickers.add_sticker
       ).pack(side=tk.TOP, pady=2)

       tk.Button(
           sticker_btn_frame,
           text="🔒 LOCK",
           font=("Gothic", 8, "bold"),
           bg='#444400',
           fg='#ffff66',
           width=8,
           command=self.stickers.toggle_lock_all
       ).pack(side=tk.TOP, pady=2)

       tk.Button(
           sticker_btn_frame,
           text="💾 SAVE",
           font=("Gothic", 8, "bold"),
           bg='#440044',
           fg='#ff66cc',
           width=8,
           command=self.stickers.save_as_startup
       ).pack(side=tk.TOP, pady=2)

       tk.Button(
           sticker_btn_frame,
           text="🧹 CLEAR",
           font=("Gothic", 8, "bold"),
           bg='#440000',
           fg='#ff6666',
           width=8,
           command=self.stickers.clear_all
       ).pack(side=tk.TOP, pady=2)

       # Video switching controls
       switching_frame = tk.LabelFrame(
           top_controls,
           text="Auto Switch",
           font=("Gothic", 9, "bold"),
           fg='#ff66cc',
           bg='#110011'
       )
       switching_frame.pack(side=tk.LEFT, padx=20)
       
       # Time switching
       time_row = tk.Frame(switching_frame, bg='#110011')
       time_row.pack(pady=2)
       
       tk.Label(time_row, text="🕒", font=("Gothic", 8), fg='#ff66cc', bg='#110011').pack(side=tk.LEFT)
       
       self.random_interval_entry = MouseWheelEntry(
           time_row, 
           increment=5,
           min_value=5,
           max_value=300,
           width=4, 
           font=("Gothic", 10, "bold"),
           bg='#ffffff', 
           fg='#000000',
           insertbackground='#000000',
           justify='center'
       )
       self.random_interval_entry.pack(side=tk.LEFT, padx=2)
       self.random_interval_entry.insert(0, "30")
       
       tk.Label(time_row, text="sec", font=("Gothic", 8), fg='#ff66cc', bg='#110011').pack(side=tk.LEFT)
       
       self.random_enabled = tk.BooleanVar()
       tk.Checkbutton(time_row, text="Time", variable=self.random_enabled, 
                      font=("Gothic", 8), fg='#ff66cc', bg='#110011', 
                      selectcolor='#333333', command=self.on_random_toggle).pack(side=tk.LEFT, padx=2)
       
       # Stroke switching
       stroke_row = tk.Frame(switching_frame, bg='#110011')
       stroke_row.pack(pady=2)
       
       tk.Label(stroke_row, text="🎬", font=("Gothic", 8), fg='#ff66cc', bg='#110011').pack(side=tk.LEFT)
       
       self.stroke_interval_entry = MouseWheelEntry(
           stroke_row, 
           increment=1,
           min_value=1,
           max_value=100,
           width=4, 
           font=("Gothic", 10, "bold"),
           bg='#ffffff', 
           fg='#000000',
           insertbackground='#000000',
           justify='center'
       )
       self.stroke_interval_entry.pack(side=tk.LEFT, padx=2)
       self.stroke_interval_entry.insert(0, "10")
       
       tk.Label(stroke_row, text="strokes", font=("Gothic", 8), fg='#ff66cc', bg='#110011').pack(side=tk.LEFT)
       
       self.stroke_enabled = tk.BooleanVar()
       tk.Checkbutton(stroke_row, text="Stroke", variable=self.stroke_enabled,
                      font=("Gothic", 8), fg='#ff66cc', bg='#110011',
                      selectcolor='#333333', command=self.on_stroke_toggle).pack(side=tk.LEFT, padx=2)
   
       # Video display area with better proportions
       video_display_frame = tk.Frame(video_container, bg='#000000', relief='sunken', bd=2)
       video_display_frame.pack(fill='both', expand=True, padx=15, pady=10)
   
       self.video_label = tk.Label(
           video_display_frame, 
           text="Load a video to see visualization\n\nSupported formats: MP4, AVI, MOV, MKV, WEBM", 
           font=("Gothic", 14), 
           fg='#888888', 
           bg='#000000'
       )
       self.video_label.pack(fill='both', expand=True)
   
       # Video status and navigation
       nav_section = tk.Frame(video_container, bg='#110011', relief='ridge', bd=1)
       nav_section.pack(pady=10, padx=15, fill='x')

       
   
       # Video navigation
       nav_frame = tk.Frame(nav_section, bg='#110011')
       nav_frame.pack(pady=8, fill='x')
   
       self.prev_video_btn = tk.Button(
           nav_frame, 
           text="◀ PREV", 
           font=("Gothic", 10, "bold"),
           bg='#554455', 
           fg='#ff6666', 
           width=10, 
           state='disabled'
       )
       self.prev_video_btn.pack(side=tk.LEFT, padx=5)
   
       self.current_video_name = tk.Label(
           nav_frame, 
           text="No Video Loaded", 
           font=("Gothic", 11, "bold"), 
           fg='#ff66cc', 
           bg='#110011'
       )
       self.current_video_name.pack(side=tk.LEFT, expand=True, padx=20)
   
       self.delete_video_btn = tk.Button(
           nav_frame, 
           text="🗑️", 
           font=("Gothic", 11, "bold"),
           bg='#440000', 
           fg='#ff6666', 
           width=4, 
           state='disabled'
       )
       self.delete_video_btn.pack(side=tk.RIGHT, padx=2)
   
       self.save_video_btn = tk.Button(
           nav_frame, 
           text="SAVE", 
           font=("Gothic", 10, "bold"),
           bg='#004400', 
           fg='#66ff66', 
           width=8, 
           state='disabled'
       )
       self.save_video_btn.pack(side=tk.RIGHT, padx=5)
   
       self.next_video_btn = tk.Button(
           nav_frame, 
           text="NEXT ▶", 
           font=("Gothic", 10, "bold"),
           bg='#554455', 
           fg='#ff6666', 
           width=10, 
           state='disabled'
       )
       self.next_video_btn.pack(side=tk.RIGHT, padx=5)
   
       # Video status
       self.video_status_label = tk.Label(
           nav_section, 
           text="🎹 No video loaded", 
           font=("Gothic", 10), 
           fg='#888888', 
           bg='#110011'
       )
       self.video_status_label.pack(pady=(0, 8))
       
       # Gallery section with better layout
       self.setup_gallery_section(video_container)
   
       # Initialize video visualizer
       self.video_visualizer = VideoVisualizer(self.root)
       self.video_visualizer.video_label = self.video_label
       self.video_visualizer.invert_var = self.video_invert_var
       self.video_visualizer.test_mode_var = self.test_mode_var
       self.video_visualizer.test_slider = self.test_slider
   
       # Connect callbacks
       self.connect_video_callbacks()
       self.start_video_position_monitoring()

       tk.Button(
           top_controls, 
           text="🖥️ FULLSCREEN", 
           font=("Gothic", 11, "bold"), 
           bg='#440044', 
           fg='#ff66cc', 
           width=12,
           height=2,
           command=self.on_fullscreen_button_click
       ).pack(side=tk.LEFT, padx=10)


    def auto_load_last_video(self):
        """Auto-load the last selected video from gallery"""
        try:
            print(f"🔍 Auto-load check: {len(self.video_gallery.videos)} videos, index {self.video_gallery.current_index}")
        
            if self.video_gallery.videos:
                # Force update gallery display first
                self.update_gallery_display()
            
                # RE-CONNECT the video navigation buttons
                self.prev_video_btn.config(command=self.load_prev_video)
                self.next_video_btn.config(command=self.load_next_video)
            
                # Then load the current video
                if self.video_gallery.current_index < len(self.video_gallery.videos):
                    current_video = self.video_gallery.get_current_video()
                    if current_video:
                        print(f"🎬 Auto-loading: {current_video['name']}")
                        self.load_gallery_video()
                        return
        
            print("ℹ️ No video to auto-load")
        
        except Exception as e:
            print(f"⚠️ Error auto-loading video: {e}")
            import traceback
            traceback.print_exc()      


    def setup_gallery_section(self, parent):
        """Setup gallery section with stroke-based video switching"""
        gallery_container = tk.LabelFrame(
            parent,
            text="♦ VIDEO GALLERY ♦",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#000000',
            labelanchor='n'
        )
        gallery_container.pack(pady=15, padx=15, fill='x')

        # Gallery navigation
        gallery_nav_frame = tk.Frame(gallery_container, bg='#000000')
        gallery_nav_frame.pack(pady=10, fill='x')

        self.prev_gallery_btn = tk.Button(
            gallery_nav_frame, 
            text="◄ GALLERY", 
            font=("Gothic", 10, "bold"), 
            bg='#554455', 
            fg='#ff6666', 
            width=12, 
            state='disabled'
        )
        self.prev_gallery_btn.pack(side=tk.LEFT, padx=5)

        self.gallery_status = tk.Label(
            gallery_nav_frame, 
            text="Gallery: 0 videos", 
            font=("Gothic", 11, "bold"), 
            fg='#ff66cc', 
            bg='#000000'
        )
        self.gallery_status.pack(expand=True)

        self.next_gallery_btn = tk.Button(
            gallery_nav_frame, 
            text="GALLERY ►", 
            font=("Gothic", 10, "bold"), 
            bg='#554455', 
            fg='#ff6666', 
            width=12, 
            state='disabled'
        )
        self.next_gallery_btn.pack(side=tk.RIGHT, padx=5)

        # Gallery thumbnails frame
        self.gallery_frame = tk.Frame(gallery_container, bg='#000000')
        self.gallery_frame.pack(pady=10, fill='x', padx=10)

        # Auto-load last selected video
        self.root.after(2000, self.auto_load_last_video)

        # Create 5 thumbnail slots
        self.gallery_thumbnails = []
        for i in range(5):
            thumb_frame = tk.Frame(
                self.gallery_frame, 
                bg='#440044', 
                relief='raised', 
                bd=2,
                width=110,
                height=100
            )
            thumb_frame.pack(side=tk.LEFT, padx=3, fill='both', expand=True)
            thumb_frame.pack_propagate(False)

            thumb_label = tk.Label(
                thumb_frame, 
                text=f"Slot {i+1}\nEmpty", 
                font=("Gothic", 8, "bold"), 
                fg='#666666', 
                bg='#440044',
                compound='center',
                width=400,
                height=300
            )
            thumb_label.pack(pady=(5, 0), expand=True)
            thumb_label.bind("<Button-1>", lambda e, idx=i: self.on_thumbnail_click(idx))

            name_label = tk.Label(
                thumb_frame, 
                text="", 
                font=("Gothic", 7), 
                fg='#cccccc', 
                bg='#440044',
                wraplength=100
            )
            name_label.pack(pady=(0, 2))

            self.gallery_thumbnails.append({
                'frame': thumb_frame,
                'label': thumb_label,
                'name': name_label,
                'video_id': None
            })

            

            
                                   
    def setup_joystick_tab_fixed(self):
        """Set up joystick configuration tab with video navigation - UPDATED"""

        # Create scrollable frame
        canvas = tk.Canvas(self.joystick_frame, bg='#220022', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.joystick_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#220022')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Title
        tk.Label(
            scrollable_frame,
            text="♦ CONTROLLER CONFIGURATION ♦",
            font=("Gothic", 16, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).pack(pady=20)

        # Device selection section
        device_container = tk.LabelFrame(
            scrollable_frame,
            text="♠ DEVICE SELECTION ♠",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022',
            labelanchor='n'
        )
        device_container.pack(pady=15, padx=20, fill='x')

        device_select_frame = tk.Frame(device_container, bg='#220022')
        device_select_frame.pack(pady=15, fill='x')

        tk.Label(
            device_select_frame, 
            text="Joystick Device:", 
                font=("Gothic", 11, "bold"), 
            fg='#ff66cc', 
            bg='#220022'
        ).pack(side=tk.LEFT, padx=10)

        self.device_combo = ttk.Combobox(
            device_select_frame,
            width=35,
            state="readonly",
            font=("Gothic", 9)
        )
        self.device_combo.pack(side=tk.LEFT, padx=10)
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_selected)

        tk.Button(
            device_select_frame,
            text="♦ Refresh ♦",
            font=("Gothic", 10, "bold"),
            bg='#554455',
            fg='#ff6666',
            command=self.refresh_joystick_devices
        ).pack(side=tk.LEFT, padx=10)

        # Control mapping section
        config_container = tk.LabelFrame(
            scrollable_frame,
            text="♥ CONTROL MAPPING ♥",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022',
            labelanchor='n'
        )
        config_container.pack(pady=15, padx=20, fill='x')

        # Create control mapping grid
        mapping_frame = tk.Frame(config_container, bg='#220022')
        mapping_frame.pack(pady=15, padx=15, fill='x')

        # Header row
        headers = ["Control", "Assignment", "Detect", "Options"]
        for i, header in enumerate(headers):
            tk.Label(
                mapping_frame,
                text=header,
                font=("Gothic", 11, "bold"),
                fg='#ff66cc',
                bg='#220022'
            ).grid(row=0, column=i, padx=10, pady=10, sticky='w')

        # 🔧 UPDATED: Control rows with NEW VIDEO BUTTONS
        controls = [
            ("Speed Control Axis:", "speed"),
            ("Manual Control Axis:", "manual"),
            ("Manual Override Button:", "manual_btn"),
            ("Skip Pattern Button:", "skip"),
            ("Play/Pause Button:", "play_pause"),
            ("Next Video Button:", "next_video"),      # 🔧 NEW
            ("Previous Video Button:", "prev_video")   # 🔧 NEW
        ]

        for i, (label_text, control_type) in enumerate(controls, 1):
            self.create_control_row_fixed(mapping_frame, label_text, control_type, i)

        # Apply button
        apply_frame = tk.Frame(config_container, bg='#220022')
        apply_frame.pack(pady=20)

        tk.Button(
            apply_frame,
            text="♠ APPLY CONFIGURATION ♠",
            font=("Gothic", 12, "bold"),
            bg='#004400',
            fg='#66ff66',
            width=25,
            height=2,
            command=self.apply_joystick_config
        ).pack()

        # Live monitoring section
        live_container = tk.LabelFrame(
            scrollable_frame,
            text="♦ LIVE INPUT MONITORING ♦",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022',
            labelanchor='n'
        )
        live_container.pack(pady=15, padx=20, fill='x')

        monitor_frame = tk.Frame(live_container, bg='#220022')
        monitor_frame.pack(pady=15, padx=15)

        self.axis_value_label = tk.Label(
            monitor_frame,
            text="Speed Axis: 0.000 | Manual Axis: 0.000",
            font=("Gothic", 11, "bold"),
            fg='#66ff66',
            bg='#220022'
        )
        self.axis_value_label.pack(pady=5)

        # 🔧 UPDATED: Button states to include video buttons
        self.button_states_label = tk.Label(
            monitor_frame,
            text="Buttons: Manual:OFF Skip:OFF Play/Pause:OFF NextVid:OFF PrevVid:OFF",
            font=("Gothic", 10, "bold"),
            fg='#66ff66',
            bg='#220022'
        )
        self.button_states_label.pack(pady=5)

        # Instructions section
        instructions_container = tk.LabelFrame(
            scrollable_frame,
            text="♠ INSTRUCTIONS ♠",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022',
            labelanchor='n'
        )
        instructions_container.pack(pady=15, padx=20, fill='x')

        instructions_text = tk.Text(
            instructions_container,
            height=10,
            width=60,
            font=("Gothic", 10),
            bg='#330033',
            fg='#cccccc',
            wrap=tk.WORD,
            relief='sunken',
            bd=2
        )
        instructions_text.pack(pady=15, padx=15)

        # 🔧 UPDATED: Instructions to include video buttons
        instructions = """♦ Click DETECT next to each control to configure
    ♦ Speed Axis: Controls playback speed (neutral=1x, pull=slow, push=fast)
    ♦ Manual Axis: Position control during manual override
    ♦ Manual Override: Hold + move manual axis for direct control
    ♦ Skip Pattern: Jump to next pattern smoothly
    ♦ Play/Pause: Single button toggles playback
    ♦ Next Video: Switch to next video in gallery
    ♦ Previous Video: Switch to previous video in gallery
    ♦ Mouse wheel on time inputs: ±30 seconds per scroll
    ♦ Invert: Reverses axis direction
    ♦ Modes: full_range, half_positive, half_negative, trigger"""

        instructions_text.insert(tk.END, instructions)
        instructions_text.config(state=tk.DISABLED)

        self.root.after(100, self.refresh_joystick_devices)
        self.root.after(500, self.load_joystick_config_delayed)

        
    def create_control_row_fixed(self, parent, label_text, control_type, row):
        """Create improved control configuration row - FIXED VERSION"""

        # Control label
        tk.Label(
            parent,
            text=label_text,
            font=("Gothic", 10, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).grid(row=row, column=0, padx=10, pady=8, sticky='w')

        # Detection label
        label = tk.Label(
            parent,
            text="Not Set",
            font=("Gothic", 10, "bold"),
            fg='#cc3366',
            bg='#440044',
            width=15,
            relief='sunken',
            bd=2
        )
        label.grid(row=row, column=1, padx=10, pady=8)
        setattr(self, f"detect_{control_type}_label", label)

        # Detect button
        if control_type in ["speed", "manual"]:  # Axis controls
            command = lambda ct=control_type: self.start_axis_detection(ct)
            bg_color = '#44aa44'
            button_text = "DETECT AXIS"
        else:  # Button controls
            command = lambda ct=control_type: self.start_button_detection(ct)
            bg_color = '#4444aa'
            button_text = "DETECT BTN"

        button = tk.Button(
            parent,
            text=button_text,
            font=("Gothic", 9, "bold"),
            bg=bg_color,
            fg='#ffffff',
            width=12,
            command=command
        )
        button.grid(row=row, column=2, padx=10, pady=8)
        setattr(self, f"detect_{control_type}_btn", button)

        # Options frame for axes only
        if control_type in ["speed", "manual"]:
            options_frame = tk.Frame(parent, bg='#220022')
            options_frame.grid(row=row, column=3, padx=10, pady=8, sticky='w')
    
            # Invert checkbox
            invert_var = tk.BooleanVar()
            setattr(self, f"{control_type}_invert_var", invert_var)
    
            tk.Checkbutton(
                options_frame,
                text="Invert",
                variable=invert_var,
                fg='#ff66cc',
                bg='#220022',
                selectcolor='#333333',
                font=("Gothic", 9, "bold")
            ).pack(side=tk.LEFT, padx=5)
    
            # Mode dropdown
            mode_combo = ttk.Combobox(
            options_frame,
                width=12,
                state="readonly",
                font=("Gothic", 8),
                values=["full_range", "half_positive", "half_negative", "trigger"]
            )
            mode_combo.set("full_range")
            mode_combo.pack(side=tk.LEFT, padx=5)
            setattr(self, f"{control_type}_mode_combo", mode_combo)

    def connect_video_callbacks(self):
        """Connect all video-related callbacks"""
        self.save_video_btn.config(command=self.save_current_video)
        self.delete_video_btn.config(command=self.delete_current_video)
        self.prev_video_btn.config(command=self.load_prev_video)
        self.next_video_btn.config(command=self.load_next_video)
        self.prev_gallery_btn.config(command=self.prev_gallery_page)
        self.next_gallery_btn.config(command=self.next_gallery_page)
    
        # Update gallery display
        self.update_gallery_display()

    def on_voice_change(self, event=None):
        """Handle voice selection change"""
        pass  # Just update the selection, don't apply yet
    
    def on_volume_change(self, value):
        """Handle volume change"""
        self.audio_manager.set_volume(float(value))

    def toggle_audio_system(self):
        """Toggle audio system on/off"""
        enabled = self.audio_manager.toggle_enabled()
        if enabled:
            self.audio_manager.play('device_connect')

    def test_all_audio_triggers(self):
        """Test all audio triggers sequentially"""
        import threading
    
        def test_sequence():
            triggers = list(self.audio_manager.trigger_mappings.keys())
            for trigger in triggers:
                self.audio_manager.play(trigger)
                time.sleep(1.5)  # Wait between sounds
    
        threading.Thread(target=test_sequence, daemon=True).start()

    # ADDITIONAL STYLING IMPROVEMENTS


    def on_random_toggle(self):
        """Handle time-based random toggle - COMPLETE VERSION"""
        if self.random_enabled.get():
            if self.stroke_enabled.get():
                self.stroke_enabled.set(False)  # Disable stroke mode
            self.start_random_video_timer()
        else:
            self.stop_random_video_timer()

    def on_stroke_toggle(self):
        """Handle stroke-based toggle - COMPLETE VERSION"""
        if self.stroke_enabled.get():
            if self.random_enabled.get():
                self.random_enabled.set(False)  # Disable time mode
                self.stop_random_video_timer()
            self.stroke_count = 0  # Reset counter
            self.last_position = 50.0  # Reset position tracking
            # Update display if it exists
            if hasattr(self, 'video_status_label'):
                self.video_status_label.config(
                    text=f"🎬 Stroke mode: 0/{self.stroke_interval_entry.get()} strokes",
                    fg='#66ff66'
                )
        else:
            if hasattr(self, 'video_status_label'):
                self.video_status_label.config(
                    text="🎹 Stroke switching disabled", 
                    fg='#888888'
                )

    def start_random_video_timer(self):
        """Start time-based random video switching"""
        # Implementation for time-based switching
        pass

    def stop_random_video_timer(self):
        """Stop time-based random video switching"""
        # Implementation to stop timer
        pass
                    
    def open_video(self):
        """Open video file dialog"""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Video Clip", 
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.webm"), ("All files", "*.*")]
       )
        if file_path:
            self.video_loading = True  
            self.video_visualizer.load_video(file_path)
            self.audio_manager.play('video_loaded')
            self.video_status_label.config(text=f"🎹 Loading: {os.path.basename(file_path)}", fg='#ff99cc')
            self.save_video_btn.config(state='normal')  # Enable save button

    def on_video_direction_change(self, event=None):
        """Handle video direction change"""
        self.video_visualizer.direction = self.direction_var.get()
        self.video_visualizer.on_direction_change()

    def on_test_position_change(self, value):
        """Handle test slider change"""
        self.video_visualizer.on_test_position_change(value)

    def start_video_position_monitoring(self):
        """Start monitoring position data for video"""
        def monitor_loop():
            while True:
                try:
                    if os.path.exists(self.video_visualizer.status_file):
                        with open(self.video_visualizer.status_file, 'r') as f:
                            content = f.read().strip()
                            if content:
                                data = json.loads(content)
                                position = data.get('position', 50)
                                self.video_visualizer.update_position(position)
                    time.sleep(0.003)
                except:
                    time.sleep(0.1)
    
        threading.Thread(target=monitor_loop, daemon=True).start()    
            
    def auto_apply_config(self):
        """Auto-apply config if everything is detected"""
        try:
            if self.joystick_controller.device:
                print("🔧 Auto-applying saved joystick configuration...")
                self.apply_joystick_config()  # ✅ FIXED - moved inside the if block
            else:
                print("⚠️ No joystick device selected for auto-apply")
        except Exception as e:
            print(f"⚠️ Auto-apply failed: {e}")    
    
    def start_axis_detection(self, axis_type):
        """Start axis detection"""
        if not self.joystick_controller.device:
            messagebox.showerror("Error", "Please select a joystick device first!")
            return
        
        if self.detecting_input:
            print("⚠️ Detection already running!")
            return
        
        self.detecting_input = True
        self.detection_type = f'axis_{axis_type}'
        
        label = getattr(self, f"detect_{axis_type}_label")
        button = getattr(self, f"detect_{axis_type}_btn")
        
        button.config(text="DETECTING...", bg='#ff8844', state='disabled')
        label.config(text="MOVE AXIS NOW!", fg='#ff99cc')
        
        threading.Thread(target=self._detect_axis_input, args=(axis_type,), daemon=True).start()
        self.detection_timeout = self.root.after(5000, self._detection_timeout)
    
    def start_button_detection(self, button_type):
        """Start button detection"""
        if not self.joystick_controller.device:
            messagebox.showerror("Error", "Please select a joystick device first!")
            return
        
        if self.detecting_input:
            print("⚠️ Detection already running!")
            return
        
        self.detecting_input = True
        self.detection_type = button_type
        
        label = getattr(self, f"detect_{button_type}_label")
        button = getattr(self, f"detect_{button_type}_btn")
        
        button.config(text="DETECTING...", bg='#ff8844', state='disabled')
        label.config(text="PRESS BUTTON NOW!", fg='#ff99cc')
        
        threading.Thread(target=self._detect_button_input, args=(button_type,), daemon=True).start()
        self.detection_timeout = self.root.after(5000, self._detection_timeout)
    
    def _detect_axis_input(self, axis_type):
        """Detect axis input - IMPROVED VERSION FOR T16000M"""
        print(f"🎮 Detecting {axis_type} axis...")
    
        device = self.joystick_controller.device
        if not device:
            self.detecting_input = False
            return
    
        # IMPROVED: Get more stable baseline with multiple samples
        pygame.event.pump()
        time.sleep(0.2)  # Longer settle time
    
        # Get baseline with multiple samples for stability
        baseline_values = []
        for i in range(device.get_numaxes()):
            samples = []
            for _ in range(5):  # Take 5 samples
                pygame.event.pump()
                samples.append(device.get_axis(i))
                time.sleep(0.02)
            baseline_values.append(sum(samples) / len(samples))  # Average
            print(f"Baseline Axis {i}: {baseline_values[i]:.3f}")
    
        print(f"✅ MOVE {axis_type} axis NOW! (Try your stick or throttle)")
    
        detected_axis = -1
        max_change = 0.0
    
        # LONGER detection loop with better thresholds
        for sample in range(100):  # 10 seconds instead of 5
            pygame.event.pump()
        
            for i in range(device.get_numaxes()):
                current_value = device.get_axis(i)
                change = abs(current_value - baseline_values[i])
            
                # Show ANY movement above deadzone
                if change > 0.02:  # Lower threshold to see small movements
                    print(f"Axis {i}: {current_value:.3f} (Δ{change:.3f})")
            
                if change > max_change:
                    max_change = change
                    detected_axis = i
        
            # IMPROVED: Stop when we find significant movement
            if max_change > 0.15:  # Higher threshold for final detection
                print(f"🎯 Strong movement detected on Axis {detected_axis}!")
                break
        
            time.sleep(0.1)
        
            if not self.detecting_input:
                break
    
        print(f"Final Result: Axis {detected_axis}, Max Change: {max_change:.3f}")
    
        # Update UI with better success criteria
        if detected_axis >= 0 and max_change > 0.1:  # Lower threshold for acceptance
            setattr(self, f"detected_{axis_type}_axis", detected_axis)
            def success():
                label = getattr(self, f"detect_{axis_type}_label")
                button = getattr(self, f"detect_{axis_type}_btn")
                label.config(text=f"Axis {detected_axis}", fg='#66ff66')
                button.config(text="DETECT AXIS", bg='#004400', state='normal')
            self.root.after(0, success)
            print(f"✅ SUCCESS: {axis_type} = Axis {detected_axis}")
        else:
            def failed():
                label = getattr(self, f"detect_{axis_type}_label")
                button = getattr(self, f"detect_{axis_type}_btn")
                label.config(text="Try Again", fg='#cc3366')
                button.config(text="DETECT AXIS", bg='#004400', state='normal')
            self.root.after(0, failed)
            print(f"❌ FAILED - try moving the axis more")
    
        self.detecting_input = False
        if self.detection_timeout:
            self.root.after_cancel(self.detection_timeout)
    
    def _detect_button_input(self, button_type):
        """Detect button input - SIMPLE VERSION"""
        print(f"🎮 Detecting {button_type} button...")
        
        device = self.joystick_controller.device
        if not device:
            self.detecting_input = False
            return
        
        # Get baseline
        pygame.event.pump()
        time.sleep(0.1)
        
        baseline = []
        for i in range(device.get_numbuttons()):
            baseline.append(device.get_button(i))
        
        print(f"✅ PRESS your {button_type} button NOW!")
        
        best_button = -1
        
        # Watch for 4 seconds
        for check in range(40):
            pygame.event.pump()
            
            for i in range(device.get_numbuttons()):
                current = device.get_button(i)
                
                # Button was pressed (was off, now on)
                if not baseline[i] and current:
                    best_button = i
                    print(f"🎯 Found button {i}!")
                    break
            
            if best_button >= 0:
                break
                
            time.sleep(0.1)
            if not self.detecting_input:
                break
        
        # Show result
        if best_button >= 0:
            setattr(self, f"detected_{button_type}_button", best_button)
            def success():
                label = getattr(self, f"detect_{button_type}_label")
                button = getattr(self, f"detect_{button_type}_btn")
                label.config(text=f"Button {best_button}", fg='#66ff66')
                button.config(text="DETECT", bg='#4444ff', state='normal')
            self.root.after(0, success)
            print(f"✅ {button_type} = Button {best_button}")
        else:
            def failed():
                label = getattr(self, f"detect_{button_type}_label")
                button = getattr(self, f"detect_{button_type}_btn")
                label.config(text="Try again", fg='#cc3366')
                button.config(text="DETECT", bg='#4444ff', state='normal')
            self.root.after(0, failed)
            print(f"❌ Failed - press the button!")
        
        self.detecting_input = False
        if self.detection_timeout:
            self.root.after_cancel(self.detection_timeout)
    
    def _detection_timeout(self):
        """Handle detection timeout"""
        print("⏰ Timeout!")
        self.detecting_input = False
        
        # Reset any stuck buttons
        for control in ['speed', 'manual', 'manual_btn', 'skip', 'play_pause']:
            try:
                button = getattr(self, f"detect_{control}_btn", None)
                if button and button['state'] == 'disabled':
                    if 'axis' in control:
                        button.config(text="DETECT", bg='#004400', state='normal')
                    else:
                        button.config(text="DETECT", bg='#4444ff', state='normal')
            except:
                pass
        
        self.detection_timeout = None
    
    def refresh_joystick_devices(self):
        """Refresh joystick devices"""
        devices = self.joystick_controller.refresh_devices()
        device_names = [f"{d['name']} (Axes: {d['axes']}, Buttons: {d['buttons']})" for d in devices]
        
        self.device_combo['values'] = device_names
        if device_names:
            self.device_combo.set(device_names[0])
            self.on_device_selected(None)
            self.joystick_status_label.config(
                text="🎮 Joystick: Available (Configure in Joystick tab)",
                fg='#ff99cc'
            )
        else:
            self.device_combo.set("")
            self.joystick_status_label.config(
                text="🎮 Joystick: No devices found",
                fg='#cc3366'
            )
    
    def on_device_selected(self, event):
        """Handle device selection"""
        if not self.device_combo.get():
            return
            
        device_index = self.device_combo.current()
        if self.joystick_controller.select_device(device_index):
            device_info = self.joystick_controller.available_devices[device_index]
            self.joystick_status_label.config(
                text=f"🎮 Joystick: {device_info['name']} (Ready to configure)",
                fg='#66ff66'
            )
    
    def apply_joystick_config(self):
        """Apply enhanced joystick configuration with video navigation"""
        try:
            # Validate all inputs detected - ADD NEW VIDEO BUTTONS
            required_inputs = [
                ("speed axis", self.detected_speed_axis),
                ("manual axis", self.detected_manual_axis),
                ("manual button", self.detected_manual_btn_button),
                ("skip button", self.detected_skip_button),
                ("play/pause button", self.detected_play_pause_button),
                ("next video button", self.detected_next_video_button),    # 🔧 NEW
                ("previous video button", self.detected_prev_video_button) # 🔧 NEW
            ]
    
            for name, value in required_inputs:
                if value < 0:
                    raise ValueError(f"Please detect the {name} input first")
    
            # Get enhanced settings safely
            speed_invert = self.speed_invert_var.get() if hasattr(self, 'speed_invert_var') else False
            manual_invert = self.manual_invert_var.get() if hasattr(self, 'manual_invert_var') else False
    
            speed_mode = self.speed_mode_combo.get() if hasattr(self, 'speed_mode_combo') else "full_range"
            manual_mode = self.manual_mode_combo.get() if hasattr(self, 'manual_mode_combo') else "full_range"
    
            print(f"Applying config: speed_axis={self.detected_speed_axis}, manual_axis={self.detected_manual_axis}")
            print(f"Video buttons: next={self.detected_next_video_button}, prev={self.detected_prev_video_button}")
            print(f"Options: speed_invert={speed_invert}, manual_invert={manual_invert}")
            print(f"Modes: speed_mode={speed_mode}, manual_mode={manual_mode}")
    
            # Configure with ALL buttons including video navigation
            self.joystick_controller.configure(
                self.detected_speed_axis,
                self.detected_manual_axis,
                self.detected_manual_btn_button,
                self.detected_skip_button,
                self.detected_play_pause_button,
                self.detected_next_video_button,     # 🔧 NEW
                self.detected_prev_video_button,     # 🔧 NEW
                speed_invert,
                manual_invert,
                speed_mode,
                manual_mode
            )
        
            # Set callbacks
            self.joystick_controller.set_callbacks(
                speed_callback=self.on_joystick_speed_change,
                manual_callback=self.on_manual_override,
                skip_callback=self.on_skip_pattern,
                play_pause_callback=self.on_play_pause_button,
                next_video_callback=self.on_joystick_next_video,    # 🔧 NEW
                prev_video_callback=self.on_joystick_prev_video     # 🔧 NEW
            )
    
            # Start monitoring
            if self.joystick_controller.start():
                if hasattr(self, 'joystick_status_label'):
                    self.joystick_status_label.config(
                        text="🎮 Joystick: ACTIVE with video navigation",
                        fg='#66ff66'
                    )
        
                # Save the config AFTER successful application
                self.save_joystick_config()
        
                # Start live monitoring display
                self.update_joystick_display()
            else:
                raise ValueError("Failed to start joystick monitoring")
        
        except ValueError as e:
            messagebox.showerror("Configuration Error", str(e))
            print(f"❌ Configuration error: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply configuration: {e}")
            print(f"❌ Apply config error: {e}")
            import traceback
            traceback.print_exc()

    def save_joystick_config(self):
        """Save joystick config including video buttons"""
        try:
            config = {
                "device_name": self.device_combo.get() if hasattr(self, 'device_combo') and self.device_combo else "",
"device_index": self.device_combo.current() if hasattr(self, 'device_combo') and self.device_combo.get() else -1,
                "device_index": self.device_combo.current() if hasattr(self, 'device_combo') and self.device_combo.get() else -1,
                "speed_axis": getattr(self, 'detected_speed_axis', -1),
                "manual_axis": getattr(self, 'detected_manual_axis', -1),
                "manual_btn": getattr(self, 'detected_manual_btn_button', -1),
                "skip_btn": getattr(self, 'detected_skip_button', -1),
                "play_pause_btn": getattr(self, 'detected_play_pause_button', -1),
                "next_video_btn": getattr(self, 'detected_next_video_button', -1),     # ADD THIS
                "prev_video_btn": getattr(self, 'detected_prev_video_button', -1), 
                "speed_invert": self.speed_invert_var.get() if hasattr(self, 'speed_invert_var') else False,
                "manual_invert": self.manual_invert_var.get() if hasattr(self, 'manual_invert_var') else False,
                "speed_mode": self.speed_mode_combo.get() if hasattr(self, 'speed_mode_combo') else "full_range",
                "manual_mode": self.manual_mode_combo.get() if hasattr(self, 'manual_mode_combo') else "full_range"
            }

            print(f"💾 Saving config with video buttons: {config}")

            # Atomic write to prevent corruption
            temp_file = "joystick_config_temp.json"
            with open(temp_file, "w") as f:
                json.dump(config, f, indent=2)
    
            # Replace the original file
            if os.path.exists("joystick_config.json"):
                os.remove("joystick_config.json")
            os.rename(temp_file, "joystick_config.json")
    
            print("✅ Joystick config with video buttons saved successfully")
            return True

        except Exception as e:
            print(f"❌ Error saving joystick config: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_joystick_display(self):
        """Update live joystick display with video buttons"""
        if self.joystick_controller.running and self.joystick_controller.device:
            try:
                # Get axis values
                speed_value = 0.0
                manual_value = 0.0
            
                if (self.detected_speed_axis >= 0 and 
                    self.detected_speed_axis < self.joystick_controller.device.get_numaxes()):
                    speed_value = self.joystick_controller.device.get_axis(self.detected_speed_axis)
                
                if (self.detected_manual_axis >= 0 and 
                    self.detected_manual_axis < self.joystick_controller.device.get_numaxes()):
                    manual_value = self.joystick_controller.device.get_axis(self.detected_manual_axis)
            
                self.axis_value_label.config(
                    text=f"Speed Axis: {speed_value:+.3f} | Manual Axis: {manual_value:+.3f}"
                )
            
                # Get ALL button states including video buttons
                manual_state = "ON" if (self.detected_manual_btn_button >= 0 and 
                                      self.joystick_controller.device.get_button(self.detected_manual_btn_button)) else "OFF"
                skip_state = "ON" if (self.detected_skip_button >= 0 and 
                                    self.joystick_controller.device.get_button(self.detected_skip_button)) else "OFF"
                play_pause_state = "ON" if (self.detected_play_pause_button >= 0 and 
                                          self.joystick_controller.device.get_button(self.detected_play_pause_button)) else "OFF"
                # 🔧 NEW: Video button states
                next_video_state = "ON" if (self.detected_next_video_button >= 0 and 
                                          self.joystick_controller.device.get_button(self.detected_next_video_button)) else "OFF"
                prev_video_state = "ON" if (self.detected_prev_video_button >= 0 and 
                                          self.joystick_controller.device.get_button(self.detected_prev_video_button)) else "OFF"
            
                self.button_states_label.config(
                    text=f"Buttons: Manual:{manual_state} Skip:{skip_state} Play/Pause:{play_pause_state} NextVid:{next_video_state} PrevVid:{prev_video_state}"
                )
            
            except Exception as e:
                pass
    
        if self.joystick_controller.running:
            self.root.after(100, self.update_joystick_display)
            
    def on_connection_change(self, connected: bool, device_found: bool = False):
        """Handle connection status changes"""
        def update_gui():
            if connected and device_found:
                self.connection_label.config(text="● Device: Connected & Ready", fg='#66ff66')
                self.status_label.config(text="Ready for seamless streaming", fg='#66ff66')
                self.play_button.config(state='normal')
                self.audio_manager.play('device_connect')
                
            elif connected and not device_found:
                self.connection_label.config(text="● Server Connected, Scanning...", fg='#ff99cc')
                self.status_label.config(text="Server connected, waiting for device...", fg='#ff99cc')
                self.play_button.config(state='disabled')
                self.audio_manager.play('device_scanning')
                
            else:
                self.audio_manager.play('device_disconnect')
                self.connection_label.config(text="● Device: Disconnected", fg='#cc3366')
                self.status_label.config(text="Not connected to server", fg='#cc3366')
                self.play_button.config(state='disabled')
                if self.running:
                    self.stop_playback()
                
        self.root.after(0, update_gui)
    
    
    def on_speed_change(self, value):
        """Handle manual speed slider changes - FIXED STARTUP AUDIO"""
        self.arousal = float(value)
        self.pattern_sequencer.base_speed = self.arousal
        # Show it's manual control, not joystick
        self.speed_display_label.config(text=f"Manual Speed: {self.arousal:.2f}x")
    
        # 🔧 FIXED: Only play sound if startup is complete AND this is a real user interaction
        if (hasattr(self, '_startup_complete') and 
            self._startup_complete and 
            hasattr(self, '_ui_ready') and 
            self._ui_ready):
            self.audio_manager.play('speed_change_manual')
    
    def on_joystick_speed_change(self, new_speed, raw_axis):
        """Handle joystick speed changes - FIXED STARTUP AUDIO"""
        self.arousal = new_speed
        self.pattern_sequencer.base_speed = new_speed

        self.speed_display_label.config(
            text=f"Joystick Speed: {new_speed:.2f}x (Raw: {raw_axis:+.2f})"
        )

        # 🔧 FIXED: Only play sound after UI is fully loaded AND startup complete
        if (hasattr(self, '_startup_complete') and 
            self._startup_complete and 
            hasattr(self, '_ui_ready') and 
            self._ui_ready):
            self.audio_manager.play('speed_change_joystick')
    
    
    def on_skip_pattern(self):
        """Handle skip pattern"""
        self.pattern_sequencer.skip_to_next_pattern()
        self.audio_manager.play('pattern_skip')
    
    def on_play_pause_button(self):
        """Handle play/pause button"""
        self.toggle_playback()
    
    def stop_buildup_mode(self):
        """Stop build-up mode"""
        self.pattern_sequencer.stop_buildup_mode()
        self.audio_manager.play('buildup_stop')
        
        self.buildup_start_button.config(state='normal')
        self.buildup_stop_button.config(state='disabled')
        self.buildup_status_label.config(text="Build-up: Inactive", fg='#888888')
    
    def update_buildup_status(self):
        """Update build-up status"""
        if self.pattern_sequencer.buildup_mode and self.pattern_sequencer.buildup_start_time:
            elapsed = time.time() - self.pattern_sequencer.buildup_start_time
            remaining = max(0, self.pattern_sequencer.buildup_duration - elapsed)
            
            current_speed = self.pattern_sequencer.get_current_speed(self.arousal)
            
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            
            self.buildup_status_label.config(
                text=f"Cycle {self.pattern_sequencer.current_buildup_cycle + 1}/{self.pattern_sequencer.buildup_cycles} | Speed: {current_speed:.2f}x | Time: {minutes:02d}:{seconds:02d}",
                fg='#66ff66'
            )
            
            if self.pattern_sequencer.buildup_mode:
                self.root.after(1000, self.update_buildup_status)
            else:
                self.stop_buildup_mode()
                self.pattern_sequencer.play_climax_patterns()
        else:
            self.buildup_status_label.config(text="Build-up: Inactive", fg='#888888')
    
    # Playback control
    def toggle_playback(self):
        """Toggle playback"""
        try:
            if self.running:
                self.emergency_stop()
            else:
                self.start_playback()
        except Exception as e:
            print(f"Toggle playback error: {e}")
    
    def start_playback(self):
        """Start playback"""
        try:
            if not hasattr(self.device_client, 'connected') or not self.device_client.connected:
                messagebox.showerror("Error", "Device not connected!")
                return
                
            if not hasattr(self.device_client, 'device_connected') or not self.device_client.device_connected:
                messagebox.showerror("Error", "Device not connected!")
                return
                
            if not self.pattern_sequencer.pattern_database:
                messagebox.showerror("Error", "No patterns loaded!")
                return
                
            self.running = True
            self.audio_manager.play('start_playback')
            self.play_button.config(text="♦ EMERGENCY STOP ♦", bg='#440000')
            
            # Start streaming thread
            threading.Thread(target=self.seamless_streaming_loop, daemon=True).start()
            
            print("🌊 SEAMLESS streaming started!")
            
        except Exception as e:
            print(f"Start playback error: {e}")
            messagebox.showerror("Error", f"Failed to start: {e}")
    
    def stop_playback(self):
        """Stop playback"""
        self.running = False
        self.play_button.config(text="♠ AWAKEN ♠", bg='#004400')
        self.status_label.config(text="Playback stopped")
        
        # Reset the stream
        self.pattern_sequencer.motion_stream.clear()
    
    def emergency_stop(self):
        """Emergency stop"""
        self.running = False
        self.audio_manager.play('emergency_stop')
        self.audio_manager.play('stop_playback')
        self.play_button.config(text="♠ AWAKEN ♠", bg='#004400')
        self.status_label.config(text="Emergency stop - returning to home...")
        
        # Reset everything
        self.pattern_sequencer.motion_stream.clear()
        self.pattern_sequencer.manual_override_active = False
        self.manual_status_label.config(
            text="♦ Manual Override: Inactive",
            fg='#888888'
        )
        
        def smooth_return():
            try:
                # Smooth return to home over 2 seconds
                steps = 8
                step_duration = 250
                
                for i in range(steps):
                    progress = (i + 1) / steps
                    eased_progress = 1 - (1 - progress) ** 3
                    intermediate_pos = (1 - eased_progress) * 50
                    
                    self.device_client.send_position_command(intermediate_pos / 100.0, step_duration)
                    time.sleep(step_duration / 1000.0)
                
                self.status_label.config(text="Safely returned to home")
                
            except Exception as e:
                print(f"Emergency stop error: {e}")
        
        threading.Thread(target=smooth_return, daemon=True).start()

    def seamless_streaming_loop(self):
        """SEAMLESS streaming loop - ZERO PAUSES WITH WORKING SPEED"""
        print("🌊 Starting ZERO-PAUSE streaming loop...")
        
        while self.running:
            try:
                loop_start = time.time()
                
                # MANUAL OVERRIDE: Ultra-responsive mode
                if self.pattern_sequencer.manual_override_active:
                    manual_pos = self.joystick_controller.get_manual_position()
                    position = int(manual_pos * 100)
                    self.pattern_sequencer.update_manual_position(manual_pos)
                    
                    # Send directly with minimal delay
                    device_position = position / 100.0
                    self.device_client.send_position_command(device_position, 50)
                    self.write_position_status(position)
                    self.write_position_status(position)
                    if hasattr(self, 'video_visualizer'):
                        self.video_visualizer.update_position(position)
                        self.video_visualizer.current_position = position
                    
                    # Update display
                    self.root.after(0, lambda: self.pattern_display.config(
                        text=f"Stream: MANUAL | Pos: {position} | Mode: Manual"
                    ))
                    
                    time.sleep(0.008)  # ~125Hz
                    continue
                
                # PATTERN MODE: ZERO GAPS WITH PROPER SPEED
                # Pass CURRENT arousal speed to get_next_motion_command
                result = self.pattern_sequencer.get_next_motion_command(self.arousal)
                
                if result[0] is None:
                    time.sleep(0.005)  # Minimal wait
                    continue
                
                position, duration, action_type = result
                
                # Get current speed (includes build-up and joystick)
                current_speed = self.pattern_sequencer.get_current_speed(self.arousal)
                
                # Send command IMMEDIATELY - NO WAITING
                device_position = position / 100.0
                current_speed = self.pattern_sequencer.get_current_speed(self.arousal)
                final_duration = int(duration / current_speed)
                final_duration = max(50, min(500, final_duration))
                self.device_client.send_position_command(device_position, final_duration)
                self.write_position_status(position)
                if hasattr(self, 'video_visualizer') and not self.test_mode_var.get():
                    self.video_visualizer.target_position = position
               
                # Update display with ACTUAL speed
                mode_text = "Pattern"
                speed_text = f"{current_speed:.2f}x"

                if self.pattern_sequencer.buildup_mode:
                    speed_text += " (Build-up)"

                # ADD THIS LINE FOR CHAOS MODE
                if self.pattern_sequencer.chaos_mode:
                    speed_text += " (CHAOS)"
                
                # FIXED: Ultra-precise timing - NO GAPS
                target_sleep = duration / 1000.0
                
                # Account for actual loop execution time
                loop_time = time.time() - loop_start
                adjusted_sleep = max(0.003, target_sleep - loop_time)  # Minimal floor
                
                time.sleep(max(0.001, adjusted_sleep))
                
            except Exception as e:
                print(f"Streaming error: {e}")
                time.sleep(0.005)  # Quick recovery
                self.audio_manager.play('error_playback')

    def write_position_status(self, position=None):
        if hasattr(self, 'stroke_enabled'):
            print(f"Stroke enabled: {self.stroke_enabled.get()}, Position: {position}")
        current_time = time.time()
        if current_time - self.last_json_write_time < self.json_write_interval:
            return
        self.last_json_write_time = current_time

        try:
            if position is None:
                if self.pattern_sequencer.manual_override_active:
                    current_position = self.pattern_sequencer.manual_return_position * 100
                else:
                    current_position = 50
            else:
                current_position = position

            # FIXED: Stroke detection for video switching
            if (hasattr(self, 'stroke_enabled') and 
                hasattr(self, 'stroke_interval_entry') and 
                self.stroke_enabled.get() and 
                position is not None):
                self.detect_stroke(position)

            status_data = {
                'manual_active': self.pattern_sequencer.manual_override_active,
                'position': current_position,
                'timestamp': time.time(),
                'running': self.running,
                'mode': 'manual' if self.pattern_sequencer.manual_override_active else 'pattern',
                'buildup_active': getattr(self.pattern_sequencer, 'buildup_mode', False),
                'current_speed': self.arousal,
                'joystick_speed_multiplier': self.joystick_controller.get_current_speed_multiplier() if self.joystick_controller else 1.0
            }
    
            # Write atomically
            temp_file = 'manual_position_temp.json'
            with open(temp_file, 'w') as f:
                json.dump(status_data, f)

            if os.path.exists('manual_position.json'):
                os.remove('manual_position.json')
            os.rename(temp_file, 'manual_position.json')

        except Exception as e:
            pass
        
    def detect_stroke(self, current_position):
        """Simple stroke detection that actually works"""
        try:
            position_change = current_position - self.last_position
        
            # Only count significant movements
            if abs(position_change) > 20:  # Lowered threshold
                current_direction = "up" if position_change > 0 else "down"
            
                # Count stroke on direction change
                if hasattr(self, '_last_direction') and self._last_direction != current_direction:
                    self.stroke_count += 1
                    print(f"🎬 STROKE DETECTED! Count: {self.stroke_count}")
                    self.update_stroke_display()  # Add this line
                
                    try:
                        target_strokes = int(self.stroke_interval_entry.get())
                        if self.stroke_count >= target_strokes:
                            print(f"🎬 SWITCHING VIDEO! ({self.stroke_count}/{target_strokes})")
                            self.switch_to_next_video()
                            self.stroke_count = 0
                    except:
                        pass
            
                self._last_direction = current_direction
        
            self.last_position = current_position
        
        except Exception as e:
            print(f"Stroke detection error: {e}")

    def update_stroke_display(self):
        """Update stroke count display"""
        try:
            target_strokes = int(self.stroke_interval_entry.get())
            if hasattr(self, 'video_status_label'):
                self.video_status_label.config(
                    text=f"🎬 Stroke mode: {self.stroke_count}/{target_strokes} strokes",
                    fg='#66ff66'
                )
        except:
            pass

    def on_trigger_type_change(self, event=None):
        """Update input field based on trigger type selection"""
        trigger_type = self.change_trigger_combo.get()
    
        if "min:sec" in trigger_type:
            # Time-based: 30-second increments, MM:SS format
            self.change_interval_entry.config(state='normal')
            self.change_interval_entry.increment = 30
            self.change_interval_entry.min_value = 30
            self.change_interval_entry.max_value = 600
            self.change_interval_entry.delete(0, tk.END)
            self.change_interval_entry.insert(0, "2:00")
        
        elif "strokes" in trigger_type:
            # Stroke-based: 1-stroke increments, plain numbers
            self.change_interval_entry.config(state='normal')
            self.change_interval_entry.increment = 1
            self.change_interval_entry.min_value = 5
            self.change_interval_entry.max_value = 100
            self.change_interval_entry.delete(0, tk.END)
            self.change_interval_entry.insert(0, "10")
        
        elif "25%" in trigger_type:
            # Progress-based: disable input (fixed quarters)
            self.change_interval_entry.config(state='disabled')
            self.change_interval_entry.delete(0, tk.END)
            self.change_interval_entry.insert(0, "25%")
        
        elif "patterns" in trigger_type:
            # Pattern-based: 1-pattern increments
            self.change_interval_entry.config(state='normal')
            self.change_interval_entry.increment = 1
            self.change_interval_entry.min_value = 1
            self.change_interval_entry.max_value = 20
            self.change_interval_entry.delete(0, tk.END)
            self.change_interval_entry.insert(0, "3")        
        
    def switch_to_next_video(self):
        """Switch to next video in gallery - IMPROVED VERSION"""
        try:
            if not self.video_gallery.videos:
                return False
            
            # Try to go to next video
            if self.video_gallery.next_video():
                self.load_gallery_video()
                self.update_gallery_display()
                return True
            else:
                # Loop back to first video
                self.video_gallery.current_index = 0
                self.load_gallery_video()
                self.update_gallery_display()
                return True
            
        except Exception as e:
            return False           
            

    def save_current_video(self):
        """Auto-save current video to gallery without popup"""
        if not hasattr(self.video_visualizer, 'video_path') or not self.video_visualizer.video_path:
            messagebox.showerror("Error", "No video loaded!")
            return

        try:
            # Get current settings
            direction = self.direction_var.get()
            invert = self.video_invert_var.get()
        
            # Auto-generate name from filename
            original_filename = os.path.basename(self.video_visualizer.video_path)
            name_without_ext = os.path.splitext(original_filename)[0]
        
            # Create a clean name
            clean_name = name_without_ext.replace('_', ' ').replace('-', ' ')
        
            # Add direction/invert info to name if needed
            name_parts = [clean_name]
            if direction == "100_to_0":
                name_parts.append("(Reverse)")
            if invert:
                name_parts.append("(Inverted)")
        
            final_name = " ".join(name_parts)
            
            # Check if name already exists and add number if needed
            existing_names = [video['name'] for video in self.video_gallery.videos]
            original_final_name = final_name
            counter = 1
        
            while final_name in existing_names:
                final_name = f"{original_final_name} ({counter})"
                counter += 1
        
            print(f"🎬 Auto-saving video as: '{final_name}'")
        
            # Save to gallery
            if self.video_gallery.add_video(self.video_visualizer.video_path, final_name, direction, invert):
                self.audio_manager.play('video_save')
                self.update_gallery_display()
                
                # Show brief success message in status instead of popup
                self.video_status_label.config(
                    text=f"✅ Saved: {final_name[:30]}{'...' if len(final_name) > 30 else ''}",
                    fg='#66ff66'
                )
            
                # Reset status after 3 seconds
                self.root.after(3000, lambda: self.video_status_label.config(
                    text="🎹 Video saved to gallery", 
                    fg='#888888'
                ))
            
                print(f"✅ Video auto-saved successfully: {final_name}")
            else:
                messagebox.showerror("Error", "Failed to save video!")
            
        except Exception as e:
            print(f"❌ Auto-save error: {e}")
            messagebox.showerror("Error", f"Failed to auto-save video: {e}")
    
            # Get current settings
            direction = self.direction_var.get()
            invert = self.video_invert_var.get()
    
            # Ask for video name
            name = tk.simpledialog.askstring("Save Video", "Enter name for this video:")
            if not name:
                return
    
            # Save to gallery
            if self.video_gallery.add_video(self.video_visualizer.video_path, name, direction, invert):
               self.audio_manager.play('video_save')
               self.update_gallery_display()
               messagebox.showinfo("Success", f"Video '{name}' saved to gallery!")
            else:
                messagebox.showerror("Error", "Failed to save video!")

    def delete_current_video(self):
       """Delete current video from gallery"""
       current_video = self.video_gallery.get_current_video()
       if not current_video:
            messagebox.showerror("Error", "No video selected!")
            return
    
        # Confirm deletion
       result = messagebox.askyesno("Delete Video", f"Delete '{current_video['name']}'?")
       if result:
            if self.video_gallery.delete_video(current_video['id']):
                self.update_gallery_display()
                messagebox.showinfo("Deleted", "Video deleted!")
            else:
                messagebox.showerror("Error", "Failed to delete video!")

    def load_next_video(self):
        """Load next video - FIXED VERSION"""
        if not self.video_gallery.videos:
            print("❌ No videos in gallery")
            return

        total_videos = len(self.video_gallery.videos)
        print(f"📊 Total videos: {total_videos}, Current index: {self.video_gallery.current_index}")
    
        # Simple increment with wrap-around
        self.video_gallery.current_index = (self.video_gallery.current_index + 1) % total_videos
    
        # Calculate which page this video is on
        self.video_gallery.gallery_page = self.video_gallery.current_index // 5

        print(f"➡️ NEXT: Going to video {self.video_gallery.current_index} on page {self.video_gallery.gallery_page}")

        # Load and display
        self.load_gallery_video()
        self.update_gallery_display()

        # Force save the new position
        self.video_gallery.save_gallery()

    def load_prev_video(self):
        """Load previous video - FIXED VERSION"""
        if not self.video_gallery.videos:
            print("❌ No videos in gallery")
            return

        total_videos = len(self.video_gallery.videos)
        print(f"📊 Total videos: {total_videos}, Current index: {self.video_gallery.current_index}")

        # Simple decrement with wrap-around
        self.video_gallery.current_index = (self.video_gallery.current_index - 1) % total_videos

        # Calculate which page this video is on
        self.video_gallery.gallery_page = self.video_gallery.current_index // 5

        print(f"⬅️ PREV: Going to video {self.video_gallery.current_index} on page {self.video_gallery.gallery_page}")

        # Load and display
        self.load_gallery_video()
        self.update_gallery_display()

        # Force save the new position
        self.video_gallery.save_gallery()
            
    def prev_gallery_page(self):
        """Go to previous gallery page"""
        if self.video_gallery.prev_gallery_page():
            self.update_gallery_display()

    def next_gallery_page(self):
        """Go to next gallery page"""
        if self.video_gallery.next_gallery_page():
            self.update_gallery_display()

    def load_gallery_video(self):
        """Load the currently selected gallery video - FIXED VERSION"""
        current_video = self.video_gallery.get_current_video()
        if not current_video:
            print("❌ No current video to load")
            return
    
        # ✅ FIXED: Remove the video_loading flag entirely - it was causing problems
        print(f"🎬 Loading: {current_video['name']} (Index: {self.video_gallery.current_index})")
    
        # Load video
        self.video_visualizer.load_video(current_video['file_path'])

        # Apply settings
        self.direction_var.set(current_video['direction'])
        self.video_invert_var.set(current_video['invert'])
        self.on_video_direction_change()

        # Update UI
        self.current_video_name.config(
            text=f"{current_video['name']} ({self.video_gallery.current_index + 1}/{len(self.video_gallery.videos)})"
        )

    def update_gallery_display(self):
        """Update gallery display with current video highlighting - FIXED VERSION"""
        visible_videos = self.video_gallery.get_visible_videos()
    
        print(f"🖼️ Updating gallery: Page {self.video_gallery.gallery_page}, Current video {self.video_gallery.current_index}")
    
        # Update thumbnail slots with real images
        for i, thumb in enumerate(self.gallery_thumbnails):
            if i < len(visible_videos):
                video = visible_videos[i]
            
                # Calculate actual video index for this thumbnail
                actual_video_index = (self.video_gallery.gallery_page * 5) + i
                is_current_video = (actual_video_index == self.video_gallery.current_index)
            
                try:
                    # Get thumbnail image
                    thumbnail_pil = self.video_gallery.get_thumbnail_image(video['id'], (350, 250))
                    thumbnail_tk = ImageTk.PhotoImage(thumbnail_pil)
                
                    # Update thumbnail display
                    thumb['label'].config(
                        image=thumbnail_tk, 
                        text="",
                        compound='center'
                    )
                    thumb['label'].image = thumbnail_tk
                
                    # Update name
                    thumb['name'].config(text=video['name'][:15])
                    thumb['video_id'] = video['id']
                
                    # ✅ FIXED: Highlight current video with different colors
                    if is_current_video:
                        thumb['frame'].config(bg='#66ff66', relief='raised', bd=3)  # Green highlight
                        thumb['name'].config(fg='#000000', bg='#66ff66')  # Black text on green
                        print(f"🎯 Highlighted current video: {video['name']} at slot {i}")
                    else:
                        thumb['frame'].config(bg='#554455', relief='raised', bd=2)  # Normal
                        thumb['name'].config(fg='#cccccc', bg='#440044')  # Normal colors
                
                except Exception as e:
                    print(f"⚠️ Error loading thumbnail for {video['name']}: {e}")
                    # Fallback to text display
                    thumb['label'].config(
                        image="",
                        text=f"📹\n{video['name'][:10]}", 
                        fg='#66ff66' if is_current_video else '#cccccc'
                    )
                    thumb['name'].config(text=video['name'][:15])
                    thumb['video_id'] = video['id']
                
                    if is_current_video:
                        thumb['frame'].config(bg='#66ff66', relief='raised', bd=3)
                    else:
                        thumb['frame'].config(bg='#554455', relief='raised', bd=2)
            
            else:
                # Empty slot
                thumb['label'].config(
                    image="",
                    text=f"Slot {i+1}\nEmpty", 
                    fg='#666666'
                )
                thumb['name'].config(text="", fg='#666666', bg='#440044')
                thumb['video_id'] = None
                thumb['frame'].config(bg='#440044', relief='sunken', bd=1)
    
        # Update status and navigation buttons
        total_videos = len(self.video_gallery.videos)
        current_page = self.video_gallery.gallery_page + 1
        total_pages = max(1, (total_videos + 4) // 5)
    
        self.gallery_status.config(
            text=f"Gallery: {total_videos} videos (Page {current_page}/{total_pages}) - Video {self.video_gallery.current_index + 1}"
        )
    
        # Enable/disable navigation buttons
        max_page = (len(self.video_gallery.videos) - 1) // 5 if len(self.video_gallery.videos) > 0 else 0
    
        self.prev_gallery_btn.config(state='normal' if self.video_gallery.gallery_page > 0 else 'disabled')
        self.next_gallery_btn.config(state='normal' if self.video_gallery.gallery_page < max_page else 'disabled')
    
        self.prev_video_btn.config(state='normal' if len(self.video_gallery.videos) > 1 else 'disabled')
        self.next_video_btn.config(state='normal' if len(self.video_gallery.videos) > 1 else 'disabled')
    
        self.delete_video_btn.config(state='normal' if self.video_gallery.get_current_video() else 'disabled')
        
        if hasattr(self.video_visualizer, 'video_path') and self.video_visualizer.video_path:
            self.save_video_btn.config(state='normal')


    def on_thumbnail_click(self, thumbnail_index):
        """Handle clicking on a gallery thumbnail"""
        visible_videos = self.video_gallery.get_visible_videos()
    
        if thumbnail_index < len(visible_videos):
            # Calculate the actual video index
            actual_index = (self.video_gallery.gallery_page * self.video_gallery.videos_per_page) + thumbnail_index
        
            # Set as current video
            self.video_gallery.current_index = actual_index
        
            # Load the video
            self.load_gallery_video()
        
            # Update display
            self.update_gallery_display()
        
            print(f"🎯 Clicked thumbnail {thumbnail_index}, loaded video {actual_index}")
            

    def on_connection_change(self, connected: bool, device_found: bool = False):
        """Handle connection status changes"""
        def update_gui():
            if connected and device_found:
                self.connection_label.config(text="● Device: Connected & Ready", fg='#66ff66')
                self.status_label.config(text="Ready for seamless streaming", fg='#66ff66')
                self.play_button.config(state='normal')
                self.audio_manager.play('device_connect')
            elif connected and not device_found:
                self.connection_label.config(text="● Server Connected, Scanning...", fg='#ff99cc')
                self.status_label.config(text="Server connected, waiting for device...", fg='#ff99cc')
                self.play_button.config(state='disabled')
                self.audio_manager.play('device_scanning')
            else:
                self.audio_manager.play('device_disconnect')
                self.connection_label.config(text="● Device: Disconnected", fg='#cc3366')
                self.status_label.config(text="Not connected to server", fg='#cc3366')
                self.play_button.config(state='disabled')
                if self.running:
                    self.stop_playback()
        self.root.after(0, update_gui)

    def on_joystick_speed_change(self, new_speed, raw_axis):
        """Handle joystick speed changes"""
        self.arousal = new_speed
        self.pattern_sequencer.base_speed = new_speed
        self.speed_display_label.config(
            text=f"Joystick Speed: {new_speed:.2f}x (Raw: {raw_axis:+.2f})"
        )
        

    def on_manual_override(self, active, position):
        """Handle manual override - FIXED: No button bounce"""
        if active:
            # Only play sound and update UI when FIRST activating manual mode
            if not self.pattern_sequencer.manual_override_active:
                self.pattern_sequencer.start_manual_override(position)
                self.audio_manager.play('manual_start')  # "You take control"
                self.manual_status_label.config(
                        text="🎮 Manual Override: ACTIVE",
                fg='#cc3366'
                )
                print("🎮 Manual override STARTED")
            else:
                # Already active, just update position silently
                self.pattern_sequencer.update_manual_position(position)
        else:
            # Only play sound and update UI when ACTUALLY ending manual mode
            if self.pattern_sequencer.manual_override_active:
                self.pattern_sequencer.end_manual_override()
                self.audio_manager.play('manual_stop')  # "I take control"
                self.manual_status_label.config(
                    text="♦ Manual Override: Inactive",
                    fg='#888888'
                )
                print("🎮 Manual override ENDED")
    
        # Always update position status
        self.write_position_status(position * 100 if position is not None else None)

    def on_skip_pattern(self):
        """Handle skip pattern"""
        self.pattern_sequencer.skip_to_next_pattern()
        self.audio_manager.play('pattern_skip')

    def on_play_pause_button(self):
        """Handle play/pause button"""
        self.toggle_playback()        
    # ADD THESE MISSING CALLBACK METHODS:

    def refresh_joystick_devices(self):
        """Refresh joystick devices"""
        devices = self.joystick_controller.refresh_devices()
        device_names = [f"{d['name']} (Axes: {d['axes']}, Buttons: {d['buttons']})" for d in devices]
    
        self.device_combo['values'] = device_names
        if device_names:
            self.device_combo.set(device_names[0])
            self.on_device_selected(None)
            self.joystick_status_label.config(
                text="🎮 Joystick: Available (Configure in Joystick tab)",
                fg='#ff99cc'
            )
        else:
            self.device_combo.set("")
            self.joystick_status_label.config(
                text="🎮 Joystick: No devices found",
                fg='#cc3366'
            )

    def on_device_selected(self, event):
        """Handle device selection"""
        if not self.device_combo.get():
            return
        
        device_index = self.device_combo.current()
        if self.joystick_controller.select_device(device_index):
            device_info = self.joystick_controller.available_devices[device_index]
            self.joystick_status_label.config(
                text=f"🎮 Joystick: {device_info['name']} (Ready to configure)",
                fg='#66ff66'
            )

    def start_buildup_mode(self):
        """Start build-up mode with FIXED speed limits and time parsing"""
        try:
            # RESET all audio tracking flags
            self.pattern_sequencer._buildup_completed = False
            # Clear any existing milestone flags
            for attr in list(vars(self.pattern_sequencer).keys()):
                if attr.startswith('_fired_cycle_'):
                    delattr(self.pattern_sequencer, attr)
                
            time_input = self.buildup_time_entry.get().strip()
    
            # Parse time input - handle both "MM:SS" and plain seconds
            if ":" in time_input:
                parts = time_input.split(":")
                minutes = int(parts[0])
                seconds = int(parts[1]) if len(parts) > 1 else 0
                duration_seconds = minutes * 60 + seconds
            else:
                duration_seconds = int(time_input)

            cycles_input = self.buildup_cycles_entry.get().strip()
            cycles = int(cycles_input) if cycles_input.isdigit() else 1

            max_speed_input = self.buildup_max_speed_entry.get().strip()
            max_speed = float(max_speed_input)

            if duration_seconds < 30 or duration_seconds > 3600:
                raise ValueError("Duration must be between 30 and 3600 seconds")
            if cycles < 1 or cycles > 50:
                raise ValueError("Cycles must be between 1 and 50")
            if max_speed < 0.1 or max_speed > 1.5:  # CHANGED: new limits
                raise ValueError("Max speed must be between 0.1x and 1.5x")

            # Get folder cycling settings
            cycle_folders = self.folder_cycling_var.get()
            trigger_type = self.change_trigger_combo.get()
            interval_value = self.change_interval_entry.get()

            self.pattern_sequencer.start_buildup_mode(duration_seconds, cycles, 0.1, max_speed, 
                                             cycle_folders, trigger_type, interval_value)
            self.audio_manager.play('buildup_start')
    
            self.buildup_start_button.config(state='disabled')
            self.buildup_stop_button.config(state='normal')

            self.update_buildup_status()

        except ValueError as e:
            messagebox.showerror("Error", str(e))
            print(f"❌ Build-up mode error: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start build-up mode: {e}")
            print(f"❌ Build-up mode exception: {e}")
        
    def load_joystick_config_delayed(self):
        """FIXED: Load joystick config after UI is fully ready"""
        try:
            if not os.path.exists("joystick_config.json"):
                print("ℹ️ No joystick config file found")
                return
        
            with open("joystick_config.json", "r") as f:
                config = json.load(f)

            print(f"📋 Loading SAVED config: {config}")

            # Set detected values
            self.detected_speed_axis = config.get("speed_axis", -1)
            self.detected_manual_axis = config.get("manual_axis", -1)
            self.detected_manual_btn_button = config.get("manual_btn", -1)
            self.detected_skip_button = config.get("skip_btn", -1)
            self.detected_play_pause_button = config.get("play_pause_btn", -1)
            self.detected_next_video_button = config.get("next_video_btn", -1)     # ADD THIS
            self.detected_prev_video_button = config.get("prev_video_btn", -1)  

            # FIXED: Update UI labels only if they exist AND have valid values
            self.update_config_ui_labels()
        
            # FIXED: Set enhanced options safely
            self.update_config_ui_options(config)

            # RESTORE SAVED JOYSTICK SELECTION
            saved_device_name = config.get("device_name", "")
            if saved_device_name and hasattr(self, 'device_combo'):
                current_devices = self.device_combo['values']
                for i, device in enumerate(current_devices):
                    if saved_device_name in device:
                        self.device_combo.current(i)
                        self.on_device_selected(None)
                        print(f"✅ Restored joystick: {saved_device_name}")
                        break

            print("✅ Config loaded and UI updated successfully")

            # FIXED: Auto-apply if everything is ready
            self.schedule_auto_apply_if_ready()

        except Exception as e:
            print(f"⚠️ Error loading joystick config: {e}")
            import traceback
            traceback.print_exc()

    def update_config_ui_labels(self):
        """Update UI labels with loaded config values including video buttons"""
        try:
            if hasattr(self, 'detect_speed_label') and self.detected_speed_axis >= 0:
                self.detect_speed_label.config(text=f"Axis {self.detected_speed_axis}", fg='#66ff66')
    
            if hasattr(self, 'detect_manual_label') and self.detected_manual_axis >= 0:
                self.detect_manual_label.config(text=f"Axis {self.detected_manual_axis}", fg='#66ff66')
    
            if hasattr(self, 'detect_manual_btn_label') and self.detected_manual_btn_button >= 0:
                self.detect_manual_btn_label.config(text=f"Button {self.detected_manual_btn_button}", fg='#66ff66')
    
            if hasattr(self, 'detect_skip_label') and self.detected_skip_button >= 0:
                self.detect_skip_label.config(text=f"Button {self.detected_skip_button}", fg='#66ff66')
    
            if hasattr(self, 'detect_play_pause_label') and self.detected_play_pause_button >= 0:
                self.detect_play_pause_label.config(text=f"Button {self.detected_play_pause_button}", fg='#66ff66')
        
            # 🔧 NEW: Update video button labels
            if hasattr(self, 'detect_next_video_label') and self.detected_next_video_button >= 0:
                self.detect_next_video_label.config(text=f"Button {self.detected_next_video_button}", fg='#66ff66')
                print(f"✅ Updated next video button label: {self.detected_next_video_button}")
        
            if hasattr(self, 'detect_prev_video_label') and self.detected_prev_video_button >= 0:
                self.detect_prev_video_label.config(text=f"Button {self.detected_prev_video_button}", fg='#66ff66')
                print(f"✅ Updated prev video button label: {self.detected_prev_video_button}")
        
        except Exception as e:
            print(f"⚠️ Error updating UI labels: {e}")


    def update_config_ui_options(self, config):
        """Update UI options with loaded config values"""
        try:
            # Set enhanced options (check if UI elements exist)
            if hasattr(self, 'speed_invert_var'):
                self.speed_invert_var.set(config.get("speed_invert", False))
                print(f"✅ Set speed invert: {config.get('speed_invert', False)}")
            
            if hasattr(self, 'manual_invert_var'):
                self.manual_invert_var.set(config.get("manual_invert", False))
                print(f"✅ Set manual invert: {config.get('manual_invert', False)}")
            
            if hasattr(self, 'speed_mode_combo'):
                self.speed_mode_combo.set(config.get("speed_mode", "full_range"))
                print(f"✅ Set speed mode: {config.get('speed_mode', 'full_range')}")
            
            if hasattr(self, 'manual_mode_combo'):
                self.manual_mode_combo.set(config.get("manual_mode", "full_range"))
                print(f"✅ Set manual mode: {config.get('manual_mode', 'full_range')}")
            
        except Exception as e:
            print(f"⚠️ Error updating UI options: {e}")

    def schedule_auto_apply_if_ready(self):
        """Schedule auto-apply if all conditions are met"""
        try:
            # Check if all controls are detected
            all_detected = all([
                self.detected_speed_axis >= 0, 
                self.detected_manual_axis >= 0, 
                self.detected_manual_btn_button >= 0, 
                self.detected_skip_button >= 0, 
                self.detected_play_pause_button >= 0
            ])
        
            # Check if device combo exists and has values
            device_ready = (hasattr(self, 'device_combo') and 
                           self.device_combo.get() and 
                           hasattr(self, 'joystick_controller'))
        
            print(f"🔍 Auto-apply check: all_detected={all_detected}, device_ready={device_ready}")
        
            if all_detected and device_ready:
                print("🚀 Scheduling auto-apply in 1 second...")
                self.root.after(1000, self.auto_apply_config_safe)
            else:
                print("⏳ Not ready for auto-apply yet")
            
        except Exception as e:
            print(f"⚠️ Error in schedule_auto_apply_if_ready: {e}")

    def auto_apply_config_safe(self):
        """SAFE auto-apply config with error handling"""
        try:
            if (hasattr(self, 'joystick_controller') and 
                hasattr(self, 'device_combo') and 
                self.device_combo.get()):
            
                print("🔧 Auto-applying SAVED joystick configuration...")
                self.apply_joystick_config()
                print("✅ Auto-apply completed successfully!")
            else:
                print("⚠️ Auto-apply skipped - prerequisites not met")
        except Exception as e:
            print(f"⚠️ Auto-apply failed: {e}")
            import traceback
            traceback.print_exc()    
            print(f"💾 Saving config: {config}")
    
            # IMPROVED: Atomic write to prevent corruption
            temp_file = "joystick_config_temp.json"
            with open(temp_file, "w") as f:
                json.dump(config, f, indent=2)
        
            # Replace the original file
            if os.path.exists("joystick_config.json"):
                os.remove("joystick_config.json")
            os.rename(temp_file, "joystick_config.json")
        
            print("✅ Joystick config saved successfully")
            return True
    
        except Exception as e:
            print(f"❌ Error saving joystick config: {e}")
            import traceback
            traceback.print_exc()
            return False            

    def start_random_video_timer(self):
        """Start time-based random video switching - COMPLETE IMPLEMENTATION"""
        try:
            # Cancel existing timer
            self.stop_random_video_timer()
        
            # Get interval from entry
            interval_seconds = int(self.random_interval_entry.get())
            interval_ms = interval_seconds * 1000
        
            # Schedule next switch
            self.random_timer = self.root.after(interval_ms, self._random_video_switch)
        
            # Update status
            if hasattr(self, 'video_status_label'):
                self.video_status_label.config(
                    text=f"⏰ Random mode: next switch in {interval_seconds}s",
                    fg='#66ff66'
                )
            
        except ValueError:
            self.random_enabled.set(False)

    def stop_random_video_timer(self):
        """Stop time-based random video switching"""
        if self.random_timer:
            self.root.after_cancel(self.random_timer)
            self.random_timer = None

    def _random_video_switch(self):
            """Internal method for random video switching"""
            try:
                if self.random_enabled.get() and self.video_gallery.videos:
                    # Switch to random video
                    import random
                    current_index = self.video_gallery.current_index
                    available_indices = [i for i in range(len(self.video_gallery.videos)) if i != current_index]
            
                    if available_indices:
                        new_index = random.choice(available_indices)
                        self.video_gallery.current_index = new_index
                        self.load_gallery_video()
                        self.update_gallery_display()
            
                    # Schedule next switch
                    self.start_random_video_timer()
            
            except Exception as e:
                self.random_enabled.set(False)

    def toggle_voice_audio(self):
        """Toggle voice audio on/off"""
        enabled = self.voice_enabled_var.get()
        self.audio_manager.audio_enabled = enabled
        print(f"🔊 Voice audio: {'ON' if enabled else 'OFF'}")

    def on_voice_change(self, event=None):
        """Handle voice selection change"""
        selected_voice = self.voice_combo.get()
        if self.audio_manager.set_voice(selected_voice):
            print(f"🎭 Voice changed to: {selected_voice}")

    def on_voice_volume_change(self, value):
        """Handle voice volume change"""
        volume = float(value)
        self.audio_manager.set_volume(volume)
        self.voice_vol_label.config(text=f"{int(volume * 100)}%")
        
    def on_audio_device_change(self, event=None):
        """Handle audio device selection change"""
        selected_device = self.audio_device_combo.get()
        if self.audio_device_manager.set_device(selected_device):
            print(f"🔊 Switched to audio device: {selected_device}")
        
            # Reinitialize audio managers with new device
            try:
                self.audio_manager.load_voice_sounds()  # Reload sounds
                self.moans_manager.load_moans_files()   # Reload moans
                messagebox.showinfo("Success", f"Audio output switched to:\n{selected_device}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reinitialize audio: {e}")
        else:
            messagebox.showerror("Error", f"Failed to switch to: {selected_device}")

    def refresh_audio_devices(self):
        """Refresh available audio devices"""
        self.audio_device_manager.scan_audio_devices()
        self.audio_device_combo['values'] = self.audio_device_manager.get_available_devices()
    
        # Keep current selection if still available
        current = self.audio_device_combo.get()
        if current not in self.audio_device_manager.get_available_devices():
            self.audio_device_combo.set("Default System Output")
    
        messagebox.showinfo("Refreshed", f"Found {len(self.audio_device_manager.get_available_devices())} audio devices")

    def calculate_frame_index(self, position):
        # Cache the last calculation
        if hasattr(self, '_last_pos') and abs(position - self._last_pos) < 0.5:
            return self._last_frame_index
    
        # ... existing calculation ...
    
        self._last_pos = position
        self._last_frame_index = frame_index
        return frame_index

    def on_joystick_next_video(self):
        """Handle joystick next video button - IMPROVED VERSION"""
        try:
            if not self.video_gallery.videos:
                print("⚠️ No videos in gallery")
                return
            
            print(f"🎮 NEXT VIDEO: Current index {self.video_gallery.current_index}/{len(self.video_gallery.videos)-1}")
        
            # Simple increment with wrap-around
            old_index = self.video_gallery.current_index
            self.video_gallery.current_index = (self.video_gallery.current_index + 1) % len(self.video_gallery.videos)
        
            # Calculate which page this video should be on
            self.video_gallery.gallery_page = self.video_gallery.current_index // 5
        
            print(f"➡️ NEXT: {old_index} → {self.video_gallery.current_index}, page {self.video_gallery.gallery_page}")
        
            # ✅ FIXED: Always load the video - no blocking flag
            self.load_gallery_video()
        
            # ✅ FIXED: Update display with small delay to ensure proper rendering
            self.root.after(50, self.update_gallery_display)
        
            # Save the new position
            self.video_gallery.save_gallery()
            
            # Play audio feedback
            self.audio_manager.play('gallery_next')
        
        except Exception as e:
            print(f"❌ Joystick next video error: {e}")
            import traceback
            traceback.print_exc()

 

    def connect_device(self):
        """Connect to C# server - SIMPLIFIED VERSION"""
        print("🔌 Attempting connection to C# server...")
    
        def connection_thread():
            try:
                if self.device_client.connect():
                    print("✅ Connected to C# server successfully!")
                    # Connection status will be updated via callback
                else:
                    print("❌ Failed to connect to C# server")
                    self.root.after(0, self.show_connection_error)
            except Exception as e:
                print(f"❌ Connection error: {e}")
                self.root.after(0, self.show_connection_error)
    
        # Start connection in background thread
        threading.Thread(target=connection_thread, daemon=True).start()

    def on_closing(self):
        """Handle app closing - SIMPLIFIED VERSION"""
        print("🛑 Application shutting down...")

        try:
            # Stop playback first
            if hasattr(self, 'running') and self.running:
                print("🛑 Stopping playback...")
                self.emergency_stop()
    
            # Disconnect device client
            if hasattr(self, 'device_client'):
                print("🛑 Disconnecting from C# server...")
                try:
                    self.device_client.disconnect()
                except Exception as e:
                    print(f"⚠️ Error disconnecting: {e}")
    
            # Stop joystick controller
            if hasattr(self, 'joystick_controller'):
                print("🛑 Stopping joystick controller...")
                try:
                    self.joystick_controller.stop()
                except Exception as e:
                    print(f"⚠️ Error stopping joystick: {e}")
    
            # Stop moans manager
            if hasattr(self, 'moans_manager'):
                try:
                    self.moans_manager.stop_background_player()
                except Exception as e:
                    print(f"⚠️ Error stopping moans: {e}")

            # REMOVE any engine manager code
    
        except Exception as e:
            print(f"⚠️ Error during shutdown: {e}")

        # Destroy GUI
        print("🛑 Closing GUI...")
        self.root.destroy()
        print("✅ Shutdown complete")    
                    
    def on_joystick_prev_video(self):
        """Handle joystick previous video button - IMPROVED VERSION"""
        try:
            if not self.video_gallery.videos:
                print("⚠️ No videos in gallery")
                return
            
            print(f"🎮 PREV VIDEO: Current index {self.video_gallery.current_index}/{len(self.video_gallery.videos)-1}")
        
            # Simple decrement with wrap-around
            old_index = self.video_gallery.current_index
            self.video_gallery.current_index = (self.video_gallery.current_index - 1) % len(self.video_gallery.videos)
            
            # Calculate which page this video should be on
            self.video_gallery.gallery_page = self.video_gallery.current_index // 5
        
            print(f"⬅️ PREV: {old_index} → {self.video_gallery.current_index}, page {self.video_gallery.gallery_page}")
        
            # ✅ FIXED: Always load the video - no blocking flag
            self.load_gallery_video()
        
            # ✅ FIXED: Update display with small delay to ensure proper rendering
            self.root.after(50, self.update_gallery_display)
        
            # Save the new position
            self.video_gallery.save_gallery()
        
            # Play audio feedback
            self.audio_manager.play('gallery_prev')
        
        except Exception as e:
            print(f"❌ Joystick prev video error: {e}")
            import traceback
            traceback.print_exc()

    
        print("✅ Shutdown complete")            
        
     
            
    def run(self):
        """Start the application"""
        print("Starting AI Pattern Sequencer.")

        # Set up proper shutdown handling
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Connect to C# server directly - NO ENGINE STARTUP
        print("🔌 Connecting to C# Intiface server...")
        self.connect_device()

        # Start the GUI
        self.root.mainloop()


if __name__ == "__main__":
    try:
        print("Initializing AI Pattern Sequencer...")
        app = AIPatternSequencerGUI()
        app.run()
    except Exception as e:
        print(f"STARTUP ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
