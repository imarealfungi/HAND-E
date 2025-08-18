"""
Enhanced Session Manager with Multi-Peak Arousal Curves
Supports 1-10 peaks with visual timeline integration
"""

import json
import random
import time
import math
import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages session timing and pattern progression with multi-peak support"""
    
    def __init__(self, pattern_speeds_file: str = "pattern_speeds.json"):
        self.pattern_speeds = {}
        self.session_queue = []
        self.session_length = 0  # seconds
        self.session_start_time = 0
        self.current_arousal = 0.0  # 0-100
        self.target_arousal_curve = []
        self.peaks_count = 3  # NEW: Number of peaks in session
        
        # Load pattern speed data
        self._load_pattern_speeds(pattern_speeds_file)
        
        # Organize patterns by speed class
        self.slow_patterns = []
        self.medium_patterns = []
        self.fast_patterns = []
        self._organize_patterns_by_speed()
    
    def _load_pattern_speeds(self, file_path: str):
        """Load pattern speed analysis data"""
        try:
            with open(file_path, 'r') as f:
                self.pattern_speeds = json.load(f)
            logger.info(f"Loaded speed data for {len(self.pattern_speeds)} patterns")
        except Exception as e:
            logger.error(f"Failed to load pattern speeds: {e}")
            self.pattern_speeds = {}
    
    def _organize_patterns_by_speed(self):
        """Organize patterns into speed categories"""
        for pattern_name, data in self.pattern_speeds.items():
            speed_class = data.get('speed_class', 'medium')
            pattern_info = {
                'name': pattern_name,
                'category': data.get('category', 'bj'),
                'intensity': data.get('intensity', 0.1),
                'speed_class': speed_class
            }
            
            if speed_class == 'slow':
                self.slow_patterns.append(pattern_info)
            elif speed_class == 'fast':
                self.fast_patterns.append(pattern_info)
            else:
                self.medium_patterns.append(pattern_info)
        
        logger.info(f"Organized patterns: {len(self.slow_patterns)} slow, "
                   f"{len(self.medium_patterns)} medium, {len(self.fast_patterns)} fast")
    
    def parse_session_time(self, time_str: str) -> int:
        """Parse session time string (MM:SS, M:SS, :SS) to seconds"""
        try:
            time_str = time_str.strip()
            
            # Handle different formats
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2:
                    minutes = int(parts[0]) if parts[0] else 0
                    seconds = int(parts[1])
                    return minutes * 60 + seconds
                elif len(parts) == 3:  # HH:MM:SS
                    hours = int(parts[0]) if parts[0] else 0
                    minutes = int(parts[1]) if parts[1] else 0
                    seconds = int(parts[2]) if parts[2] else 0
                    return hours * 3600 + minutes * 60 + seconds
            else:
                # Just seconds
                return int(time_str)
        except Exception as e:
            logger.error(f"Failed to parse time '{time_str}': {e}")
            return 300  # Default 5 minutes
    
    def create_multi_peak_arousal_curve(self, session_length: int, peaks: int) -> List[float]:
        """Create multi-peak arousal progression curve"""
        peaks = max(1, min(10, peaks))  # Clamp to 1-10 peaks
        curve_points = max(20, session_length // 15)  # Point every 15 seconds, minimum 20 points
        curve = []
        
        logger.info(f"Creating {peaks}-peak arousal curve with {curve_points} points")
        
        for i in range(curve_points):
            progress = i / (curve_points - 1)  # 0 to 1
            
            # Base arousal level (gradual increase over session)
            base_arousal = 20 + (progress * 30)  # 20-50 base level
            
            # Calculate wave component based on peaks
            wave_frequency = peaks * math.pi * 2  # Full cycles over session
            wave_amplitude = 35 + (progress * 20)  # Increasing amplitude over time
            
            # Create wave pattern
            wave_component = math.sin(progress * wave_frequency) * wave_amplitude
            
            # Combine base and wave
            arousal = base_arousal + (wave_component * 0.5)  # Reduce wave intensity
            
            # Add some controlled randomness
            noise = random.uniform(-3, 3)
            arousal += noise
            
            # Ensure peaks get progressively more intense
            if peaks > 1:
                peak_progress = (progress * peaks) % 1.0
                if peak_progress > 0.7:  # Near peak
                    peak_bonus = (progress * 20) + 10  # Later peaks are more intense
                    arousal += peak_bonus * (peak_progress - 0.7) / 0.3
            
            # Clamp to valid range
            arousal = max(10, min(95, arousal))
            curve.append(arousal)
        
        # Ensure curve starts low and has proper peaks
        curve[0] = random.uniform(15, 25)  # Always start low
        
        # Smooth the curve slightly
        smoothed_curve = []
        for i in range(len(curve)):
            if i == 0 or i == len(curve) - 1:
                smoothed_curve.append(curve[i])
            else:
                # Simple moving average
                avg = (curve[i-1] + curve[i] + curve[i+1]) / 3
                smoothed_curve.append(avg)
        
        return smoothed_curve
    
    def get_target_arousal(self, elapsed_time: int) -> float:
        """Get target arousal for current time in session"""
        if not self.target_arousal_curve or self.session_length == 0:
            return 50.0
        
        # Calculate progress through session
        progress = min(1.0, elapsed_time / self.session_length)
        curve_index = int(progress * (len(self.target_arousal_curve) - 1))
        
        return self.target_arousal_curve[curve_index]
    
    def select_pattern_by_arousal(self, target_arousal: float, current_pos: int = 0) -> Optional[Dict]:
        """Select appropriate pattern based on target arousal level"""
        # Map arousal to speed preference
        if target_arousal < 30:
            # Low arousal - prefer slow patterns
            pattern_pool = self.slow_patterns + (self.medium_patterns[:len(self.medium_patterns)//3])
        elif target_arousal < 70:
            # Medium arousal - prefer medium patterns
            pattern_pool = self.medium_patterns + (self.slow_patterns[:len(self.slow_patterns)//3]) + (self.fast_patterns[:len(self.fast_patterns)//3])
        else:
            # High arousal - prefer fast patterns
            pattern_pool = self.fast_patterns + (self.medium_patterns[:len(self.medium_patterns)//2])
        
        if not pattern_pool:
            pattern_pool = self.medium_patterns  # Fallback
        
        return random.choice(pattern_pool) if pattern_pool else None
    
    def calculate_speed_multiplier(self, current_arousal: float, target_arousal: float) -> float:
        """Calculate speed multiplier based on arousal levels"""
        # Base multiplier from target arousal
        if target_arousal < 25:
            base_multiplier = 2.0  # Very slow for low arousal
        elif target_arousal < 40:
            base_multiplier = 1.5  # Slow for low-medium arousal
        elif target_arousal < 60:
            base_multiplier = 1.0  # Normal for medium arousal
        elif target_arousal < 80:
            base_multiplier = 0.8  # Faster for high arousal
        else:
            base_multiplier = 0.6  # Very fast for peak arousal
        
        # Fine-tune based on difference between current and target
        arousal_diff = target_arousal - current_arousal
        if arousal_diff > 15:
            base_multiplier *= 0.9  # Speed up to catch up
        elif arousal_diff < -15:
            base_multiplier *= 1.2  # Slow down to reduce arousal
        
        # Clamp to reasonable range
        return max(0.4, min(3.0, base_multiplier))
    
    def start_session(self, session_time_str: str) -> bool:
        """Start a new session with given time and peaks"""
        try:
            self.session_length = self.parse_session_time(session_time_str)
            self.session_start_time = time.time()
            self.current_arousal = 0.0
            
            # Create multi-peak arousal progression curve
            self.target_arousal_curve = self.create_multi_peak_arousal_curve(
                self.session_length, self.peaks_count
            )
            
            logger.info(f"Started session: {self.session_length}s ({session_time_str}) with {self.peaks_count} peaks")
            logger.info(f"Arousal curve: {len(self.target_arousal_curve)} points, peaks at ~{[i for i, v in enumerate(self.target_arousal_curve) if v > 70]}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            return False
    
    def get_session_progress(self) -> Tuple[int, int, float]:
        """Get current session progress"""
        if self.session_start_time == 0:
            return 0, 0, 0.0
        
        elapsed = int(time.time() - self.session_start_time)
        remaining = max(0, self.session_length - elapsed)
        progress = min(1.0, elapsed / self.session_length) if self.session_length > 0 else 0.0
        
        return elapsed, remaining, progress
    
    def update_arousal(self, new_arousal: float):
        """Update current arousal level"""
        self.current_arousal = max(0, min(100, new_arousal))
    
    def manual_arousal_override(self, position: float):
        """Override arousal position manually (0.0 to 1.0)"""
        if self.session_length > 0:
            # Calculate what time this position represents
            target_time = position * self.session_length
            
            # Override session start time to make current time = target time
            self.session_start_time = time.time() - target_time
            
            # Update arousal to match position
            if self.target_arousal_curve:
                curve_index = int(position * (len(self.target_arousal_curve) - 1))
                target_arousal = self.target_arousal_curve[curve_index]
                self.update_arousal(target_arousal)
                
                logger.info(f"Manual override: position {position:.2f} -> time {target_time:.0f}s -> arousal {target_arousal:.1f}%")
    
    def get_next_pattern_recommendation(self, current_pos: int = 0) -> Tuple[Optional[Dict], float]:
        """Get next pattern recommendation and speed multiplier"""
        elapsed, remaining, progress = self.get_session_progress()
        
        if remaining <= 0 and self.session_length > 0:
            return None, 1.0  # Session ended
        
        # Get target arousal for current time
        target_arousal = self.get_target_arousal(elapsed)
        
        # Select appropriate pattern
        pattern = self.select_pattern_by_arousal(target_arousal, current_pos)
        
        # Calculate speed multiplier
        speed_multiplier = self.calculate_speed_multiplier(self.current_arousal, target_arousal)
        
        return pattern, speed_multiplier
    
    def is_session_active(self) -> bool:
        """Check if session is currently active"""
        if self.session_start_time == 0:
            return False
        
        elapsed = time.time() - self.session_start_time
        return elapsed < self.session_length
    
    def stop_session(self):
        """Stop current session"""
        self.session_start_time = 0
        self.session_length = 0
        self.current_arousal = 0.0
        self.target_arousal_curve = []
        logger.info("Session stopped")

# Test function
def test_multi_peak_session():
    """Test the multi-peak session manager"""
    sm = SessionManager()
    
    print("Testing multi-peak session manager...")
    
    # Test different peak counts
    for peaks in [1, 3, 5]:
        print(f"\n=== Testing {peaks} peaks ===")
        sm.peaks_count = peaks
        sm.start_session("2:00")  # 2 minutes
        
        # Show curve preview
        curve = sm.target_arousal_curve
        print(f"Curve length: {len(curve)}")
        print(f"Peak positions: {[i for i, v in enumerate(curve) if v > 70]}")
        print(f"Arousal range: {min(curve):.1f} - {max(curve):.1f}")
        
        # Simulate a few time points
        for i in range(0, 120, 30):  # Every 30 seconds
            sm.session_start_time = time.time() - i
            target = sm.get_target_arousal(i)
            pattern, speed = sm.get_next_pattern_recommendation()
            
            print(f"  {i}s: Target {target:.1f}%, Speed {speed:.2f}x, Pattern: {pattern['speed_class'] if pattern else 'None'}")

if __name__ == "__main__":
    test_multi_peak_session()