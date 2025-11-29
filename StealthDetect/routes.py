from flask import render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import BehavioralData, DetectionLog, ModelMetrics, User, Task
from behavioral_analyzer import BehavioralAnalyzer
from ml_model import MLModel
import uuid
import time
from datetime import datetime, timedelta
import logging
import random
import numpy as np  # For keystroke analysis

# Initialize components
behavioral_analyzer = BehavioralAnalyzer()
ml_model = MLModel()

# ------------------------ Home / Auth routes ------------------------ #
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            return jsonify({'error': 'All fields are required'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        if request.is_json:
            return jsonify({'success': True, 'message': 'Registration successful'})
        else:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.is_blocked:
                return jsonify({'error': 'Your account has been blocked due to suspicious behavior'}), 403

            session.clear()
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            session['session_id'] = str(uuid.uuid4())

            redirect_url = url_for('admin_dashboard') if user.is_admin else url_for('welcome_page')
            if request.is_json:
                return jsonify({'success': True, 'redirect': redirect_url})
            else:
                return redirect(redirect_url)

        return jsonify({'error': 'Invalid username or password'}), 401

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))


# ------------------------ DASHBOARD ------------------------ #
@app.route('/dashboard')
@login_required
def user_dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

    user_tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.asc()).limit(3).all()

    if len(user_tasks) < 3:
        remaining = 3 - len(user_tasks)
        create_user_tasks(current_user.id, num_tasks=remaining)
        user_tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.asc()).limit(3).all()

    detection_query = DetectionLog.query.order_by(DetectionLog.timestamp.desc())
    if hasattr(DetectionLog, 'user_id'):
        detection_query = detection_query.filter(
            DetectionLog.user_id == current_user.id,
            DetectionLog.session_id == session.get('session_id', ''),
            DetectionLog.action_type == 'task_completion'
        )
    else:
        detection_query = detection_query.filter(
            DetectionLog.session_id == session.get('session_id', ''),
            DetectionLog.action_type == 'task_completion'
        )

    recent_detections = detection_query.limit(3).all()

    if not recent_detections:
        final_classification = 'unknown'
        avg_confidence = 0.0
    else:
        human_count = 0
        bot_count = 0
        total_confidence = 0.0

        for d in recent_detections:
            if d.prediction == 'human':
                human_count += 1
            elif d.prediction == 'bot':
                bot_count += 1
            total_confidence += (d.confidence or 0.0)

        avg_confidence = total_confidence / len(recent_detections)
        final_classification = (
            'human' if human_count > bot_count else
            'bot' if bot_count > human_count else
            'unknown'
        )

    return render_template(
        'dashboard/user_dashboard.html',
        tasks=user_tasks,
        recent_detections=recent_detections,
        final_classification=final_classification,
        avg_confidence=avg_confidence
    )


@app.route('/welcome')
@login_required
def welcome_page():
    return render_template('dashboard/welcome.html', user=current_user)


def create_user_tasks(user_id, num_tasks=3):
    task_templates = [
        {'title': 'Form Interaction Test',
         'description': 'Complete a simple form with natural mouse and keyboard interactions.',
         'task_type': 'form_fill'},
        {'title': 'Click Pattern Analysis',
         'description': 'Perform a series of clicks to analyze your clicking behavior.',
         'task_type': 'click_sequence'},
        {'title': 'Typing Behavior Assessment',
         'description': 'Type a given text to analyze your keystroke dynamics.',
         'task_type': 'typing_test'}
    ]

    existing_types = {t.task_type for t in Task.query.filter_by(user_id=user_id).all()}
    available = [t for t in task_templates if t['task_type'] not in existing_types]

    selected = random.sample(available, k=min(num_tasks, len(available)))

    for template in selected:
        task = Task(
            user_id=user_id,
            title=template['title'],
            description=template['description'],
            task_type=template['task_type'],
            status='pending'
        )
        db.session.add(task)

    db.session.commit()


# ------------------------ TASK PAGE ------------------------ #
@app.route('/task/<int:task_id>')
@login_required
def perform_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return redirect(url_for('user_dashboard'))

    if task.status == 'completed':
        flash('This task has already been completed.', 'info')
        return redirect(url_for('user_dashboard'))

    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

    return render_template('tasks/task_interface.html', task=task, session_id=session['session_id'])


# ------------------------ API: behavioral_data ------------------------ #
@app.route('/api/behavioral_data', methods=['POST'])
def collect_behavioral_data():
    try:
        data = request.get_json()
        if not data or 'sessionId' not in data:
            return jsonify({'error': 'Invalid data'}), 400

        session_id = data['sessionId']

        behavioral_data = BehavioralData(
            session_id=session_id,
            mouse_movements=data.get('mouseMovements', []),
            click_patterns=data.get('clickPatterns', []),
            scroll_patterns=data.get('scrollPatterns', []),
            keystroke_patterns=data.get('keystrokePatterns', []),
            user_agent=request.headers.get('User-Agent'),
            ip_address=request.remote_addr
        )

        metrics = behavioral_analyzer.analyze_patterns(data)
        behavioral_data.mouse_velocity_avg = metrics.get('mouse_velocity_avg')
        behavioral_data.mouse_velocity_std = metrics.get('mouse_velocity_std')
        behavioral_data.click_frequency = metrics.get('click_frequency')
        behavioral_data.typing_rhythm_consistency = metrics.get('typing_rhythm_consistency')

        db.session.add(behavioral_data)
        db.session.commit()

        return jsonify({'status': 'success', 'data_id': behavioral_data.id})

    except Exception as e:
        logging.error(f"Error collecting behavioral data: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# ------------------------ API: detect_bot (ORIGINAL) ------------------------ #
@app.route('/api/detect_bot', methods=['POST'])
def detect_bot():
    start_time = time.time()
    try:
        data = request.get_json()
        if not data or 'sessionId' not in data:
            return jsonify({'error': 'Invalid data'}), 400

        print("🧠 Received behavioral data:", data.keys())

        session_id = data['sessionId']
        task_id = data.get('taskId')

        click_events = len(data.get('clickPatterns', []))
        mouse_events = len(data.get('mouseMovements', []))
        keyboard_events = len(data.get('keystrokePatterns', []))
        scroll_events = len(data.get('scrollPatterns', []))
        interaction_time = float(data.get('interactionTime', 0))

        # Debug log for server-side inspection
        logging.info(f"DEBUG detect_bot: task_id={task_id} clicks={click_events} keys={keyboard_events} mouse={mouse_events} scrolls={scroll_events} interaction_time={interaction_time}")

        # ------------------------ CLICK-TASK SPECIAL CASE ------------------------
        # If the task is the click_pattern task, decide based on clicks only.
        # This prevents the keyboard==0 rule from misclassifying click-only tasks.
        try:
            if task_id:
                task_obj = Task.query.get(task_id)
            else:
                task_obj = None
        except Exception:
            task_obj = None

        if task_obj and getattr(task_obj, 'task_type', None) == 'click_sequence':
            # Require at least 3 clicks to be considered human (tune threshold as needed)
            if click_events >= 3:
                prediction = 'human'
                confidence = 0.90
            else:
                prediction = 'bot'
                confidence = 0.96

            # Save detection log and mark task completed (preserve original flow)
            detection_log = DetectionLog(
                session_id=session_id,
                prediction=prediction,
                confidence=confidence,
                action_type=data.get('action_type', 'task_completion'),
                page_url=data.get('page_url', ''),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

            if current_user.is_authenticated and not current_user.is_admin and hasattr(DetectionLog, 'user_id'):
                detection_log.user_id = current_user.id

            db.session.add(detection_log)

            if current_user.is_authenticated and not current_user.is_admin:
                current_user.update_behavioral_stats(prediction, confidence)

            # Mark the task completed if it belongs to the current user (keep original behavior)
            if task_id and current_user.is_authenticated:
                try:
                    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
                    if task:
                        task.status = 'completed'
                        task.completed_at = datetime.utcnow()
                        task.behavioral_score = confidence
                except Exception:
                    # if something goes wrong here, we still proceed to commit log
                    logging.exception("Error updating task status for click_sequence")

            db.session.commit()

            logging.info(f"✅ Click-task prediction: {prediction.upper()} (Confidence: {confidence:.2f})")
            return jsonify({'prediction': prediction, 'confidence': confidence, 'is_human': prediction == 'human'})
        # ---------------------- end click-task special case ----------------------

        # ---------------- BOT DETECTION LOGIC (original rules preserved) ---------------- #
        if keyboard_events == 0:
            prediction = 'bot'
            confidence = 0.98

        elif keyboard_events < 3 and mouse_events < 7:
            prediction = 'bot'
            confidence = 0.95

        elif (
            interaction_time < 1.5 and
            keyboard_events < 3 and
            mouse_events < 7 and
            click_events <= 1 and
            scroll_events == 0
        ):
            prediction = 'bot'
            confidence = 0.96

        elif keyboard_events > 5:
            intervals = data.get("keystrokeIntervals", [])
            if intervals:
                std_dev = np.std(intervals)
                if std_dev < 0.05:
                    prediction = 'bot'
                    confidence = 0.92
                else:
                    prediction = 'human'
                    confidence = 0.88
            else:
                prediction = 'human'
                confidence = 0.88

        else:
            prediction = 'human'
            confidence = 0.85
        # ---------------------------------------------------------------------------- #

        detection_log = DetectionLog(
            session_id=session_id,
            prediction=prediction,
            confidence=confidence,
            action_type=data.get('action_type', 'task_completion'),
            page_url=data.get('page_url', ''),
            processing_time_ms=int((time.time() - start_time) * 1000)
        )

        if current_user.is_authenticated and not current_user.is_admin and hasattr(DetectionLog, 'user_id'):
            detection_log.user_id = current_user.id

        db.session.add(detection_log)

        if current_user.is_authenticated and not current_user.is_admin:
            current_user.update_behavioral_stats(prediction, confidence)

        if task_id:
            task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
            if task:
                task.status = 'completed'
                task.completed_at = datetime.utcnow()
                task.behavioral_score = confidence

        db.session.commit()

        logging.info(f"✅ Prediction: {prediction.upper()} (Confidence: {confidence:.2f})")

        return jsonify({'prediction': prediction, 'confidence': confidence, 'is_human': prediction == 'human'})

    except Exception as e:
        db.session.rollback()
        logging.error(f"❌ Error in detect_bot: {str(e)}")
        return jsonify({'error': 'Analysis failed'}), 500


# ------------------------ Admin Dashboard ------------------------ #
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))

    users = (
        User.query
        .filter(
            User.is_admin == False,
            User.last_login.isnot(None)
        )
        .order_by(User.last_login.desc())
        .all()
    )

    recent_detections = DetectionLog.query.order_by(DetectionLog.timestamp.desc()).limit(100).all()

    total_users = len(users)
    active_users = len([
        u for u in users if u.last_login and u.last_login > datetime.utcnow() - timedelta(days=7)
    ])
    blocked_users = len([u for u in users if u.is_blocked])
    suspected_bots = len([u for u in users if u.is_likely_bot])
    latest_metrics = ModelMetrics.query.order_by(ModelMetrics.timestamp.desc()).first()

    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'blocked_users': blocked_users,
        'suspected_bots': suspected_bots,
        'total_detections': len(recent_detections),
        'human_detections': len([d for d in recent_detections if d.prediction == 'human']),
        'bot_detections': len([d for d in recent_detections if d.prediction == 'bot'])
    }

    return render_template(
        'dashboard/admin_dashboard.html',
        users=users,
        stats=stats,
        recent_detections=recent_detections[:20],
        model_metrics=latest_metrics
    )


# ------------------------ API: Admin Users Data for Chart ------------------------ #
@app.route('/api/admin/users')
@login_required
def admin_users_data():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    users = User.query.filter_by(is_admin=False).all()

    user_data = []
    for user in users:
        user_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'bot_percentage': getattr(user, 'bot_percentage', 0),
            'avg_confidence_score': getattr(user, 'avg_confidence_score', 0),
            'is_likely_bot': getattr(user, 'is_likely_bot', False),
            'is_blocked': getattr(user, 'is_blocked', False)
        })

    return jsonify({'users': user_data})


# ------------------------ Admin User Control APIs ------------------------ #
@app.route('/admin/block_user/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403

    user = User.query.get(user_id)
    if not user or user.is_admin:
        return jsonify({'success': False, 'message': 'Invalid user'}), 404

    try:
        user.is_blocked = True
        db.session.commit()
        return jsonify({'success': True, 'message': f'User {user.username} has been blocked.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error blocking user: {str(e)}'}), 500


@app.route('/admin/unblock_user/<int:user_id>', methods=['POST'])
@login_required
def unblock_user(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403

    user = User.query.get(user_id)
    if not user or user.is_admin:
        return jsonify({'success': False, 'message': 'Invalid user'}), 404

    try:
        user.is_blocked = False
        db.session.commit()
        return jsonify({'success': True, 'message': f'User {user.username} has been unblocked.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error unblocking user: {str(e)}'}), 500
