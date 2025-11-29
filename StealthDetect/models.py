#from app import db
from extensions import db
from datetime import datetime
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class BehavioralData(db.Model):
    __tablename__ = 'behavioral_data'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Mouse movement data
    mouse_movements = db.Column(db.JSON)  # Array of {x, y, timestamp}
    click_patterns = db.Column(db.JSON)   # Array of {x, y, timestamp, button}
    scroll_patterns = db.Column(db.JSON)  # Array of {deltaX, deltaY, timestamp}
    
    # Typing patterns
    keystroke_patterns = db.Column(db.JSON)  # Array of {key, timestamp, duration}
    
    
    user_agent = db.Column(db.Text)
    screen_resolution = db.Column(db.String(20))
    timezone = db.Column(db.String(50))
    language = db.Column(db.String(10))
    platform = db.Column(db.String(50))
    
    # Behavioral metrics (calculated)
    mouse_velocity_avg = db.Column(db.Float)
    mouse_velocity_std = db.Column(db.Float)
    click_frequency = db.Column(db.Float)
    typing_rhythm_consistency = db.Column(db.Float)
    
    # IP and network data
    ip_address = db.Column(db.String(45))
    
    # Classification result
    is_human = db.Column(db.Boolean)
    confidence_score = db.Column(db.Float)
    
    def __repr__(self):
        return f'<BehavioralData {self.session_id}>'

class DetectionLog(db.Model):
    __tablename__ = 'detection_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Detection results
    prediction = db.Column(db.String(10))  # 'human' or 'bot'
    confidence = db.Column(db.Float)
    
    # Context
    page_url = db.Column(db.String(500))
    action_type = db.Column(db.String(50))  # 'form_submit', 'login', 'payment', etc.
    
    # Additional metadata
    processing_time_ms = db.Column(db.Integer)
    
    def __repr__(self):
        return f'<DetectionLog {self.session_id}: {self.prediction}>'

class ModelMetrics(db.Model):
    __tablename__ = 'model_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Model performance metrics
    accuracy = db.Column(db.Float)
    precision = db.Column(db.Float)
    recall = db.Column(db.Float)
    f1_score = db.Column(db.Float)
    
    # Training data stats
    training_samples = db.Column(db.Integer)
    human_samples = db.Column(db.Integer)
    bot_samples = db.Column(db.Integer)
    
    # Model version
    model_version = db.Column(db.String(20))
    
    def __repr__(self):
        return f'<ModelMetrics v{self.model_version}: {self.accuracy:.3f}>'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Behavioral classification results
    total_sessions = db.Column(db.Integer, default=0)
    human_classifications = db.Column(db.Integer, default=0)
    bot_classifications = db.Column(db.Integer, default=0)
    avg_confidence_score = db.Column(db.Float, default=0.0)
    
    # Relationship to tasks
    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def update_behavioral_stats(self, prediction, confidence):
        """Update user's behavioral classification statistics"""
        self.total_sessions += 1
        if prediction == 'human':
            self.human_classifications += 1
        else:
            self.bot_classifications += 1
        
        # Update average confidence score
        if self.total_sessions == 1:
            self.avg_confidence_score = confidence
        else:
            self.avg_confidence_score = (
                (self.avg_confidence_score * (self.total_sessions - 1) + confidence) 
                / self.total_sessions
            )
    
    @property
    def bot_percentage(self):
        if self.total_sessions == 0:
            return 0
        return (self.bot_classifications / self.total_sessions) * 100
    
    @property
    def is_likely_bot(self):
        return self.bot_percentage > 60  # Threshold for bot classification

    def __repr__(self):
        return f'<User {self.username}>'

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    task_type = db.Column(db.String(50), nullable=False)  # 'form_fill', 'click_sequence', 'typing_test'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Task performance metrics
    completion_time_ms = db.Column(db.Integer)
    mouse_events = db.Column(db.Integer, default=0)
    keyboard_events = db.Column(db.Integer, default=0)
    behavioral_score = db.Column(db.Float)  # Human-likeness score
    
    def __repr__(self):
        return f'<Task {self.title} - {self.status}>'
