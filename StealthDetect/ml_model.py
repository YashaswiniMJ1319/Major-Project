import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import os
import logging
from app import db
from models import ModelMetrics


class MLModel:
    """Machine-Learning engine for StealthCAPTCHA."""

    def __init__(self):
        # Initialize models
        self.rf_model = RandomForestClassifier(
            n_estimators=120,
            max_depth=10,
            random_state=42,
            class_weight="balanced"
        )

        self.svm_model = SVC(
            kernel="rbf",
            probability=True,
            random_state=42,
            class_weight="balanced"
        )

        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_version = "3.4"

        # Logging setup
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler("training_logs.txt"),
                logging.StreamHandler()
            ]
        )

        # Load existing model if available
        self.load_model()

    # ---------------------------------------------------------------------
    # FEATURE EXTRACTION
    # ---------------------------------------------------------------------
    def extract_features(self, behavioral_data):
        """Convert behavioral JSON data to numerical features."""
        f = []

        # Mouse movements
        mv = behavioral_data.get("mouse_movements", [])
        if mv:
            vels = []
            for i in range(1, len(mv)):
                prev, curr = mv[i - 1], mv[i]
                t = (curr["timestamp"] - prev["timestamp"]) / 1000.0
                if t > 0:
                    dist = np.hypot(curr["x"] - prev["x"], curr["y"] - prev["y"])
                    vels.append(dist / t)
            f += [
                np.mean(vels) if vels else 0,
                np.std(vels) if vels else 0,
                len(vels),
                np.max(vels) if vels else 0,
                np.min(vels) if vels else 0,
            ]
        else:
            f += [0, 0, 0, 0, 0]

        # Click patterns
        cp = behavioral_data.get("click_patterns", [])
        if cp:
            intervals = [(cp[i]["timestamp"] - cp[i - 1]["timestamp"]) / 1000.0 for i in range(1, len(cp))]
            f += [len(cp), np.mean(intervals) if intervals else 0, np.std(intervals) if intervals else 0]
        else:
            f += [0, 0, 0]

        # Keystrokes
        ks = behavioral_data.get("keystroke_patterns", [])
        if ks:
            dwell = [k.get("duration", 0) for k in ks]
            flight = [ks[i]["timestamp"] - ks[i - 1]["timestamp"] for i in range(1, len(ks))]
            f += [
                len(ks),
                np.mean(dwell) if dwell else 0,
                np.std(dwell) if dwell else 0,
                np.mean(flight) if flight else 0,
                np.std(flight) if flight else 0,
            ]
        else:
            f += [0, 0, 0, 0, 0]

        # Scrolls
        sp = behavioral_data.get("scroll_patterns", [])
        if sp:
            speeds = [abs(s.get("deltaY", 0)) for s in sp]
            f += [len(sp), np.mean(speeds), np.std(speeds)]
        else:
            f += [0, 0, 0]

        # Browser/device info
        ua = behavioral_data.get("user_agent", "")
        f += [
            int("Chrome" in ua),
            int("Firefox" in ua),
            int("Safari" in ua),
            int("Mobile" in ua),
            len(ua),
        ]

        # Screen resolution
        sr = behavioral_data.get("screen_resolution", "0x0")
        try:
            w, h = map(int, sr.split("x"))
            f += [w, h, w * h]
        except Exception:
            f += [0, 0, 0]

        return np.array(f).reshape(1, -1)

    # ---------------------------------------------------------------------
    # SYNTHETIC TRAINING DATA
    # ---------------------------------------------------------------------
    def generate_training_data(self, n=2000):
        """Generate realistic overlapping synthetic data (humans & bots)."""
        X, y = [], []
        rng = np.random.default_rng()

        # Humans
        for _ in range(n // 2):
            mouse_velocity_avg = rng.normal(200, 90)
            mouse_velocity_std = rng.normal(70, 30)
            num_movements = rng.integers(30, 150)
            max_velocity = mouse_velocity_avg + rng.normal(100, 50)
            min_velocity = max(0, mouse_velocity_avg - rng.normal(100, 40))

            num_clicks = rng.integers(2, 40)
            click_interval_avg = rng.normal(1.2, 0.8)
            click_interval_std = rng.normal(0.8, 0.5)

            num_keystrokes = rng.integers(5, 80)
            dwell_time_avg = rng.normal(100, 40)
            dwell_time_std = rng.normal(60, 30)
            flight_time_avg = rng.normal(120, 60)
            flight_time_std = rng.normal(70, 30)

            num_scrolls = rng.integers(5, 40)
            scroll_speed_avg = rng.normal(70, 30)
            scroll_speed_std = rng.normal(40, 20)

            chrome = rng.choice([0, 1], p=[0.5, 0.5])
            firefox = rng.choice([0, 1], p=[0.85, 0.15])
            safari = rng.choice([0, 1], p=[0.95, 0.05])
            mobile = rng.choice([0, 1], p=[0.5, 0.5])
            ua_length = rng.integers(70, 200)

            width = rng.choice([1920, 1366, 1440, 1280, 1024])
            height = rng.choice([1080, 900, 768, 720])
            features = [
                mouse_velocity_avg, mouse_velocity_std, num_movements,
                max_velocity, min_velocity,
                num_clicks, click_interval_avg, click_interval_std,
                num_keystrokes, dwell_time_avg, dwell_time_std,
                flight_time_avg, flight_time_std,
                num_scrolls, scroll_speed_avg, scroll_speed_std,
                chrome, firefox, safari, mobile, ua_length,
                width, height, width * height
            ]
            X.append(features)
            y.append(1)

        # Bots
        for _ in range(n // 2):
            mouse_velocity_avg = rng.normal(230, 100)
            mouse_velocity_std = rng.normal(60, 40)
            num_movements = rng.integers(40, 160)
            max_velocity = mouse_velocity_avg + rng.normal(80, 60)
            min_velocity = max(0, mouse_velocity_avg - rng.normal(100, 50))

            num_clicks = rng.integers(3, 35)
            click_interval_avg = rng.normal(1.0, 0.6)
            click_interval_std = rng.normal(0.6, 0.3)

            num_keystrokes = rng.integers(5, 90)
            dwell_time_avg = rng.normal(85, 35)
            dwell_time_std = rng.normal(50, 25)
            flight_time_avg = rng.normal(110, 50)
            flight_time_std = rng.normal(60, 25)

            num_scrolls = rng.integers(5, 35)
            scroll_speed_avg = rng.normal(80, 25)
            scroll_speed_std = rng.normal(35, 15)

            chrome = rng.choice([0, 1], p=[0.4, 0.6])
            firefox = rng.choice([0, 1], p=[0.9, 0.1])
            safari = rng.choice([0, 1], p=[0.95, 0.05])
            mobile = rng.choice([0, 1], p=[0.7, 0.3])
            ua_length = rng.integers(60, 190)

            width = rng.choice([1920, 1366, 1024])
            height = rng.choice([1080, 900, 768])
            features = [
                mouse_velocity_avg, mouse_velocity_std, num_movements,
                max_velocity, min_velocity,
                num_clicks, click_interval_avg, click_interval_std,
                num_keystrokes, dwell_time_avg, dwell_time_std,
                flight_time_avg, flight_time_std,
                num_scrolls, scroll_speed_avg, scroll_speed_std,
                chrome, firefox, safari, mobile, ua_length,
                width, height, width * height
            ]
            X.append(features)
            y.append(0)

        return np.array(X), np.array(y)

    # ---------------------------------------------------------------------
    # TRAINING
    # ---------------------------------------------------------------------
    def _calculate_metrics(self, model, X_test, y_test):
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        y_pred = model.predict(X_test)
        return dict(
            accuracy=accuracy_score(y_test, y_pred),
            precision=precision_score(y_test, y_pred, zero_division=0),
            recall=recall_score(y_test, y_pred, zero_division=0),
            f1_score=f1_score(y_test, y_pred, zero_division=0)
        )

    def train_initial_model(self):
        """Train SVM first → Random Forest → compare → select best."""
        if self.is_trained:
            return
        try:
            X, y = self.generate_training_data(2000)
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
            X_train_s, X_test_s = self.scaler.fit_transform(X_train), self.scaler.transform(X_test)

            results = {}

            logging.info("Training SVM first...")
            self.svm_model.fit(X_train_s, y_train)
            results["SVM"] = self._calculate_metrics(self.svm_model, X_test_s, y_test)
            logging.info(f"SVM Accuracy: {results['SVM']['accuracy']:.4f}")

            logging.info("Training Random Forest...")
            self.rf_model.fit(X_train_s, y_train)
            results["Random Forest"] = self._calculate_metrics(self.rf_model, X_test_s, y_test)
            logging.info(f"Random Forest Accuracy: {results['Random Forest']['accuracy']:.4f}")

            best = max(results, key=lambda k: results[k]["accuracy"])
            self.model = self.rf_model if best == "Random Forest" else self.svm_model
            self.is_trained = True

            df = pd.DataFrame(results).T
            logging.info("\n--- MODEL COMPARISON RESULTS ---\n%s", df.to_string(float_format="%.4f"))
            logging.info(f"✅ Selected Model: {best}\n--------------------------------")

            m = results[best]
            db.session.add(ModelMetrics(
                accuracy=m["accuracy"],
                precision=m["precision"],
                recall=m["recall"],
                f1_score=m["f1_score"],
                training_samples=len(X),
                human_samples=int(sum(y)),
                bot_samples=int(len(y) - sum(y)),
                model_version=self.model_version
            ))
            db.session.commit()
            self.save_model()

        except Exception as e:
            logging.error(f"Error training model: {e}", exc_info=True)

    # ---------------------------------------------------------------------
    # PREDICT / SAVE / LOAD
    # ---------------------------------------------------------------------
    def predict(self, features):
        """Predict human/bot label."""
        if not self.is_trained:
            self.train_initial_model()
        try:
            scaled = self.scaler.transform(features)
            proba = self.model.predict_proba(scaled)[0]
            pred = self.model.predict(scaled)[0]
            return ("human" if pred == 1 else "bot", float(proba[pred]))
        except Exception as e:
            logging.error(f"Error predicting: {e}")
            return "unknown", 0.5

    def save_model(self):
        try:
            os.makedirs("models", exist_ok=True)
            joblib.dump(self.model, "models/stealth_captcha_model.pkl")
            joblib.dump(self.scaler, "models/stealth_captcha_scaler.pkl")
            logging.info("✅ Model saved successfully.")
        except Exception as e:
            logging.error(f"Error saving model: {e}")

    def load_model(self):
        try:
            if all(os.path.exists(f) for f in [
                "models/stealth_captcha_model.pkl", "models/stealth_captcha_scaler.pkl"
            ]):
                self.model = joblib.load("models/stealth_captcha_model.pkl")
                self.scaler = joblib.load("models/stealth_captcha_scaler.pkl")
                self.is_trained = True
                logging.info("✅ Model loaded successfully.")
            else:
                logging.info("No saved model found. Training a new one...")
        except Exception as e:
            logging.error(f"Error loading model: {e}")