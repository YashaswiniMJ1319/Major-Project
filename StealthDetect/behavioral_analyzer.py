import numpy as np
import logging
from datetime import datetime

class BehavioralAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_patterns(self, behavioral_data):
        """Analyze behavioral patterns and extract key metrics"""
        metrics = {}
        
        try:
            # Analyze mouse movements
            mouse_metrics = self._analyze_mouse_movements(
                behavioral_data.get('mouse_movements', [])
            )
            metrics.update(mouse_metrics)
            
            # Analyze click patterns
            click_metrics = self._analyze_click_patterns(
                behavioral_data.get('click_patterns', [])
            )
            metrics.update(click_metrics)
            
            # Analyze keystroke patterns
            keystroke_metrics = self._analyze_keystroke_patterns(
                behavioral_data.get('keystroke_patterns', [])
            )
            metrics.update(keystroke_metrics)
            
            # Analyze scroll patterns
            scroll_metrics = self._analyze_scroll_patterns(
                behavioral_data.get('scroll_patterns', [])
            )
            metrics.update(scroll_metrics)
            
        except Exception as e:
            self.logger.error(f"Error analyzing behavioral patterns: {str(e)}")
        
        return metrics
    
    def _analyze_mouse_movements(self, mouse_movements):
        """Analyze mouse movement patterns"""
        if not mouse_movements or len(mouse_movements) < 2:
            return {
                'mouse_velocity_avg': 0,
                'mouse_velocity_std': 0,
                'mouse_trajectory_smoothness': 0,
                'mouse_pause_frequency': 0
            }
        
        velocities = []
        direction_changes = 0
        pauses = 0
        
        for i in range(1, len(mouse_movements)):
            prev = mouse_movements[i-1]
            curr = mouse_movements[i]
            
            # Calculate time difference in seconds
            time_diff = (curr['timestamp'] - prev['timestamp']) / 1000.0
            
            if time_diff > 0:
                # Calculate distance and velocity
                distance = np.sqrt(
                    (curr['x'] - prev['x'])**2 + (curr['y'] - prev['y'])**2
                )
                velocity = distance / time_diff
                velocities.append(velocity)
                
                # Detect pauses (very low velocity)
                if velocity < 10:  # pixels per second
                    pauses += 1
                
                # Detect direction changes (simplified)
                if i >= 2:
                    prev_prev = mouse_movements[i-2]
                    
                    # Calculate angles
                    angle1 = np.arctan2(
                        prev['y'] - prev_prev['y'],
                        prev['x'] - prev_prev['x']
                    )
                    angle2 = np.arctan2(
                        curr['y'] - prev['y'],
                        curr['x'] - prev['x']
                    )
                    
                    angle_diff = abs(angle2 - angle1)
                    if angle_diff > np.pi:
                        angle_diff = 2 * np.pi - angle_diff
                    
                    # Consider it a direction change if angle > 45 degrees
                    if angle_diff > np.pi / 4:
                        direction_changes += 1
        
        # Calculate metrics
        velocity_avg = np.mean(velocities) if velocities else 0
        velocity_std = np.std(velocities) if velocities else 0
        
        # Trajectory smoothness (inverse of direction changes per movement)
        smoothness = 1.0 - (direction_changes / len(mouse_movements)) if len(mouse_movements) > 0 else 0
        
        # Pause frequency
        pause_frequency = pauses / len(mouse_movements) if len(mouse_movements) > 0 else 0
        
        return {
            'mouse_velocity_avg': float(velocity_avg),
            'mouse_velocity_std': float(velocity_std),
            'mouse_trajectory_smoothness': float(smoothness),
            'mouse_pause_frequency': float(pause_frequency)
        }
    
    def _analyze_click_patterns(self, click_patterns):
        """Analyze click patterns for bot-like behavior"""
        if not click_patterns or len(click_patterns) < 2:
            return {
                'click_frequency': 0,
                'click_rhythm_consistency': 0,
                'click_spatial_distribution': 0
            }
        
        # Calculate intervals between clicks
        intervals = []
        positions = []
        
        for i in range(1, len(click_patterns)):
            interval = (click_patterns[i]['timestamp'] - click_patterns[i-1]['timestamp']) / 1000.0
            intervals.append(interval)
            positions.append((click_patterns[i]['x'], click_patterns[i]['y']))
        
        # Click frequency (clicks per second)
        total_time = (click_patterns[-1]['timestamp'] - click_patterns[0]['timestamp']) / 1000.0
        frequency = len(click_patterns) / total_time if total_time > 0 else 0
        
        # Rhythm consistency (lower std indicates more bot-like)
        rhythm_consistency = 1.0 / (1.0 + np.std(intervals)) if intervals else 0
        
        # Spatial distribution (measure of click position variance)
        if positions:
            x_coords = [pos[0] for pos in positions]
            y_coords = [pos[1] for pos in positions]
            spatial_variance = np.std(x_coords) + np.std(y_coords)
            spatial_distribution = min(1.0, spatial_variance / 1000.0)  # Normalized
        else:
            spatial_distribution = 0
        
        return {
            'click_frequency': float(frequency),
            'click_rhythm_consistency': float(rhythm_consistency),
            'click_spatial_distribution': float(spatial_distribution)
        }
    
    def _analyze_keystroke_patterns(self, keystroke_patterns):
        """Analyze typing patterns for human-like behavior"""
        if not keystroke_patterns or len(keystroke_patterns) < 2:
            return {
                'typing_rhythm_consistency': 0,
                'typing_speed': 0,
                'key_dwell_variance': 0
            }
        
        # Extract dwell times and flight times
        dwell_times = [k.get('duration', 0) for k in keystroke_patterns]
        
        flight_times = []
        for i in range(1, len(keystroke_patterns)):
            flight_time = keystroke_patterns[i]['timestamp'] - keystroke_patterns[i-1]['timestamp']
            flight_times.append(flight_time)
        
        # Calculate typing speed (characters per minute)
        total_time = (keystroke_patterns[-1]['timestamp'] - keystroke_patterns[0]['timestamp']) / 1000.0 / 60.0
        typing_speed = len(keystroke_patterns) / total_time if total_time > 0 else 0
        
        # Rhythm consistency (based on flight time variance)
        rhythm_consistency = 1.0 / (1.0 + np.std(flight_times)) if flight_times else 0
        
        # Key dwell variance (humans have more variance)
        dwell_variance = np.std(dwell_times) if dwell_times else 0
        
        return {
            'typing_rhythm_consistency': float(rhythm_consistency),
            'typing_speed': float(typing_speed),
            'key_dwell_variance': float(dwell_variance)
        }
    
    def _analyze_scroll_patterns(self, scroll_patterns):
        """Analyze scrolling behavior"""
        if not scroll_patterns:
            return {
                'scroll_smoothness': 0,
                'scroll_speed_variance': 0,
                'scroll_direction_consistency': 0
            }
        
        # Extract scroll speeds and directions
        speeds = []
        directions = []
        
        for scroll in scroll_patterns:
            delta_y = scroll.get('deltaY', 0)
            speeds.append(abs(delta_y))
            directions.append(1 if delta_y > 0 else -1 if delta_y < 0 else 0)
        
        # Speed variance (humans have more variance)
        speed_variance = np.std(speeds) if speeds else 0
        
        # Direction consistency (bots might scroll more consistently)
        direction_changes = sum(1 for i in range(1, len(directions)) 
                              if directions[i] != directions[i-1])
        direction_consistency = 1.0 - (direction_changes / len(directions)) if len(directions) > 0 else 0
        
        # Smoothness (inverse of speed variance, normalized)
        smoothness = 1.0 / (1.0 + speed_variance / 100.0) if speed_variance > 0 else 1.0
        
        return {
            'scroll_smoothness': float(smoothness),
            'scroll_speed_variance': float(speed_variance),
            'scroll_direction_consistency': float(direction_consistency)
        }
    
    def extract_features(self, behavioral_data):
        """Extract features from behavioral data for ML model"""
        # Handle both database model and dictionary formats
        if hasattr(behavioral_data, 'mouse_movements'):
            # Database model
            data_dict = {
                'mouse_movements': behavioral_data.mouse_movements or [],
                'click_patterns': behavioral_data.click_patterns or [],
                'keystroke_patterns': behavioral_data.keystroke_patterns or [],
                'scroll_patterns': behavioral_data.scroll_patterns or [],
                'user_agent': behavioral_data.user_agent or '',
                'screen_resolution': behavioral_data.screen_resolution or '0x0'
            }
        else:
            # Dictionary format from API
            data_dict = behavioral_data
        
        # Use the ML model's feature extraction method
        from ml_model import MLModel
        ml_model = MLModel()
        return ml_model.extract_features(data_dict)
