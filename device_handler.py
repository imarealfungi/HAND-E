import json
import os
import random
import threading
import time
import logging
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FunscriptPattern:
    """Class to handle individual funscript pattern data"""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.name = os.path.basename(file_path)
        self.actions = []
        self.duration = 0
        self.start_pos = 0
        self.end_pos = 0
        self.load_pattern()
    
    def load_pattern(self):
        """Load and parse funscript data from file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.actions = data.get('actions', [])
                
                if self.actions:
                    self.duration = self.actions[-1]['at']
                    self.start_pos = self.actions[0]['pos']
                    self.end_pos = self.actions[-1]['pos']
                    
                logger.info(f"Loaded pattern: {self.name} ({len(self.actions)} actions, "
                           f"{self.start_pos}->{self.end_pos}, {self.duration}ms)")
                
        except Exception as e:
            logger.error(f"Error loading pattern {self.file_path}: {e}")

class PatternManager:
    """Manages loading and categorizing funscript patterns"""
    def __init__(self, funscript_folder: str):
        self.funscript_folder = funscript_folder
        self.main_patterns_0_to_0 = []
        self.main_patterns_100_to_100 = []
        self.main_patterns_50_to_50 = []  # NEW: Twerk patterns
        self.transitions_0_to_100 = []
        self.transitions_100_to_0 = []
        self.transitions_50_to_0 = []   # NEW: Twerk to deep
        self.transitions_50_to_100 = [] # NEW: Twerk to surface
        self.transitions_0_to_50 = []   # NEW: Deep to twerk
        self.transitions_100_to_50 = [] # NEW: Surface to twerk
        self.load_all_patterns()
    
    def load_all_patterns(self):
        """Load and categorize all patterns from folders"""
        logger.info(f"Loading patterns from: {self.funscript_folder}")
        
        # Load main BJ patterns
        bj_folder = os.path.join(self.funscript_folder, 'bj')
        if os.path.exists(bj_folder):
            self._load_patterns_from_folder(bj_folder, is_transition=False)
        
        # Load transition patterns
        transitions_folder = os.path.join(self.funscript_folder, 'transitions')
        if os.path.exists(transitions_folder):
            self._load_patterns_from_folder(transitions_folder, is_transition=True)
        
        # Load twerk patterns (50->50) directly from root folder or twerk subfolder
        twerk_folder = os.path.join(self.funscript_folder, 'twerk')
        if os.path.exists(twerk_folder):
            self._load_patterns_from_folder(twerk_folder, is_transition=False)
        else:
            # Also check root folder for 50-50 patterns
            self._load_patterns_from_folder(self.funscript_folder, is_transition=False)
        
        self._log_pattern_summary()
    
    def _load_patterns_from_folder(self, folder_path: str, is_transition: bool):
        """Load patterns from specific folder and categorize them"""
        for filename in os.listdir(folder_path):
            if filename.lower().endswith('.funscript'):
                file_path = os.path.join(folder_path, filename)
                pattern = FunscriptPattern(file_path)
                
                if pattern.actions:  # Only add valid patterns
                    self._categorize_pattern(pattern, is_transition)
    
    def _categorize_pattern(self, pattern: FunscriptPattern, is_transition: bool):
        """Categorize pattern based on start/end positions with relaxed thresholds"""
        
        # DEBUG: Log every pattern's actual positions
        logger.info(f"DEBUG: {pattern.name} -> start:{pattern.start_pos} end:{pattern.end_pos}")
        
        # RELAXED THRESHOLDS - More flexible position ranges
        start_deep = pattern.start_pos <= 30      # Was <=10, now <=30
        end_deep = pattern.end_pos <= 30          # Was <=10, now <=30
        start_shallow = pattern.start_pos >= 70   # Was >=90, now >=70
        end_shallow = pattern.end_pos >= 70       # Was >=90, now >=70
        start_mid = 35 <= pattern.start_pos <= 65 # Slightly wider range for twerk
        end_mid = 35 <= pattern.end_pos <= 65     # Slightly wider range for twerk
        
        if is_transition:
            # Transition patterns: start != end
            if start_deep and end_shallow:
                self.transitions_0_to_100.append(pattern)
                logger.info(f"Categorized {pattern.name} as transition 0->100")
            elif start_shallow and end_deep:
                self.transitions_100_to_0.append(pattern)
                logger.info(f"Categorized {pattern.name} as transition 100->0")
            elif start_mid and end_deep:
                self.transitions_50_to_0.append(pattern)
                logger.info(f"Categorized {pattern.name} as transition 50->0")
            elif start_mid and end_shallow:
                self.transitions_50_to_100.append(pattern)
                logger.info(f"Categorized {pattern.name} as transition 50->100")
            elif start_deep and end_mid:
                self.transitions_0_to_50.append(pattern)
                logger.info(f"Categorized {pattern.name} as transition 0->50")
            elif start_shallow and end_mid:
                self.transitions_100_to_50.append(pattern)
                logger.info(f"Categorized {pattern.name} as transition 100->50")
            else:
                logger.warning(f"Uncategorized transition pattern {pattern.name}: {pattern.start_pos}→{pattern.end_pos}")
        else:
            # Main patterns: start ≈ end (allow some variance)
            position_diff = abs(pattern.start_pos - pattern.end_pos)
            
            if start_deep and end_deep and position_diff <= 20:  # Allow 20 position variance
                self.main_patterns_0_to_0.append(pattern)
                logger.info(f"Categorized {pattern.name} as main 0->0")
            elif start_shallow and end_shallow and position_diff <= 20:
                self.main_patterns_100_to_100.append(pattern)
                logger.info(f"Categorized {pattern.name} as main 100->100")
            elif start_mid and end_mid and position_diff <= 20:
                self.main_patterns_50_to_50.append(pattern)
                logger.info(f"Categorized {pattern.name} as main 50->50 (twerk)")
            else:
                # FALLBACK: If pattern doesn't fit strict categories, guess based on average position
                avg_pos = (pattern.start_pos + pattern.end_pos) / 2
                if avg_pos <= 35:
                    self.main_patterns_0_to_0.append(pattern)
                    logger.info(f"Categorized {pattern.name} as main 0->0 (fallback - avg pos {avg_pos:.1f})")
                elif avg_pos >= 65:
                    self.main_patterns_100_to_100.append(pattern)
                    logger.info(f"Categorized {pattern.name} as main 100->100 (fallback - avg pos {avg_pos:.1f})")
                else:
                    self.main_patterns_50_to_50.append(pattern)
                    logger.info(f"Categorized {pattern.name} as main 50->50 (fallback - avg pos {avg_pos:.1f})")
    
    def _log_pattern_summary(self):
        """Log summary of loaded patterns"""
        logger.info(f"Pattern Summary:")
        logger.info(f"  Main 0->0: {len(self.main_patterns_0_to_0)} patterns")
        logger.info(f"  Main 100->100: {len(self.main_patterns_100_to_100)} patterns")
        logger.info(f"  Main 50->50 (Twerk): {len(self.main_patterns_50_to_50)} patterns")  # NEW
        logger.info(f"  Transitions 0->100: {len(self.transitions_0_to_100)} patterns")
        logger.info(f"  Transitions 100->0: {len(self.transitions_100_to_0)} patterns")
        logger.info(f"  Transitions 50->0: {len(self.transitions_50_to_0)} patterns")      # NEW
        logger.info(f"  Transitions 50->100: {len(self.transitions_50_to_100)} patterns")  # NEW
        logger.info(f"  Transitions 0->50: {len(self.transitions_0_to_50)} patterns")      # NEW
        logger.info(f"  Transitions 100->50: {len(self.transitions_100_to_50)} patterns")  # NEW
    
    def get_patterns(self):
        """Get patterns organized by category"""
        return {
            'main_0_to_0': self.main_patterns_0_to_0,
            'main_100_to_100': self.main_patterns_100_to_100,
            'main_50_to_50': self.main_patterns_50_to_50,
            'transitions_0_to_100': self.transitions_0_to_100,
            'transitions_100_to_0': self.transitions_100_to_0,
            'transitions_50_to_0': self.transitions_50_to_0,
            'transitions_50_to_100': self.transitions_50_to_100,
            'transitions_0_to_50': self.transitions_0_to_50,
            'transitions_100_to_50': self.transitions_100_to_50
        }

    def set_patterns(self, pattern_dict):
        """Set patterns from dictionary"""
        self.main_patterns_0_to_0 = pattern_dict.get('main_0_to_0', [])
        self.main_patterns_100_to_100 = pattern_dict.get('main_100_to_100', [])
        self.main_patterns_50_to_50 = pattern_dict.get('main_50_to_50', [])
        self.transitions_0_to_100 = pattern_dict.get('transitions_0_to_100', [])
        self.transitions_100_to_0 = pattern_dict.get('transitions_100_to_0', [])
        self.transitions_50_to_0 = pattern_dict.get('transitions_50_to_0', [])
        self.transitions_50_to_100 = pattern_dict.get('transitions_50_to_100', [])
        self.transitions_0_to_50 = pattern_dict.get('transitions_0_to_50', [])
        self.transitions_100_to_50 = pattern_dict.get('transitions_100_to_50', [])
    
    def get_all_patterns(self):
        """Get all patterns combined"""
        return (
            self.main_patterns_0_to_0 +
            self.main_patterns_100_to_100 +
            self.main_patterns_50_to_50 +      # NEW
            self.transitions_0_to_100 +
            self.transitions_100_to_0 +
            self.transitions_50_to_0 +         # NEW
            self.transitions_50_to_100 +       # NEW
            self.transitions_0_to_50 +         # NEW
            self.transitions_100_to_50         # NEW
        )
    
    def find_pattern_by_name(self, pattern_name: str):
        """Find pattern by filename"""
        for pattern in self.get_all_patterns():
            if pattern.name == pattern_name:
                return pattern
        return None
    
    def get_total_count(self):
        """Get total pattern count"""
        return len(self.get_all_patterns())

class IntifaceClient:
    """Handles HTTP communication with C# Buttplug Server"""
    def __init__(self, url: str = "http://localhost:8080"):
        self.url = url
        self.connected = False
        self.device_connected = False
        self.connection_callback = None
        self.session = None
        self.check_thread = None
        self.should_check = False
    
    def set_connection_callback(self, callback):
        """Set callback for connection status changes"""
        self.connection_callback = callback
    
    def connect(self):
        """Connect to C# Buttplug Server"""
        try:
            import requests
            self.session = requests.Session()
            self.session.timeout = 5
            
            logger.info(f"Connecting to C# Buttplug Server at {self.url}")
            
            response = self.session.post(f"{self.url}/connect")
            if response.status_code == 200:
                result = response.json()
                self.connected = True
                self.device_connected = result.get('device_connected', False)
                self._update_connection_status(True, self.device_connected)
                
                self._start_status_checking()
                logger.info("Connected to C# Buttplug Server")
            else:
                logger.error(f"Failed to connect: HTTP {response.status_code}")
                self._update_connection_status(False)
                
        except ImportError:
            logger.error("requests library not installed. Installing...")
            import subprocess
            subprocess.run(["pip", "install", "requests"])
            self.connect()
        except Exception as e:
            logger.error(f"Failed to connect to C# server: {e}")
            self._update_connection_status(False)
    
    def disconnect(self):
        """Disconnect from C# server"""
        self.should_check = False
        if self.session:
            try:
                self.session.post(f"{self.url}/disconnect")
            except:
                pass
        self.connected = False
        self.device_connected = False
        self._update_connection_status(False)
    
    def _start_status_checking(self):
        """Start periodic status checking"""
        self.should_check = True
        if not self.check_thread or not self.check_thread.is_alive():
            self.check_thread = threading.Thread(target=self._check_status_loop)
            self.check_thread.daemon = True
            self.check_thread.start()
    
    def _check_status_loop(self):
        """Periodically check connection status"""
        while self.should_check:
            try:
                if self.session:
                    response = self.session.get(f"{self.url}/status")
                    if response.status_code == 200:
                        status = response.json()
                        old_device_status = self.device_connected
                        self.device_connected = status.get('device_connected', False)
                        
                        if old_device_status != self.device_connected:
                            self._update_connection_status(True, self.device_connected)
                    else:
                        self.connected = False
                        self.device_connected = False
                        self._update_connection_status(False)
                        break
                        
            except Exception as e:
                logger.error(f"Status check failed: {e}")
                self.connected = False
                self.device_connected = False
                self._update_connection_status(False)
                break
            
            time.sleep(2)
    
    def _update_connection_status(self, connected: bool, device_found: bool = False):
        """Update connection status"""
        self.connected = connected
        self.device_connected = device_found
        if self.connection_callback:
            self.connection_callback(connected, device_found)
    
    def send_position_command(self, position: float, duration: int):
        """Send position command to The Handy via C# server"""
        if not self.connected or not self.session:
            logger.warning("Cannot send command: not connected to C# server")
            return
        
        # Apply position rounding fix for smoother motion
        position = round(max(0.0, min(1.0, position)), 2)
        
        try:
            command = {
                "command": "move",
                "position": position,
                "duration": duration
            }
            
            response = self.session.post(f"{self.url}/command", json=command)
            if response.status_code != 200:
                logger.error(f"Command failed: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
    
    def send_stop_command(self):
        """Send stop command (go to position 0)"""
        if not self.connected or not self.session:
            return
            
        try:
            command = {"command": "stop"}
            self.session.post(f"{self.url}/command", json=command)
        except Exception as e:
            logger.error(f"Failed to send stop command: {e}")

class PlaybackEngine:
    """Handles pattern playback logic with smart chaining and session integration"""
    def __init__(self, pattern_manager: PatternManager, device_client: IntifaceClient):
        self.pattern_manager = pattern_manager
        self.device_client = device_client
        self.is_playing = False
        self.playback_thread = None
        self.min_range = 0
        self.max_range = 100
        self.slow_mode = False
        self.twerk_mode = False  # NEW: Twerk mode flag
        self.speed_multiplier = 1.0  # NEW: Global speed multiplier (0.25x to 2.0x)
        
        # Smart chaining variables
        self.current_pattern = None
        self.next_pattern = None
        self.current_position = 0  # Track current endpoint (0, 50, or 100)
        
        # Session integration
        self.session_manager = None  # NEW: Set by GUI
        self.dynamic_speed_multiplier = 1.0  # NEW: From session manager
    
    def set_range(self, min_range: int, max_range: int):
        """Set position range limits"""
        self.min_range = min_range
        self.max_range = max_range
    
    def set_slow_mode(self, slow_mode: bool):
        """Set slow mode on/off"""
        self.slow_mode = slow_mode
    
    def set_speed_multiplier(self, multiplier: float):
        """Set global speed multiplier (0.25x to 2.0x)"""
        self.speed_multiplier = multiplier
        logger.info(f"Global speed multiplier set to {multiplier:.2f}x")
    
    def start_playback(self):
        """Start pattern playback with look-ahead"""
        if not self.pattern_manager or not self.device_client.connected:
            return False
        
        # Pick first pattern (start at depth or twerk position)
        self.current_position = 0
        self.current_pattern = self._select_pattern_for_position(0)
        if not self.current_pattern:
            logger.error("No patterns available to start playback")
            return False
        
        # Immediately select next pattern based on where current will end
        self.next_pattern = self._select_pattern_for_position(self.current_pattern.end_pos)
        
        self.is_playing = True
        self.playback_thread = threading.Thread(target=self._playback_loop)
        self.playback_thread.daemon = True
        self.playback_thread.start()
        
        logger.info(f"Started smart chaining playback. First: {self.current_pattern.name} (ends at {self.current_pattern.end_pos})")
        if self.next_pattern:
            logger.info(f"Next pattern ready: {self.next_pattern.name}")
        return True
    
    def stop_playback(self):
        """Stop pattern playback"""
        self.is_playing = False
        if self.device_client.connected and self.device_client.device_connected:
            self.device_client.send_position_command(0.0, 1000)
        logger.info("Stopped playback")
    
    def emergency_stop(self):
        """Emergency stop"""
        logger.info("EMERGENCY STOP - Going to full depth")
        self.is_playing = False
        if self.device_client.connected and self.device_client.device_connected:
            self.device_client.send_position_command(0.0, 500)
        logger.info("Emergency stop complete")
    
    def _playback_loop(self):
        """Main playback loop with seamless pattern chaining"""
        while self.is_playing and self.current_pattern:
            # Play current pattern
            self._play_pattern(self.current_pattern)
            
            if not self.is_playing:
                break
            
            # Seamless transition to next pattern
            logger.info(f"Seamless transition: {self.current_pattern.name} -> {self.next_pattern.name if self.next_pattern else 'None'}")
            
            # Move to next pattern
            self.current_position = self.current_pattern.end_pos
            self.current_pattern = self.next_pattern
            
            # Look ahead - select pattern after next
            if self.current_pattern:
                self.next_pattern = self._select_pattern_for_position(self.current_pattern.end_pos)
            else:
                # No more patterns available
                break
    
    def _select_pattern_for_position(self, current_pos):
        """Select next pattern based on current position with session manager integration"""
        if not self.pattern_manager:
            return None
        
        # NEW: Use session manager if available
        if self.session_manager and self.session_manager.is_session_active():
            pattern_rec, speed_mult = self.session_manager.get_next_pattern_recommendation(current_pos)
            if pattern_rec:
                # Apply speed multiplier
                self.dynamic_speed_multiplier = speed_mult
                
                # Find actual pattern object from recommendation
                selected = self.pattern_manager.find_pattern_by_name(pattern_rec['name'])
                if selected:
                    logger.info(f"Session selected: {selected.name} (speed: {speed_mult:.2f}x)")
                    return selected
                else:
                    logger.warning(f"Session recommended pattern not found: {pattern_rec['name']}")
        
        # Fallback to original random selection logic
        return self._select_pattern_random(current_pos)
    
    def _select_pattern_random(self, current_pos):
        """Original random pattern selection logic with twerk mode support"""
        # NEW: If twerk mode is on, heavily favor twerk patterns
        if self.twerk_mode and self.pattern_manager.main_patterns_50_to_50:
            rand = random.random()
            if rand < 0.8:  # 80% chance to use twerk patterns in twerk mode
                selected = random.choice(self.pattern_manager.main_patterns_50_to_50)
                logger.info(f"Twerk mode: Selected twerk pattern 50->50: {selected.name}")
                return selected
        
        # Determine position type
        at_depth = current_pos <= 10
        at_surface = current_pos >= 90
        at_mid = 40 <= current_pos <= 60  # Twerk position
        
        if at_depth:
            # At depth - can stay with 0->0, transition to surface, or go to twerk
            available_same = self.pattern_manager.main_patterns_0_to_0
            available_to_surface = self.pattern_manager.transitions_0_to_100
            available_to_twerk = self.pattern_manager.transitions_0_to_50
            
            # Random selection with weights (modified for twerk mode)
            rand = random.random()
            twerk_chance = 0.3 if self.twerk_mode else 0.1  # Higher chance in twerk mode
            
            if available_to_twerk and rand < twerk_chance:
                selected = random.choice(available_to_twerk)
                logger.info(f"Selected transition 0->50: {selected.name}")
                return selected
            elif available_to_surface and rand < (twerk_chance + 0.2):
                selected = random.choice(available_to_surface)
                logger.info(f"Selected transition 0->100: {selected.name}")
                return selected
            elif available_same:
                selected = random.choice(available_same)
                logger.info(f"Selected depth pattern 0->0: {selected.name}")
                return selected
                
        elif at_surface:
            # At surface - can stay with 100->100, transition to depth, or go to twerk
            available_same = self.pattern_manager.main_patterns_100_to_100
            available_to_depth = self.pattern_manager.transitions_100_to_0
            available_to_twerk = self.pattern_manager.transitions_100_to_50
            
            # Random selection with weights (modified for twerk mode)
            rand = random.random()
            twerk_chance = 0.3 if self.twerk_mode else 0.1
            
            if available_to_twerk and rand < twerk_chance:
                selected = random.choice(available_to_twerk)
                logger.info(f"Selected transition 100->50: {selected.name}")
                return selected
            elif available_to_depth and rand < (twerk_chance + 0.2):
                selected = random.choice(available_to_depth)
                logger.info(f"Selected transition 100->0: {selected.name}")
                return selected
            elif available_same:
                selected = random.choice(available_same)
                logger.info(f"Selected surface pattern 100->100: {selected.name}")
                return selected
                
        elif at_mid:  # At twerk position
            # At twerk - can stay with 50->50, go to depth, or go to surface
            available_same = self.pattern_manager.main_patterns_50_to_50
            available_to_depth = self.pattern_manager.transitions_50_to_0
            available_to_surface = self.pattern_manager.transitions_50_to_100
            
            # Random selection with weights (heavily favor staying in twerk mode)
            rand = random.random()
            stay_chance = 0.8 if self.twerk_mode else 0.6  # Much higher chance to stay in twerk mode
            
            if available_same and rand < stay_chance:
                selected = random.choice(available_same)
                logger.info(f"Selected twerk pattern 50->50: {selected.name}")
                return selected
            elif available_to_depth and rand < (stay_chance + 0.1):
                selected = random.choice(available_to_depth)
                logger.info(f"Selected transition 50->0: {selected.name}")
                return selected
            elif available_to_surface:
                selected = random.choice(available_to_surface)
                logger.info(f"Selected transition 50->100: {selected.name}")
                return selected
        
        # Fallback - pick any available pattern
        all_patterns = self.pattern_manager.get_all_patterns()
        if all_patterns:
            selected = random.choice(all_patterns)
            logger.warning(f"Fallback pattern selection: {selected.name}")
            return selected
        
        return None
    
    def _play_pattern(self, pattern):
        """Play a single funscript pattern"""
        if not pattern:
            return
            
        logger.info(f"Playing pattern: {pattern.name} ({pattern.start_pos}->{pattern.end_pos}) at {self.speed_multiplier:.2f}x speed")
        start_time = time.time()
        
        for action_index, action in enumerate(pattern.actions):
            if not self.is_playing:
                break
                
            # Calculate timing
            target_time = start_time + (action['at'] / 1000.0)
            current_time = time.time()
            
            # Wait until it's time for this action
            if target_time > current_time:
                time.sleep(target_time - current_time)
            
            # Apply range clamping and send command
            position = action['pos'] / 100.0
            clamped_position = self._apply_range_clamp(position)
            
            # Calculate duration with all speed controls
            if action_index < len(pattern.actions) - 1:
                next_action = pattern.actions[action_index + 1]
                duration = next_action['at'] - action['at']
                
                # Apply all speed multipliers:
                # 1. Manual slow mode (1.5x slower)
                # 2. Dynamic session speed (from session manager)
                # 3. Global speed multiplier (from GUI slider 0.25x to 2.0x)
                speed_mult = 1.5 if self.slow_mode else 1.0
                speed_mult *= self.dynamic_speed_multiplier
                speed_mult *= self.speed_multiplier  # NEW: Apply global speed control
                duration = int(duration * speed_mult)
            else:
                duration = 500
            
            self.device_client.send_position_command(clamped_position, duration)
    
    def _apply_range_clamp(self, position):
        """Apply min/max range clamping to position"""
        range_size = self.max_range - self.min_range
        clamped = self.min_range + (position * range_size)
        return clamped / 100.0
