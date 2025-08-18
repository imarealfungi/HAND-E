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

# Import your working device handler
from device_handler import IntifaceClient

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
                    self.videos = json.load(f)
                print(f"📚 Loaded {len(self.videos)} videos from gallery")
                
                # Regenerate missing thumbnails
                self.check_and_regenerate_thumbnails()
            else:
                self.videos = []
        except Exception as e:
            print(f"⚠️ Error loading gallery: {e}")
            self.videos = []
    
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
            with open(gallery_file, 'w') as f:
                json.dump(self.videos, f, indent=2)
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
    """Audio manager with ALL triggers your code can actually detect"""
    
    def __init__(self):
        self.audio_enabled = True
        self.volume = 0.7
        self.base_audio_folder = "processed_voices"
        self.current_voice = "default"
        self.available_voices = []
        
        # Initialize pygame mixer
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            print("🔊 Enhanced audio system initialized")
        except Exception as e:
            print(f"⚠️ Audio init failed: {e}")
            self.audio_enabled = False
        
        # Trigger mappings
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
            'pattern_skip': 'pattern_skip',
            'joystick_config_applied': 'joystick_config_applied',
            'joystick_detection_success': 'joystick_detection_success',
            'joystick_detection_failed': 'joystick_detection_failed',
            'error_playback': 'error_playback',
            'error_joystick': 'error_joystick',
            'patterns_loaded': 'patterns_loaded',
            'app_startup': 'app_startup'
        }
        
        # Cache for loaded sounds
        self.loaded_sounds = {}
        self.scan_available_voices()
        self.load_voice_sounds()
    
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
        
        # Load sounds from each trigger folder
        loaded_count = 0
        for trigger_key, folder_name in self.trigger_mappings.items():
            folder_path = os.path.join(voice_path, folder_name)
            
            if os.path.exists(folder_path):
                wav_files = [f for f in os.listdir(folder_path) if f.endswith('.wav')]
                
                if wav_files:
                    # Load all WAV files for this trigger
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
    
    def play(self, trigger, random_selection=True):
        """Play audio for trigger"""
        if not self.audio_enabled or self.current_voice == "default":
            return
        
        if trigger in self.loaded_sounds:
            try:
                sounds = self.loaded_sounds[trigger]
                if sounds:
                    if random_selection and len(sounds) > 1:
                        sound = random.choice(sounds)
                    else:
                        sound = sounds[0]
                    
                    sound.play()
                    print(f"🔊 Playing: {trigger} ({self.current_voice})")
            except Exception as e:
                print(f"❌ Audio play error: {e}")
        else:
            print(f"🔇 No audio for: {trigger}")
    
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

class JoystickController:
    """Universal joystick controller with invert and half-axis support"""
    
    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        
        self.device = None
        self.running = False
        
        # Configuration
        self.speed_axis = -1
        self.manual_axis = -1
        self.manual_override_button = -1
        self.skip_pattern_button = -1
        self.play_pause_button = -1
        
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
        
        # Button states for edge detection
        self.last_manual_button = False
        self.last_skip_button = False
        self.last_play_pause_button = False
        
        # Callbacks
        self.speed_callback = None
        self.manual_override_callback = None
        self.skip_pattern_callback = None
        self.play_pause_callback = None
        
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
                 axis_invert=False, manual_axis_invert=False, 
                 speed_mode="full_range", manual_mode="full_range"):
        """Configure joystick controls with invert and half-axis"""
        self.speed_axis = speed_axis
        self.manual_axis = manual_axis
        self.manual_override_button = manual_button
        self.skip_pattern_button = skip_button
        self.play_pause_button = play_pause_button
        self.axis_invert = axis_invert
        self.manual_axis_invert = manual_axis_invert
        self.speed_axis_mode = speed_mode
        self.manual_axis_mode = manual_mode
        
        print(f"🎮 Config - Speed: Axis{speed_axis} (invert:{axis_invert}, mode:{speed_mode})")
        print(f"🎮 Config - Manual: Axis{manual_axis} (invert:{manual_axis_invert}, mode:{manual_mode})")
    
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
    
    def set_callbacks(self, speed_callback=None, manual_callback=None, skip_callback=None, play_pause_callback=None):
        """Set callback functions"""
        self.speed_callback = speed_callback
        self.manual_override_callback = manual_callback
        self.skip_pattern_callback = skip_callback
        self.play_pause_callback = play_pause_callback
    
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
        """Monitor joystick input with enhanced axis mapping - UPDATED FOR HALF-AXIS"""
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
        
                # Speed axis control with enhanced mapping - FIXED DEADZONE
                if not self.manual_override_active and self.speed_axis >= 0 and self.speed_axis < self.device.get_numaxes():
                    raw_speed_axis = self.device.get_axis(self.speed_axis)
                
                    # ONLY respond if joystick moved significantly from neutral
                    if abs(raw_speed_axis) > 0.2:  # Bigger deadzone to allow manual slider
                        # Use enhanced mapping
                        mapped_value = self._map_axis_value(raw_speed_axis, self.speed_axis_mode, self.axis_invert)
                    
                        # UPDATED: Better speed calculation for half-axis modes
                        if self.speed_axis_mode in ["half_positive", "half_negative"]:
                            # Half-axis: 0.0 = 0.3x (slow), 1.0 = 2.0x (fast)
                            new_speed = 0.3 + (mapped_value * 1.7)  # 0 → 0.3x, 1 → 2.0x
                        else:
                            # Full range: 0 = 0.3x, 0.5 = 1.0x, 1 = 2.0x
                            if mapped_value <= 0.5:
                               new_speed = 0.3 + (mapped_value * 1.4)  # 0→0.3, 0.5→1.0
                            else:
                                new_speed = 1.0 + ((mapped_value - 0.5) * 2.0)  # 0.5→1.0, 1.0→2.0
                    
                        new_speed = max(0.3, min(2.0, new_speed))
                    
                        if self.speed_callback:
                            self.speed_callback(new_speed, raw_speed_axis)
                    # If joystick at neutral (< 0.2), don't call speed callback = manual slider works
        
                # Manual position axis with enhanced mapping
                if self.manual_override_active and self.manual_axis >= 0 and self.manual_axis < self.device.get_numaxes():
                    raw_manual_axis = self.device.get_axis(self.manual_axis)
            
                    # Use enhanced mapping
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
        
        # Pattern tracking
        self.current_pattern = None
        self.pattern_history = deque(maxlen=5)
        
        # Load patterns
        self.load_patterns()
    
    def load_patterns(self, category_folder="bj"):
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
    
        print(f"✅ Loaded {len(self.pattern_database)} patterns from {category_folder}")

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
        base_duration = 180  # Base 180ms
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
        if self._get_stream_duration() < self.stream_target_duration * 0.9:
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
        base_duration = command.get('duration', 150)
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
    
    def start_buildup_mode(self, duration_seconds, cycles=1, start_speed=0.3, end_speed=2.0):
        """Start build-up mode"""
        self.buildup_mode = True
        self.buildup_duration = duration_seconds
        self.buildup_start_time = time.time()
        self.buildup_start_speed = start_speed
        self.buildup_end_speed = end_speed
        self.buildup_cycles = max(1, cycles)
        self.current_buildup_cycle = 0
        
        print(f"🚀 Build-up: {start_speed}x → {end_speed}x, {cycles} cycles, {duration_seconds}s")
    
    def stop_buildup_mode(self):
        """Stop build-up mode"""
        self.buildup_mode = False
        self.buildup_start_time = None
        print("ℹ️ Build-up stopped")
    
    def get_current_speed(self, manual_speed):
        """Get current speed with build-up and joystick multipliers"""
        base_speed = manual_speed
        
        # Apply build-up if active
        if self.buildup_mode and self.buildup_start_time:
            elapsed = time.time() - self.buildup_start_time
            total_progress = min(elapsed / self.buildup_duration, 1.0)
    
            cycle_duration = self.buildup_duration / self.buildup_cycles
            cycle_elapsed = elapsed % cycle_duration
            cycle_progress = cycle_elapsed / cycle_duration
    
            self.current_buildup_cycle = int(elapsed / cycle_duration)
    
            # CHECK FOR PROGRESS MILESTONES
            if not hasattr(self, '_last_progress_25') and cycle_progress >= 0.25:
                self._last_progress_25 = True
                if hasattr(self, 'audio_manager'):
                    self.audio_manager.play('buildup_progress_25')
    
            if not hasattr(self, '_last_progress_50') and cycle_progress >= 0.50:
                self._last_progress_50 = True
                if hasattr(self, 'audio_manager'):
                    self.audio_manager.play('buildup_progress_50')
    
            if not hasattr(self, '_last_progress_75') and cycle_progress >= 0.75:
                self._last_progress_75 = True
                if hasattr(self, 'audio_manager'):
                    self.audio_manager.play('buildup_progress_75')
    
            # RESET PROGRESS FLAGS ON NEW CYCLE
            if cycle_progress < 0.1:
                self._last_progress_25 = False
                self._last_progress_50 = False
                self._last_progress_75 = False
    
            eased_progress = cycle_progress * cycle_progress
            base_speed = self.buildup_start_speed + (eased_progress * (self.buildup_end_speed - self.buildup_start_speed))
    
            if total_progress >= 1.0:
                if hasattr(self, 'audio_manager'):
                    self.audio_manager.play('buildup_complete')
                self.stop_buildup_mode()
        
        # Apply joystick multiplier
        final_speed = base_speed * self.joystick_speed_multiplier
        return round(max(0.3, min(3.0, final_speed)), 2)


class MouseWheelEntry(tk.Entry):
    """Entry widget with mouse wheel support for time input"""
    
    def __init__(self, parent, increment=30, min_value=30, max_value=3600, **kwargs):
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
        """Handle mouse wheel scrolling"""
        try:
            current_value = int(self.get())
        except ValueError:
            current_value = 60  # Default
        
        # Determine direction
        if event.delta > 0 or event.num == 4:  # Scroll up
            new_value = current_value + self.increment
        else:  # Scroll down
            new_value = current_value - self.increment
        
        # Clamp to limits
        new_value = max(self.min_value, min(self.max_value, new_value))
        
        # Update the entry
        self.delete(0, tk.END)
        self.insert(0, str(new_value))
        
        # Visual feedback
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
    
    def load_video(self, file_path):
        """Load video and create frames"""
        print(f"Loading video: {file_path}")
        
        def load_video_thread():
            try:
                cap = cv2.VideoCapture(file_path)
                if not cap.isOpened():
                    raise Exception("Could not open video file")
                
                self.fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                # Calculate display size (big for left panel)
                max_width, max_height = 800, 600
                aspect_ratio = width / height
                
                if aspect_ratio > 1:
                    self.display_width = min(max_width, width // 2)
                    self.display_height = int(self.display_width / aspect_ratio)
                else:
                    self.display_height = min(max_height, height // 2)
                    self.display_width = int(self.display_height * aspect_ratio)
                
                # Extract and interpolate frames
                original_frames = []
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_resized = cv2.resize(frame_rgb, (self.display_width, self.display_height))
                    original_frames.append(frame_resized)
                
                cap.release()
                
                # Create interpolated frames for smoothness
                new_video_frames = []
                for i in range(len(original_frames)):
                    pil_image = Image.fromarray(original_frames[i])
                    photo = ImageTk.PhotoImage(pil_image)
                    new_video_frames.append(photo)
                    
                    if i < len(original_frames) - 1:
                        current_frame = original_frames[i].astype(np.float32)
                        next_frame = original_frames[i + 1].astype(np.float32)
                        interpolated = (current_frame + next_frame) / 2.0
                        interpolated = interpolated.astype(np.uint8)
                        
                        pil_image = Image.fromarray(interpolated)
                        photo = ImageTk.PhotoImage(pil_image)
                        new_video_frames.append(photo)
                
                # Update on main thread
                def update_gui():
                    self.video_frames = new_video_frames
                    self.total_frames = len(self.video_frames)
                    self.video_path = file_path
                    self.update_video_display()
                    print(f"✅ Video loaded: {self.total_frames} frames")
                
                if hasattr(self.parent_frame, 'after'):
                    self.parent_frame.after(0, update_gui)
                
            except Exception as e:
                print(f"❌ Video load error: {e}")
        
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
        """Update video display"""
        if not self.video_frames or not self.video_label:
            return
        
        if 0 <= self.current_frame_index < len(self.video_frames):
            self.video_label.config(image=self.video_frames[self.current_frame_index])
    
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
                    
                    time.sleep(0.016)  # 60fps
                    
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
        self.root = tk.Tk()
        self.root.title("DARK DESIRES - GOTHIC PATTERN SEQUENCER")
        self.root.geometry("1600x900")  # Larger default size
        self.root.configure(bg='#000000')
    
        # Initialize audio manager and other components
        self.audio_manager = EnhancedAudioManager()
        self.stickers = SimpleStickers(self.root)
        self.pattern_sequencer = PatternSequencer()
        self.current_category = "bj"
        self.joystick_controller = JoystickController()
        self.device_client = IntifaceClient("http://localhost:8080")
        self.video_gallery = VideoGallery()

    
        # Set up callbacks
        self.device_client.set_connection_callback(self.on_connection_change)
        self.joystick_controller.set_callbacks(
            speed_callback=self.on_joystick_speed_change,
            manual_callback=self.on_manual_override,
            skip_callback=self.on_skip_pattern,
            play_pause_callback=self.on_play_pause_button
        )
    
        # State variables
        self.arousal = 0.75
        self.running = False
        self.last_json_write_time = 0
        self.json_write_interval = 0.05
    
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
    
        # Setup GUI with improvements
        self.stickers = SimpleStickers(self.root)
        self.setup_gui()
        self.connect_device()

        self.root.after(2000, self._ensure_sticker_visibility)
        self.root.after(3000, self.fix_sticker_layers)

        # FIXED: Single delayed call for sticker startup
        self.root.after(3000, self._ensure_sticker_visibility)  # 3 seconds delay
        self.root.after(3500, self.fix_sticker_layers)         # Then fix layers

    def fix_sticker_layers(self):
        """Fix sticker layering issues"""
        if hasattr(self, "stickers") and self.stickers:
            # Small delay then bring stickers to front
            self.root.after(100, self.stickers.bring_stickers_to_front)
        

    def debug_stickers(self):
        """Debug what's happening with stickers"""
        print("\n" + "="*50)
        print("🔍 STICKER DEBUG REPORT")
        print("="*50)
    
        if hasattr(self, "stickers") and self.stickers:
            print(f"✅ Stickers object exists")
            print(f"📊 Number of stickers: {len(self.stickers.stickers)}")
            print(f"📁 Assets dir: {self.stickers.assets_dir}")
            print(f"📁 Presets dir: {self.stickers.presets_dir}")
        
            # Check if autostart.json exists
            autostart_path = os.path.join(self.stickers.presets_dir, "autostart.json")
            if os.path.exists(autostart_path):
                print(f"✅ autostart.json exists at: {autostart_path}")
                try:
                    with open(autostart_path, 'r') as f:
                        data = json.load(f)
                        layout = data.get('layout', [])
                        print(f"📋 autostart.json contains {len(layout)} sticker entries")
                except Exception as e:
                    print(f"❌ Error reading autostart.json: {e}")
            else:
                print(f"❌ autostart.json NOT found at: {autostart_path}")
            
            # Check each sticker in detail
            for i, sticker in enumerate(self.stickers.stickers):
                try:
                    x, y = sticker.winfo_x(), sticker.winfo_y()
                    visible = sticker.winfo_viewable()
                    mapped = sticker.winfo_ismapped()
                    manager = sticker.winfo_manager()
                    print(f"  Sticker {i}: x={x}, y={y}, visible={visible}, mapped={mapped}, manager={manager}")
                    print(f"    File: {getattr(sticker, 'file_path', 'NO FILE PATH')}")
                    print(f"    Size: {sticker.winfo_width()}x{sticker.winfo_height()}")
                except Exception as e:
                    print(f"  Sticker {i}: ERROR - {e}")
                
            # Check if any PNG files exist in assets folder
            if os.path.exists(self.stickers.assets_dir):
                png_files = [f for f in os.listdir(self.stickers.assets_dir) if f.endswith('.png')]
                print(f"📁 PNG files in assets: {len(png_files)} files")
                for png in png_files[:3]:  # Show first 3
                    print(f"    - {png}")
            else:
                print(f"❌ Assets directory doesn't exist: {self.stickers.assets_dir}")
            
        else:
            print("❌ No stickers object found")
        
        print("="*50 + "\n")

   
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
    
        # Create wallpaper menu (improved)
        self.create_menu_bar()
    
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
        self.audio_frame = tk.Frame(self.notebook, bg='#220022')  # New audio tab
    
        self.notebook.add(self.main_frame, text='♠ DARK CONTROL ♠')
        self.notebook.add(self.joystick_frame, text='♦ CONTROLLER ♦')
        self.notebook.add(self.audio_frame, text='♫ AUDIO ♫')
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # Setup all tabs
        self.setup_main_tab_fixed()
        self.setup_joystick_tab_fixed()
        self.setup_audio_tab()
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
    
        # Create scrollable frame for main content
        canvas = tk.Canvas(self.main_frame, bg='#220022', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#220022')
    
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
    
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
        # Title with better spacing
        title_frame = tk.Frame(scrollable_frame, bg='#220022')
        title_frame.pack(pady=(10, 20), fill='x')
    
        tk.Label(
            title_frame,
            text="♠ DARK DESIRES SEQUENCER ♠",
            font=("Gothic", 18, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).pack()
    
        # Status section with better organization
        self.setup_status_section(scrollable_frame)
    
        # Speed control section
        self.setup_speed_section(scrollable_frame)
    
        # Build-up section
        self.setup_buildup_section(scrollable_frame)
    
        # Main controls
        self.setup_main_controls(scrollable_frame)
    
        # ✅ CORRECT - Move this line INSIDE the method
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def setup_status_section(self, parent):
        """Setup status section with better layout"""
        status_container = tk.LabelFrame(
            parent, 
            text="♦ SYSTEM STATUS ♦", 
            font=("Gothic", 12, "bold"),
            fg='#ff66cc', 
            bg='#220022',
            labelanchor='n'
        )
        status_container.pack(pady=10, padx=20, fill='x')
    
        # Grid layout for status items
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
            text=f"📁 Patterns: {pattern_count} loaded",
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
        
            # Update pattern count display
            pattern_count = len(self.pattern_sequencer.pattern_database)
            # Find and update your pattern count label (you'll need to make this a self. variable)
        
            # Restart if was running
            if was_running:
                self.start_playback()
        
            print(f"🔄 Switched to category: {new_category} ({pattern_count} patterns)")        
    
    def setup_speed_section(self, parent):
        """Setup speed control section with better layout"""
        speed_container = tk.LabelFrame(
            parent,
            text="♠ DESIRES INTENSITY ♠",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022',
            labelanchor='n'
        )
        speed_container.pack(pady=15, padx=20, fill='x')
    
        # Speed labels frame
        labels_frame = tk.Frame(speed_container, bg='#220022')
        labels_frame.pack(pady=(15, 5), padx=20, fill='x')
    
        tk.Label(
            labels_frame, 
            text="Slow (0.3x)", 
            font=("Gothic", 10), 
            fg='#44ff88', 
            bg='#220022'
        ).pack(side=tk.LEFT)
    
        tk.Label(
            labels_frame, 
            text="Fast (2.0x)", 
            font=("Gothic", 10), 
            fg='#cc3366', 
            bg='#220022'
        ).pack(side=tk.RIGHT)
    
        # Speed slider with better styling
        slider_frame = tk.Frame(speed_container, bg='#220022')
        slider_frame.pack(pady=10, padx=20)
    
        self.arousal_scale = tk.Scale(
            slider_frame,
            from_=0.3,
            to=2.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            length=400,
            bg='#220022',
            fg='#ff66cc',
            highlightthickness=0,
            troughcolor='#440044',
            activebackground='#ff66cc',
            font=("Gothic", 10),
            command=self.on_speed_change
        )
        self.arousal_scale.set(0.75)
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
        """Setup build-up section with improved layout"""
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
        self.buildup_time_entry.insert(0, "60")
    
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
    
        # Max Speed input
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
            min_value=0.3,
            max_value=3.0,
            width=8,
            font=("Gothic", 11),
            bg='#440044',
            fg='#ff66cc',
            insertbackground='#ffffff',
            justify='center'
        )
        self.buildup_max_speed_entry.grid(row=1, column=2, padx=10, pady=5)
        self.buildup_max_speed_entry.insert(0, "2.0")
    
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

    def setup_main_controls(self, parent):
        """Setup main control buttons with better layout"""
        self.play_button = tk.Button(
            parent,
            text="♠ AWAKEN ♠",
            font=("Gothic", 16, "bold"),
            bg='#004400',
            fg='#66ff66',
        width=20,
            height=3,
            command=self.toggle_playback,
            state='disabled'
        )
        self.play_button.pack(pady=10)
    
        self.stop_button = tk.Button(
            parent,
            text="♦ EMERGENCY STOP ♦",
            font=("Gothic", 12, "bold"),
            bg='#440000',
           fg='#ff6666',
            width=20,
            height=2,
            command=self.emergency_stop,
            state='disabled'
        )
        self.stop_button.pack(pady=5)
    
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


    def setup_audio_tab(self):
        """Setup audio control tab"""
        # Title
        tk.Label(
            self.audio_frame,
            text="♫ ENHANCED AUDIO SYSTEM ♫",
            font=("Gothic", 16, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).pack(pady=20)
    
        # Voice selection
        voice_container = tk.LabelFrame(
            self.audio_frame,
            text="♠ VOICE SELECTION ♠",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022',
            labelanchor='n'
        )
        voice_container.pack(pady=15, padx=20, fill='x')
    
        # Current voice display
        current_voice_frame = tk.Frame(voice_container, bg='#220022')
        current_voice_frame.pack(pady=15, fill='x')
    
        tk.Label(
            current_voice_frame,
            text="Current Voice:",
            font=("Gothic", 11, "bold"),
            fg='#ff66cc',
            bg='#220022'
    ).pack(side=tk.LEFT, padx=10)
        
        self.current_voice_label = tk.Label(
            current_voice_frame,
            text=self.audio_manager.current_voice,
            font=("Gothic", 11, "bold"),
            fg='#66ff66',
            bg='#220022'
        )
        self.current_voice_label.pack(side=tk.LEFT, padx=20)
    
        # Voice selection dropdown
        voice_select_frame = tk.Frame(voice_container, bg='#220022')
        voice_select_frame.pack(pady=10, fill='x')
    
        tk.Label(
            voice_select_frame,
            text="Available Voices:",
            font=("Gothic", 11),
            fg='#ff66cc',
            bg='#220022'
        ).pack(side=tk.LEFT, padx=10)
    
        self.voice_combo = ttk.Combobox(
            voice_select_frame,
            values=self.audio_manager.get_available_voices(),
            state="readonly",
            width=20,
            font=("Gothic", 10)
        )
        self.voice_combo.pack(side=tk.LEFT, padx=10)
        self.voice_combo.set(self.audio_manager.current_voice)
        self.voice_combo.bind("<<ComboboxSelected>>", self.on_voice_change)
    
        tk.Button(
            voice_select_frame,
            text="♫ Apply Voice ♫",
            font=("Gothic", 10, "bold"),
            bg='#004400',
            fg='#66ff66',
            command=self.apply_voice_change
        ).pack(side=tk.LEFT, padx=10)
    
        # Audio controls
        audio_controls_container = tk.LabelFrame(
            self.audio_frame,
            text="♦ AUDIO CONTROLS ♦",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022',
            labelanchor='n'
        )
        audio_controls_container.pack(pady=15, padx=20, fill='x')
    
        # Volume control
        volume_frame = tk.Frame(audio_controls_container, bg='#220022')
        volume_frame.pack(pady=15, fill='x')
    
        tk.Label(
            volume_frame,
            text="Volume:",
            font=("Gothic", 11, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).pack(side=tk.LEFT, padx=10)
    
        self.volume_scale = tk.Scale(
            volume_frame,
            from_=0.0,
            to=1.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            length=300,
            bg='#220022',
            fg='#ff66cc',
            highlightthickness=0,
            troughcolor='#440044',
            activebackground='#ff66cc',
            font=("Gothic", 10),
            command=self.on_volume_change
        )
        self.volume_scale.set(self.audio_manager.volume)
        self.volume_scale.pack(side=tk.LEFT, padx=10)
    
        # Enable/Disable toggle
        toggle_frame = tk.Frame(audio_controls_container, bg='#220022')
        toggle_frame.pack(pady=10)
    
        self.audio_enabled_var = tk.BooleanVar(value=self.audio_manager.audio_enabled)
        tk.Checkbutton(
            toggle_frame,
            text="Enable Audio System",
            variable=self.audio_enabled_var,
            font=("Gothic", 11, "bold"),
            fg='#ff66cc',
            bg='#220022',
            selectcolor='#333333',
            command=self.toggle_audio_system
        ).pack(pady=5)
    
        # Test audio buttons
        test_container = tk.LabelFrame(
            self.audio_frame,
            text="♠ TEST AUDIO ♠",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022',
            labelanchor='n'
        )
        test_container.pack(pady=15, padx=20, fill='x')
    
        # Create test buttons in a grid
        test_buttons_frame = tk.Frame(test_container, bg='#220022')
        test_buttons_frame.pack(pady=15, padx=15)
    
        test_triggers = [
            ('Device Connect', 'device_connect'),
            ('Start Playback', 'start_playback'),
            ('Manual Override', 'manual_start'),
            ('Speed Change', 'speed_change_manual'),
            ('Pattern Skip', 'pattern_skip'),
            ('Build-up Start', 'buildup_start'),
            ('Emergency Stop', 'emergency_stop'),
            ('Error Sound', 'error_playback')
        ]
    
        for i, (name, trigger) in enumerate(test_triggers):
            row = i // 4
            col = i % 4
        
            tk.Button(
                test_buttons_frame,
                text=name,
                font=("Gothic", 9, "bold"),
                bg='#554455',
                fg='#ff66cc',
                width=12,
                command=lambda t=trigger: self.test_audio_trigger(t)
            ).grid(row=row, column=col, padx=5, pady=5)
            
    def setup_sticker_controls(self):
        """FIXED sticker controls setup"""
        print("🔧 Setting up sticker controls...")
    
        # Create the sticker frame
        sticker_frame = tk.LabelFrame(
            self.audio_frame,
            text="✨ STICKERS ✨",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022',
            labelanchor='n'
        )
        sticker_frame.pack(pady=15, padx=20, fill='x')

        # Button container
        button_frame = tk.Frame(sticker_frame, bg='#220022')
        button_frame.pack(pady=15, fill='x')

        # ADD button
        tk.Button(
            button_frame,
            text="📎 ADD STICKER",
            font=("Gothic", 11, "bold"),
            bg='#004400',
            fg='#66ff66',
            width=15,
            height=2,
            command=self.stickers.add_sticker
        ).pack(side=tk.LEFT, padx=10, pady=5)

        # LOCK button  
        tk.Button(
            button_frame,
            text="🔒 LOCK ALL",
            font=("Gothic", 11, "bold"),
            bg='#444400',
            fg='#ffff66',
            width=15,
            height=2,
            command=self.stickers.toggle_lock_all
        ).pack(side=tk.LEFT, padx=10, pady=5)

        # CLEAR button
        tk.Button(
            button_frame,
            text="🧹 CLEAR ALL",
            font=("Gothic", 11, "bold"),
            bg='#440000',
            fg='#ff6666',
            width=15,
            height=2,
            command=self.stickers.clear_all
        ).pack(side=tk.LEFT, padx=10, pady=5)
    
        # Second row for save/load
        save_load_frame = tk.Frame(sticker_frame, bg='#220022')
        save_load_frame.pack(pady=(0, 15), fill='x')

        tk.Button(
            save_load_frame,
            text="💾 Save as Startup",
            font=("Gothic", 10, "bold"),
            bg='#004466',
            fg='#66ccff',
            width=18,
            command=self.stickers.save_as_startup
        ).pack(side=tk.LEFT, padx=10)

        tk.Button(
            save_load_frame,
            text="↩ Load Startup",
            font=("Gothic", 10, "bold"),
            bg='#440066',
            fg='#cc66ff',
            width=18,
            command=self.stickers.load_startup_now
        ).pack(side=tk.LEFT, padx=10)

        # Instructions
        tk.Label(
            sticker_frame,
            text="📎 ADD: Load images • 🖱️ Drag to move • Ctrl+Scroll: Resize • Right-click: Options",
            font=("Gothic", 9),
            fg='#cccccc',
            bg='#220022',
            wraplength=400
        ).pack(pady=10)

        

    def setup_joystick_tab_fixed(self):
        """Set up joystick configuration tab with better layout - FIXED VERSION"""

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

        # Control rows
        controls = [
            ("Speed Control Axis:", "speed"),
            ("Manual Control Axis:", "manual"),
            ("Manual Override Button:", "manual_btn"),
            ("Skip Pattern Button:", "skip"),
            ("Play/Pause Button:", "play_pause")
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

        self.button_states_label = tk.Label(
            monitor_frame,
            text="Buttons: Manual:OFF Skip:OFF Play/Pause:OFF",
            font=("Gothic", 11, "bold"),
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
            height=8,
            width=60,
            font=("Gothic", 10),
            bg='#330033',
            fg='#cccccc',
            wrap=tk.WORD,
            relief='sunken',
            bd=2
        )
        instructions_text.pack(pady=15, padx=15)

        instructions = """♦ Click DETECT next to each control to configure
    ♦ Speed Axis: Controls playback speed (neutral=1x, pull=slow, push=fast)
    ♦ Manual Axis: Position control during manual override
    ♦ Manual Override: Hold + move manual axis for direct control
    ♦ Skip Pattern: Jump to next pattern smoothly
    ♦ Play/Pause: Single button toggles playback
    ♦ Mouse wheel on time inputs: ±30 seconds per scroll
    ♦ Invert: Reverses axis direction
    ♦ Modes: full_range, half_positive, half_negative, trigger"""

        instructions_text.insert(tk.END, instructions)
        instructions_text.config(state=tk.DISABLED)

        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Initialize detected values to -1 if not already set
        if not hasattr(self, 'detected_speed_axis'):
            self.detected_speed_axis = -1
        if not hasattr(self, 'detected_manual_axis'):
            self.detected_manual_axis = -1
        if not hasattr(self, 'detected_manual_btn_button'):
            self.detected_manual_btn_button = -1
        if not hasattr(self, 'detected_skip_button'):
            self.detected_skip_button = -1
        if not hasattr(self, 'detected_play_pause_button'):
            self.detected_play_pause_button = -1

        # Schedule initialization AFTER UI is created
        self.root.after(100, self.refresh_joystick_devices)
        

        print("✅ Joystick tab setup complete")

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

    def create_menu_bar(self):
        """Create improved menu bar"""
        menu_bar = tk.Menu(self.root, bg='#330033', fg='#ff66cc', font=("Gothic", 10))
        self.root.config(menu=menu_bar)
    
        # Audio menu
        audio_menu = tk.Menu(menu_bar, tearoff=0, bg='#330033', fg='#ff66cc', font=("Gothic", 9))
        menu_bar.add_cascade(label="♫ AUDIO ♫", menu=audio_menu)
        audio_menu.add_command(label="Refresh Voices", command=self.refresh_audio_voices)
        audio_menu.add_command(label="Test All Triggers", command=self.test_all_audio_triggers)

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

    def apply_voice_change(self):
        """Apply the selected voice change"""
        try:
            selected_voice = self.voice_combo.get()
            if self.audio_manager.set_voice(selected_voice):
                self.current_voice_label.config(text=selected_voice)
                self.audio_manager.play('device_connect')  # Test sound
                messagebox.showinfo("Success", f"Voice changed to: {selected_voice}")
            else:
                messagebox.showerror("Error", "Failed to change voice!")
        except Exception as e:
            messagebox.showerror("Error", f"Voice change error: {e}")

    def on_volume_change(self, value):
        """Handle volume change"""
        self.audio_manager.set_volume(float(value))

    def toggle_audio_system(self):
        """Toggle audio system on/off"""
        enabled = self.audio_manager.toggle_enabled()
        if enabled:
            self.audio_manager.play('device_connect')

    def test_audio_trigger(self, trigger):
        """Test a specific audio trigger"""
        self.audio_manager.play(trigger)

    def refresh_audio_voices(self):
        """Refresh available voices"""
        self.audio_manager.scan_available_voices()
        self.voice_combo['values'] = self.audio_manager.get_available_voices()
        messagebox.showinfo("Voices Refreshed", f"Found {len(self.audio_manager.get_available_voices())} voices")

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

    def apply_dark_theme(self):
        """Apply consistent dark theme to all widgets"""
        style = ttk.Style()
        style.theme_use('clam')
    
        # Configure ttk styles
        style.configure('TCombobox', fieldbackground='#440044', background='#440044', 
                       foreground='#ff66cc', borderwidth=1, relief='solid')
        style.configure('TEntry', fieldbackground='#440044', foreground='#ff66cc', 
                       borderwidth=1, relief='solid')
    
        # Configure root window
        self.root.configure(bg='#000000')
    
        # Set window icon if available
        try:
            self.root.iconbitmap('icon.ico')  # Add your icon file
        except:
            pass

    def on_random_toggle(self):
        """Handle time-based random toggle"""
        if self.random_enabled.get():
            if self.stroke_enabled.get():
                self.stroke_enabled.set(False)  # Disable stroke mode
            self.start_random_video_timer()
            print("🕒 Time-based video switching enabled")
        else:
            self.stop_random_video_timer()
            print("🕒 Time-based video switching disabled")

    def on_stroke_toggle(self):
        """Handle stroke-based toggle"""
        if self.stroke_enabled.get():
            if self.random_enabled.get():
                self.random_enabled.set(False)  # Disable time mode
                self.stop_random_video_timer()
            self.stroke_count = 0  # Reset counter
            self.update_stroke_display()
            print("🎬 Stroke-based video switching enabled")
        else:
            print("🎬 Stroke-based video switching disabled")

    def start_random_video_timer(self):
        """Start time-based random video switching"""
        # Implementation for time-based switching
        pass

    def stop_random_video_timer(self):
        """Stop time-based random video switching"""
        # Implementation to stop timer
        pass

    def update_stroke_display(self):
        """Update stroke counter display"""
        if self.stroke_enabled.get():
            try:
                target = int(self.stroke_interval_entry.get())
                self.stroke_status_label.config(
                    text=f"Stroke counter: {self.stroke_count}/{target} strokes",
                    fg='#66ff66'
                )
            except:
                self.stroke_status_label.config(text="Stroke counter: Invalid target", fg='#ff6666')
        else:
            self.stroke_status_label.config(text="Stroke counter: Inactive", fg='#888888')        
    
    def setup_joystick_tab(self):
        """Set up joystick configuration tab"""
        
        # Title
        tk.Label(
            self.joystick_frame,
            text="♦ CONTROLLER CONFIGURATION ♦",
            font=("Gothic", 16, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).pack(pady=15)
        
        # Device selection
        device_frame = tk.Frame(self.joystick_frame, bg='#220022')
        device_frame.pack(pady=15, padx=20, fill='x')
        
        tk.Label(
            device_frame,
            text="♠ DEVICE SELECTION ♠",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).pack(anchor='w')
        
        device_select_frame = tk.Frame(device_frame, bg='#220022')
        device_select_frame.pack(pady=5, fill='x')
        
        tk.Label(device_select_frame, text="Joystick:", font=("Gothic", 10), fg='#ff66cc', bg='#220022').pack(side=tk.LEFT)
        
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
            text="Refresh",
            font=("Gothic", 9),
            bg='#554455',
            fg='#ff6666',
            command=self.refresh_joystick_devices
        ).pack(side=tk.LEFT, padx=5)
        
        # Control mapping
        config_frame = tk.Frame(self.joystick_frame, bg='#220022')
        config_frame.pack(pady=15, padx=20, fill='x')
        
        tk.Label(
            config_frame,
            text="♥ CONTROL MAPPING ♥",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).pack(anchor='w')
        
        # Create control rows with enhanced options
        controls = [
            ("Speed Control Axis:", "speed"),
            ("Manual Control Axis:", "manual"),
            ("Manual Override Button:", "manual_btn"),
            ("Skip Pattern Button:", "skip"),
            ("Play/Pause Button:", "play_pause")
        ]
        
        for label_text, control_type in controls:
            self.create_control_row(config_frame, label_text, control_type)
        
        # Apply button
        tk.Button(
            config_frame,
            text="♠ APPLY CONFIGURATION ♠",
            font=("Gothic", 12, "bold"),
            bg='#004400',
            fg='#ff6666',
            command=self.apply_joystick_config
        ).pack(pady=15)
        
        # Live monitoring
        live_frame = tk.Frame(self.joystick_frame, bg='#220022')
        live_frame.pack(pady=15, padx=20, fill='x')
        
        tk.Label(
            live_frame,
            text="♦ LIVE INPUT MONITORING ♦",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).pack(anchor='w')
        
        self.axis_value_label = tk.Label(
            live_frame,
            text="Speed Axis: 0.000 | Manual Axis: 0.000",
            font=("Gothic", 10),
            fg='#66ff66',
            bg='#220022'
        )
        self.axis_value_label.pack(pady=2, anchor='w')
        
        self.button_states_label = tk.Label(
            live_frame,
            text="Buttons: Manual:OFF Skip:OFF Play/Pause:OFF",
            font=("Gothic", 10),
            fg='#66ff66',
            bg='#220022'
        )
        self.button_states_label.pack(pady=2, anchor='w')
        
        # Instructions
        instructions_frame = tk.Frame(self.joystick_frame, bg='#220022')
        instructions_frame.pack(pady=15, padx=20, fill='x')
        
        tk.Label(
            instructions_frame,
            text="♠ DARK INSTRUCTIONS ♠",
            font=("Gothic", 12, "bold"),
            fg='#ff66cc',
            bg='#220022'
        ).pack(anchor='w')
        
        instructions = [
            "• Click DETECT next to each control to configure",
            "• Speed Axis: Controls playback speed (neutral=1x, pull=slow, push=fast)",
            "• Manual Axis: Position control during manual override",
            "• Manual Override: Hold + move manual axis for direct control", 
            "• Skip Pattern: Jump to next pattern smoothly",
            "• Play/Pause: Single button toggles playback",
            "• Mouse wheel on time input: ±30 seconds per scroll",
            "• Invert: Reverses axis direction",
            "• Modes: full_range, half_positive, half_negative, trigger"
        ]
        
        for instruction in instructions:
            tk.Label(
                instructions_frame,
                text=instruction,
                font=("Gothic", 9),
                fg='#cccccc',
                bg='#220022',
                justify=tk.LEFT
            ).pack(anchor='w', pady=1)
        
        # Initialize devices
        self.root.after(100, self.refresh_joystick_devices)
        self.root.after(200, self.load_joystick_config)

    def setup_video_panel(self, video_container):
        """Set up video visualizer panel"""

        # 🆕 ADD THIS - Gallery Section
        gallery_container = tk.Frame(video_container, bg='#220022', relief='sunken', bd=1)
        gallery_container.pack(pady=10, fill='x', padx=10)
        # ... (rest of gallery code from above)

        # 🆕 ADD THIS - Video Navigation Controls
        nav_frame = tk.Frame(video_container, bg='#220022')
        nav_frame.pack(pady=5, fill='x')

        self.prev_video_btn = tk.Button(nav_frame, text="◀ PREV", font=("Gothic", 10, "bold"),
                                       bg='#554455', fg='#ff6666', width=8, state='disabled')
        self.prev_video_btn.pack(side=tk.LEFT, padx=5)

        self.current_video_name = tk.Label(nav_frame, text="No Video Loaded", 
                                          font=("Gothic", 12, "bold"), fg='#ff66cc', bg='#220022')
        self.current_video_name.pack(side=tk.LEFT, expand=True)

        self.next_video_btn = tk.Button(nav_frame, text="NEXT ▶", font=("Gothic", 10, "bold"),
                                       bg='#554455', fg='#ff6666', width=8, state='disabled')
        self.next_video_btn.pack(side=tk.RIGHT, padx=5)

        self.delete_video_btn = tk.Button(nav_frame, text="🗑️", font=("Gothic", 12, "bold"),
                                         bg='#440000', fg='#ff6666', width=3, state='disabled')
        self.delete_video_btn.pack(side=tk.RIGHT, padx=2)

        self.save_video_btn = tk.Button(nav_frame, text="SAVE", font=("Gothic", 10, "bold"),
                                       bg='#004400', fg='#ff6666', width=6, state='disabled')
        self.save_video_btn.pack(side=tk.RIGHT, padx=5)
    
        # Title
        title_label = tk.Label(video_container, text="♠ VIDEO DARK VISUALIZER ♠", 
                          font=("Gothic", 16, "bold"), fg='#ff66cc', bg='#220022')
        title_label.pack(pady=10)
    
        # Controls at top
        controls_frame = tk.Frame(video_container, bg='#220022')
        controls_frame.pack(pady=5)
    
        # Open video button
        open_btn = tk.Button(controls_frame, text="♦ OPEN VIDEO ♦", font=("Gothic", 12, "bold"), 
                            bg='#004400', fg='#ff6666', width=12, 
                            command=self.open_video)
        open_btn.pack(side=tk.LEFT, padx=5)
    
        # Direction controls
        direction_frame = tk.Frame(controls_frame, bg='#220022')
        direction_frame.pack(side=tk.LEFT, padx=20)
    
        tk.Label(direction_frame, text="Direction:", font=("Gothic", 10), 
                fg='#ff66cc', bg='#220022').pack()
    
        self.direction_var = tk.StringVar(value="0_to_100")
        direction_combo = ttk.Combobox(direction_frame, textvariable=self.direction_var, 
                                      values=["0_to_100", "100_to_0"], state="readonly", width=10)
        direction_combo.pack()
        direction_combo.bind("<<ComboboxSelected>>", self.on_video_direction_change)
    
        # Invert checkbox
        self.video_invert_var = tk.BooleanVar()
        invert_check = tk.Checkbutton(direction_frame, text="Invert", variable=self.video_invert_var, 
                                     fg='#ff66cc', bg='#220022', selectcolor='#333333',
                                     command=self.on_video_direction_change)
        invert_check.pack()
    
        # Test mode
        test_frame = tk.Frame(controls_frame, bg='#220022')
        test_frame.pack(side=tk.LEFT, padx=20)
    
        self.test_mode_var = tk.BooleanVar()
        test_check = tk.Checkbutton(test_frame, text="Test Mode", variable=self.test_mode_var, 
                                   fg='#ff66cc', bg='#220022', selectcolor='#333333')
        test_check.pack()
    
        self.test_slider = tk.Scale(test_frame, from_=0, to=100, resolution=1, orient=tk.HORIZONTAL, 
                                   length=200, bg='#220022', fg='#ff66cc', highlightthickness=0, troughcolor='#440044', activebackground='#ff66cc',
                                   command=self.on_test_position_change)
        self.test_slider.set(50)
        self.test_slider.pack()
    
        # Video display area (big)
        self.video_label = tk.Label(video_container, text="Load a video to see visualization", 
                                   font=("Gothic", 14), fg='#888888', bg='#220022')
        self.video_label.pack(fill='both', expand=True, padx=10, pady=10)
    
        # Status
        self.video_status_label = tk.Label(video_container, text="🎹 No video loaded", 
                                          font=("Gothic", 10), fg='#888888', bg='#220022')
        self.video_status_label.pack(pady=5)
        # 🆕 ADD THIS - Gallery Section  
        gallery_container = tk.Frame(video_container, bg='#220022', relief='sunken', bd=1)
        gallery_container.pack(pady=10, fill='x', padx=10)

        # Gallery navigation
        gallery_nav_frame = tk.Frame(gallery_container, bg='#220022')
        gallery_nav_frame.pack(pady=5, fill='x')

        self.prev_gallery_btn = tk.Button(gallery_nav_frame, text="◀ GALLERY", 
                                         font=("Gothic", 10, "bold"), bg='#554455', fg='#ff6666', 
                                         width=12, state='disabled')
        self.prev_gallery_btn.pack(side=tk.LEFT, padx=5)

        self.next_gallery_btn = tk.Button(gallery_nav_frame, text="GALLERY ▶", 
                                         font=("Gothic", 10, "bold"), bg='#554455', fg='#ff6666', 
                                         width=12, state='disabled')
        self.next_gallery_btn.pack(side=tk.RIGHT, padx=5)

        # Gallery status
        self.gallery_status = tk.Label(gallery_nav_frame, text="Gallery: 0 videos", 
                              font=("Gothic", 10), fg='#888888', bg='#220022')
        self.gallery_status.pack()

        # Gallery preview frame (5 thumbnails)
        self.gallery_frame = tk.Frame(gallery_container, bg='#220022')
        self.gallery_frame.pack(pady=10, fill='x')

        # Create 5 thumbnail slots
        self.gallery_thumbnails = []
        for i in range(5):
            thumb_frame = tk.Frame(self.gallery_frame, bg='#440044', relief='raised', bd=1)
            thumb_frame.pack(side=tk.LEFT, padx=5, fill='both', expand=True)
    
            # Thumbnail video display
            thumb_label = tk.Label(thumb_frame, text=f"Slot {i+1}\nEmpty", 
                                  font=("Gothic", 8), fg='#666666', bg='#440044',
                                  width=15, height=6)
            thumb_label.pack(pady=2)
            thumb_label.bind("<Button-1>", lambda e, idx=i: self.on_thumbnail_click(idx))
    
            # Video name below thumbnail
            name_label = tk.Label(thumb_frame, text="", font=("Gothic", 8), 
                                 fg='#cccccc', bg='#440044')
            name_label.pack()
    
            self.gallery_thumbnails.append({
                'frame': thumb_frame,
                'label': thumb_label, 
                'name': name_label,
                'video_id': None
            })

        # Random video feature
        random_frame = tk.Frame(gallery_container, bg='#220022')
        random_frame.pack(pady=5, fill='x')

        tk.Label(random_frame, text="🔀 Random every", font=("Gothic", 10), 
                 fg='#ff66cc', bg='#220022').pack(side=tk.LEFT, padx=5)

        self.random_interval_entry = tk.Entry(random_frame, width=5, font=("Gothic", 10),
                                             bg='#440044', fg='#ff66cc', insertbackground='#ffffff')
        self.random_interval_entry.pack(side=tk.LEFT, padx=2)
        self.random_interval_entry.insert(0, "30")

        tk.Label(random_frame, text="seconds", font=("Gothic", 10), 
                 fg='#ff66cc', bg='#220022').pack(side=tk.LEFT, padx=2)

        self.random_enabled = tk.BooleanVar()
        self.random_checkbox = tk.Checkbutton(random_frame, text="Enable Random", 
                                             variable=self.random_enabled, font=("Gothic", 10),
                                             fg='#ff66cc', bg='#220022', selectcolor='#333333')
        self.random_checkbox.pack(side=tk.LEFT, padx=10)
        
       # Create video visualizer instance
        self.video_visualizer = VideoVisualizer(self.root)
        self.video_visualizer.video_label = self.video_label
        self.video_visualizer.invert_var = self.video_invert_var
        self.video_visualizer.test_mode_var = self.test_mode_var
        self.video_visualizer.test_slider = self.test_slider
    
        # Create video visualizer instance (ADD THIS AT THE END)
        self.video_visualizer = VideoVisualizer(self.root)
        self.video_visualizer.video_label = self.video_label
        self.video_visualizer.invert_var = self.video_invert_var
        self.video_visualizer.test_mode_var = self.test_mode_var
        self.video_visualizer.test_slider = self.test_slider

        # Start monitoring position data
        self.start_video_position_monitoring()

        # Connect gallery button callbacks (ADD AT END OF setup_video_panel)
        self.save_video_btn.config(command=self.save_current_video)
        self.delete_video_btn.config(command=self.delete_current_video)
        self.prev_video_btn.config(command=self.load_prev_video)
        self.next_video_btn.config(command=self.load_next_video)
        self.prev_gallery_btn.config(command=self.prev_gallery_page)
        self.next_gallery_btn.config(command=self.next_gallery_page)

        # Update gallery display
        self.update_gallery_display()
        
    def open_video(self):
        """Open video file dialog"""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Video Clip", 
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.webm"), ("All files", "*.*")]
       )
        if file_path:
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
                    time.sleep(0.01)
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
    
    def create_control_row(self, parent, label_text, control_type):
        """Create a control configuration row with enhanced options - FIXED VERSION"""
        frame = tk.Frame(parent, bg='#220022')
        frame.pack(pady=5, fill='x')
    
        tk.Label(
            frame,
            text=label_text,
            font=("Gothic", 10),
            fg='#ff66cc',
            bg='#220022',
            width=20,
            anchor='w'
        ).pack(side=tk.LEFT)
    
        # Detection label
        label = tk.Label(
            frame,
            text="Not Set",
            font=("Gothic", 10),
            fg='#cc3366',
            bg='#440044',
            width=12,
            relief='sunken'
        )
        label.pack(side=tk.LEFT, padx=5)
        setattr(self, f"detect_{control_type}_label", label)
    
        # FIXED: Detect button - check if it's an axis or button control
        if control_type in ["speed", "manual"]:  # These are AXIS controls
            command = lambda ct=control_type: self.start_axis_detection(ct)
            bg_color = '#44aa44'
            button_text = "DETECT AXIS"
        else:  # These are BUTTON controls (manual_btn, skip, play_pause)
            command = lambda ct=control_type: self.start_button_detection(ct)
            bg_color = '#4444ff'
            button_text = "DETECT BTN"
    
        button = tk.Button(
            frame,
            text=button_text,
            font=("Gothic", 9, "bold"),
            bg=bg_color,
            fg='#ff6666',
            width=10,
            command=command
        )
        button.pack(side=tk.LEFT, padx=5)
        setattr(self, f"detect_{control_type}_btn", button)
    
        # Enhanced options for axes only
        if control_type in ["speed", "manual"]:  # Only axes get these options
            # Invert checkbox
            invert_var = tk.BooleanVar()
            setattr(self, f"{control_type}_invert_var", invert_var)
        
            tk.Checkbutton(
                frame,
                text="Invert",
                variable=invert_var,
                fg='#ff66cc',
                bg='#220022',
                selectcolor='#333333',
                font=("Gothic", 8)
            ).pack(side=tk.LEFT, padx=5)
        
            # Axis mode dropdown
            mode_combo = ttk.Combobox(
                frame,
                width=12,
                state="readonly",
                font=("Gothic", 8),
                values=["full_range", "half_positive", "half_negative", "trigger"]
            )
            mode_combo.set("full_range")
            mode_combo.pack(side=tk.LEFT, padx=5)
            setattr(self, f"{control_type}_mode_combo", mode_combo)
    
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
        """Apply enhanced joystick configuration - FIXED VERSION"""
        try:
            # Validate all inputs detected
            required_inputs = [
                ("speed axis", self.detected_speed_axis),
                ("manual axis", self.detected_manual_axis),
                ("manual button", self.detected_manual_btn_button),
                ("skip button", self.detected_skip_button),
                ("play/pause button", self.detected_play_pause_button)
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
            print(f"Options: speed_invert={speed_invert}, manual_invert={manual_invert}")
            print(f"Modes: speed_mode={speed_mode}, manual_mode={manual_mode}")
        
            # Configure with enhanced options
            self.joystick_controller.configure(
                self.detected_speed_axis,
                self.detected_manual_axis,
                self.detected_manual_btn_button,
                self.detected_skip_button,
                self.detected_play_pause_button,
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
                play_pause_callback=self.on_play_pause_button
            )
        
            # Start monitoring
            if self.joystick_controller.start():
                if hasattr(self, 'joystick_status_label'):
                    self.joystick_status_label.config(
                        text="🎮 Joystick: ACTIVE with enhanced features",
                        fg='#66ff66'
                    )
            
                # Save the config AFTER successful application
                self.save_joystick_config()
            
                # Start live monitoring display
                self.update_joystick_display()
            
                messagebox.showinfo("Success", 
                    f"Enhanced joystick configured!\n\n"
                    f"Speed: Axis {self.detected_speed_axis} ({speed_mode}, invert: {speed_invert})\n"
                    f"Manual: Axis {self.detected_manual_axis} ({manual_mode}, invert: {manual_invert})\n"
                    f"Manual Button: {self.detected_manual_btn_button}\n"
                    f"Skip Button: {self.detected_skip_button}\n"
                    f"Play/Pause Button: {self.detected_play_pause_button}")
            
                print("✅ Joystick configuration applied and saved successfully")
            
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
        """Save joystick config to file - FIXED VERSION"""
        try:
            config = {
                "device_name": self.device_combo.get() if hasattr(self, 'device_combo') and self.device_combo else "",
                "speed_axis": getattr(self, 'detected_speed_axis', -1),
                "manual_axis": getattr(self, 'detected_manual_axis', -1),
                "manual_btn": getattr(self, 'detected_manual_btn_button', -1),
                "skip_btn": getattr(self, 'detected_skip_button', -1),
                "play_pause_btn": getattr(self, 'detected_play_pause_button', -1),
                "speed_invert": self.speed_invert_var.get() if hasattr(self, 'speed_invert_var') else False,
                "manual_invert": self.manual_invert_var.get() if hasattr(self, 'manual_invert_var') else False,
                "speed_mode": self.speed_mode_combo.get() if hasattr(self, 'speed_mode_combo') else "full_range",
                "manual_mode": self.manual_mode_combo.get() if hasattr(self, 'manual_mode_combo') else "full_range"
            }
        
            print(f"💾 Saving config: {config}")
        
            with open("joystick_config.json", "w") as f:
                json.dump(config, f, indent=2)
            
            print("✅ Joystick config saved successfully")
        
        except Exception as e:
            print(f"❌ Error saving joystick config: {e}")
            import traceback
            traceback.print_exc()  
    
    def update_joystick_display(self):
        """Update live joystick display"""
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
                
                # Get button states
                manual_state = "ON" if (self.detected_manual_btn_button >= 0 and 
                                      self.joystick_controller.device.get_button(self.detected_manual_btn_button)) else "OFF"
                skip_state = "ON" if (self.detected_skip_button >= 0 and 
                                    self.joystick_controller.device.get_button(self.detected_skip_button)) else "OFF"
                play_pause_state = "ON" if (self.detected_play_pause_button >= 0 and 
                                          self.joystick_controller.device.get_button(self.detected_play_pause_button)) else "OFF"
                
                self.button_states_label.config(
                    text=f"Buttons: Manual:{manual_state} Skip:{skip_state} Play/Pause:{play_pause_state}"
                )
                
            except Exception as e:
                pass
        
        if self.joystick_controller.running:
            self.root.after(100, self.update_joystick_display)
    
    # Event handlers
    def on_connection_change(self, connected: bool, device_found: bool = False):
        """Handle connection status changes"""
        def update_gui():
            if connected and device_found:
                self.connection_label.config(text="● Device: Connected & Ready", fg='#66ff66')
                self.status_label.config(text="Ready for seamless streaming", fg='#66ff66')
                self.play_button.config(state='normal')
                self.stop_button.config(state='normal')
                self.audio_manager.play('device_connect')
                
            elif connected and not device_found:
                self.connection_label.config(text="● Server Connected, Scanning...", fg='#ff99cc')
                self.status_label.config(text="Server connected, waiting for device...", fg='#ff99cc')
                self.play_button.config(state='disabled')
                self.stop_button.config(state='disabled')
                self.audio_manager.play('device_scanning')
                
            else:
                self.audio_manager.play('device_disconnect')
                self.connection_label.config(text="● Device: Disconnected", fg='#cc3366')
                self.status_label.config(text="Not connected to server", fg='#cc3366')
                self.play_button.config(state='disabled')
                self.stop_button.config(state='disabled')
                if self.running:
                    self.stop_playback()
                
        self.root.after(0, update_gui)
    
    def connect_device(self):
        """Connect to device"""
        self.device_client.connect()
    
    def on_speed_change(self, value):
        """Handle manual speed slider changes - RESTORED"""
        self.arousal = float(value)
        self.pattern_sequencer.base_speed = self.arousal
        # Show it's manual control, not joystick
        self.speed_display_label.config(text=f"Manual Speed: {self.arousal:.2f}x")
        self.audio_manager.play('speed_change_manual')
    
    def on_joystick_speed_change(self, new_speed, raw_axis):
        """Handle joystick speed changes - DON'T override manual slider"""
        # REMOVED: self.arousal_scale.set(new_speed)  # Don't move the slider!
    
        # Let joystick control the actual speed
        self.arousal = new_speed
        self.pattern_sequencer.base_speed = new_speed
    
        # Show joystick is controlling speed (but slider stays where user set it)
        self.speed_display_label.config(
            text=f"Joystick Speed: {new_speed:.2f}x (Raw: {raw_axis:+.2f})"
        )
        self.audio_manager.play('speed_change_joystick')
    
    def on_manual_override(self, active, position):
        """Handle manual override"""
        if active:
            self.pattern_sequencer.start_manual_override(position)
            self.audio_manager.play('manual_start')
            self.manual_status_label.config(
                text="🎮 Manual Override: ACTIVE",
                fg='#cc3366'
            )
        else:
            self.pattern_sequencer.end_manual_override()
            self.audio_manager.play('manual_stop')
            self.manual_status_label.config(
                text="♦ Manual Override: Inactive",
                fg='#888888'
            )
        
        self.write_position_status(position * 100 if position is not None else None)
    
    def on_skip_pattern(self):
        """Handle skip pattern"""
        self.pattern_sequencer.skip_to_next_pattern()
        self.audio_manager.play('pattern_skip')
    
    def on_play_pause_button(self):
        """Handle play/pause button"""
        self.toggle_playback()
    
    # Build-up mode methods
    def start_buildup_mode(self):
        """Start build-up mode"""
        try:
            time_input = self.buildup_time_entry.get()
            duration_seconds = int(time_input)
            
            cycles_input = self.buildup_cycles_entry.get().strip()
            cycles = int(cycles_input) if cycles_input.isdigit() else 1
            
            max_speed_input = self.buildup_max_speed_entry.get().strip()
            max_speed = float(max_speed_input)
            
            if duration_seconds < 30 or duration_seconds > 3600:
                raise ValueError("Duration must be between 30 and 3600 seconds")
            if cycles < 1 or cycles > 50:
                raise ValueError("Cycles must be between 1 and 50")
            if max_speed < 0.3 or max_speed > 3.0:
                raise ValueError("Max speed must be between 0.3x and 3.0x")
            
            self.pattern_sequencer.start_buildup_mode(duration_seconds, cycles, 0.1, max_speed)
            self.audio_manager.play('buildup_start')
            
            self.buildup_start_button.config(state='disabled')
            self.buildup_stop_button.config(state='normal')
            
            self.update_buildup_status()
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
    
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
        else:
            self.buildup_status_label.config(text="Build-up: Inactive", fg='#888888')
    
    # Playback control
    def toggle_playback(self):
        """Toggle playback"""
        try:
            if self.running:
                self.stop_playback()
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
            self.play_button.config(text="PAUSE", bg='#ff8844')
            
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
                self.device_client.send_position_command(device_position, duration)
                self.write_position_status(position)
                
                # Update display with ACTUAL speed
                mode_text = "Pattern"
                speed_text = f"{current_speed:.2f}x"
                
                if self.pattern_sequencer.buildup_mode:
                    speed_text += " (Build-up)"
                
                self.root.after(0, lambda: self.pattern_display.config(
                    text=f"Stream: SEAMLESS | Pos: {position} | Mode: {mode_text} | Speed: {speed_text}"
                ))
                
                # FIXED: Ultra-precise timing - NO GAPS
                target_sleep = duration / 1000.0
                
                # Account for actual loop execution time
                loop_time = time.time() - loop_start
                adjusted_sleep = max(0.003, target_sleep - loop_time)  # Minimal floor
                
                time.sleep(adjusted_sleep)
                
            except Exception as e:
                print(f"Streaming error: {e}")
                time.sleep(0.005)  # Quick recovery
                self.audio_manager.play('error_playback')

    def write_position_status(self, position=None):
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

            # NEW: Stroke detection for video switching
            if hasattr(self, 'stroke_enabled') and self.stroke_enabled.get() and position is not None:
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
        """Detect strokes for video switching"""
        try:
            position_change = abs(current_position - self.last_position)
        
            if position_change > self.stroke_threshold:
                self.stroke_count += 1
                print(f"🎬 Stroke detected! Count: {self.stroke_count}")
            
                # Check if we should switch videos
                target_strokes = int(self.stroke_interval_entry.get())
                if self.stroke_count >= target_strokes:
                    self.switch_to_next_video()
                    self.stroke_count = 0  # Reset counter
            
                self.update_stroke_display()
        
            self.last_position = current_position
        
        except Exception as e:
            print(f"Stroke detection error: {e}")

    def switch_to_next_video(self):
        """Switch to next video in gallery"""
        if self.video_gallery.videos:
            if self.video_gallery.next_video():
                self.load_gallery_video()
                print(f"🎬 Auto-switched to next video!")
            else:
                # Loop back to first video
                self.video_gallery.current_index = 0
                self.load_gallery_video()
                print(f"🎬 Auto-switched to first video (looped)!")                
            

    def save_current_video(self):
        """Save current video to gallery"""
        if not hasattr(self.video_visualizer, 'video_path') or not self.video_visualizer.video_path:
            messagebox.showerror("Error", "No video loaded!")
            return
    
        # Get current settings
        direction = self.direction_var.get()
        invert = self.video_invert_var.get()
    
        # Ask for video name
        name = tk.simpledialog.askstring("Save Video", "Enter name for this video:")
        if not name:
            return
    
        # Save to gallery
        if self.video_gallery.add_video(self.video_visualizer.video_path, name, direction, invert):
           self.audio_manager.play('video_loaded')  # Success sound
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

    def load_prev_video(self):
        """Load previous video from gallery"""
        if self.video_gallery.prev_video():
            self.load_gallery_video()

    def load_next_video(self):
        """Load next video from gallery"""
        if self.video_gallery.next_video():
            self.load_gallery_video()

    def prev_gallery_page(self):
        """Go to previous gallery page"""
        if self.video_gallery.prev_gallery_page():
            self.update_gallery_display()

    def next_gallery_page(self):
        """Go to next gallery page"""
        if self.video_gallery.next_gallery_page():
            self.update_gallery_display()

    def load_gallery_video(self):
        """Load the currently selected gallery video"""
        current_video = self.video_gallery.get_current_video()
        if current_video:
            # Load video
            self.video_visualizer.load_video(current_video['file_path'])
        
            # Apply settings
            self.direction_var.set(current_video['direction'])
            self.video_invert_var.set(current_video['invert'])
            self.on_video_direction_change()
        
            # Update UI
            self.current_video_name.config(text=f"{current_video['name']} ({self.video_gallery.current_index + 1}/{len(self.video_gallery.videos)})")
        
            print(f"📹 Loaded: {current_video['name']}")

    def update_gallery_display(self):
        """Update gallery display with actual video thumbnails"""
        visible_videos = self.video_gallery.get_visible_videos()
    
        # Update thumbnail slots with real images
        for i, thumb in enumerate(self.gallery_thumbnails):
            if i < len(visible_videos):
                video = visible_videos[i]
            
                try:
                    # Get thumbnail image - BIGGER SIZE!
                    thumbnail_pil = self.video_gallery.get_thumbnail_image(video['id'], (350, 250))
                    thumbnail_tk = ImageTk.PhotoImage(thumbnail_pil)
                
                    # Update thumbnail display
                    thumb['label'].config(
                        image=thumbnail_tk, 
                        text="",  # Remove text when showing image
                        compound='center'
                    )
                    thumb['label'].image = thumbnail_tk  # Keep reference
                
                    # Update name
                    thumb['name'].config(text=video['name'][:15])
                    thumb['video_id'] = video['id']
                    thumb['frame'].config(bg='#554455')  # Active slot
                
                except Exception as e:
                    print(f"⚠️ Error loading thumbnail for {video['name']}: {e}")
                    # Fallback to text display
                    thumb['label'].config(
                        image="",
                        text=f"📹\n{video['name'][:10]}", 
                        fg='#66ff66'
                    )
                    thumb['name'].config(text=video['name'][:15])
                    thumb['video_id'] = video['id']
                    thumb['frame'].config(bg='#554455')
                
            else:
                # Empty slot
                thumb['label'].config(
                    image="",
                    text=f"Slot {i+1}\nEmpty", 
                    fg='#666666'
                )
                thumb['name'].config(text="")
                thumb['video_id'] = None
                thumb['frame'].config(bg='#440044')
    
        # Update status and buttons (keep existing logic)
        total_videos = len(self.video_gallery.videos)
        current_page = self.video_gallery.gallery_page + 1
        total_pages = (total_videos + 4) // 5
    
        self.gallery_status.config(text=f"Gallery: {total_videos} videos (Page {current_page}/{max(1, total_pages)})")
    
        # Enable/disable buttons
        max_page = (len(self.video_gallery.videos) - 1) // 5 if len(self.video_gallery.videos) > 0 else 0
        
        self.prev_gallery_btn.config(state='normal' if self.video_gallery.gallery_page > 0 else 'disabled')
        self.next_gallery_btn.config(state='normal' if self.video_gallery.gallery_page < max_page else 'disabled')
    
        self.prev_video_btn.config(state='normal' if self.video_gallery.current_index > 0 else 'disabled')
        self.next_video_btn.config(state='normal' if self.video_gallery.current_index < len(self.video_gallery.videos) - 1 else 'disabled')
    
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
                self.stop_button.config(state='normal')
                self.audio_manager.play('device_connect')
            elif connected and not device_found:
                self.connection_label.config(text="● Server Connected, Scanning...", fg='#ff99cc')
                self.status_label.config(text="Server connected, waiting for device...", fg='#ff99cc')
                self.play_button.config(state='disabled')
                self.stop_button.config(state='disabled')
                self.audio_manager.play('device_scanning')
            else:
                self.audio_manager.play('device_disconnect')
                self.connection_label.config(text="● Device: Disconnected", fg='#cc3366')
                self.status_label.config(text="Not connected to server", fg='#cc3366')
                self.play_button.config(state='disabled')
                self.stop_button.config(state='disabled')
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
        self.audio_manager.play('speed_change_joystick')

    def on_manual_override(self, active, position):
        """Handle manual override"""
        if active:
            self.pattern_sequencer.start_manual_override(position)
            self.audio_manager.play('manual_start')
            self.manual_status_label.config(
                text="🎮 Manual Override: ACTIVE",
                fg='#cc3366'
            )
        else:
            self.pattern_sequencer.end_manual_override()
            self.audio_manager.play('manual_stop')
            self.manual_status_label.config(
                text="♦ Manual Override: Inactive",
                fg='#888888'
            )
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
    def load_joystick_config(self):
        """Load joystick config from file - FIXED VERSION"""
        try:
            if not os.path.exists("joystick_config.json"):
                print("ℹ️ No joystick config file found")
                return
            
            with open("joystick_config.json", "r") as f:
                config = json.load(f)
        
            print(f"📋 Loading config: {config}")
        
            # Set detected values
            self.detected_speed_axis = config.get("speed_axis", -1)
            self.detected_manual_axis = config.get("manual_axis", -1)
            self.detected_manual_btn_button = config.get("manual_btn", -1)
            self.detected_skip_button = config.get("skip_btn", -1)
            self.detected_play_pause_button = config.get("play_pause_btn", -1)
        
            # Update UI labels (check if they exist first)
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
        
            # Set enhanced options (check if UI elements exist)
            if hasattr(self, 'speed_invert_var'):
                self.speed_invert_var.set(config.get("speed_invert", False))
            if hasattr(self, 'manual_invert_var'):
                self.manual_invert_var.set(config.get("manual_invert", False))
            if hasattr(self, 'speed_mode_combo'):
                self.speed_mode_combo.set(config.get("speed_mode", "full_range"))
            if hasattr(self, 'manual_mode_combo'):
                self.manual_mode_combo.set(config.get("manual_mode", "full_range"))
        
            print("✅ Config loaded successfully")
        
            # Auto-apply if all controls are detected and UI is ready
            if (all([self.detected_speed_axis >= 0, self.detected_manual_axis >= 0, 
                    self.detected_manual_btn_button >= 0, self.detected_skip_button >= 0, 
                    self.detected_play_pause_button >= 0]) and 
                hasattr(self, 'device_combo')):
            
                # Delay auto-apply to ensure UI is fully ready
                self.root.after(500, self.auto_apply_config)
    
        except Exception as e:
            print(f"⚠️ Error loading joystick config: {e}")
            import traceback
            traceback.print_exc()
            
    def run(self):
        """Start the application"""
        print("Starting AI Pattern Sequencer...")
        try:
            def on_closing():
                self.joystick_controller.stop()
                self.device_client.disconnect()
                self.root.destroy()
            
            self.root.protocol("WM_DELETE_WINDOW", on_closing)
            self.root.mainloop()
        except Exception as e:
            print(f"GUI error: {e}")
            import traceback
            traceback.print_exc()


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
