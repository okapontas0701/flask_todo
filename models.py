from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

#DB定義
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)  # ユーザーID (主キー)
    name = db.Column(db.String(50), nullable=False)  # ユーザー名
    email = db.Column(db.String(120), unique=True, nullable=False)  # メールアドレス
    role = db.Column(db.String(20), nullable=False, default="staff")  # 役職 (例: staff)
    password_hash = db.Column(db.String(200), nullable=False)  # ハッシュ化されたパスワード

    
    tasks = db.relationship('Task', backref='user', lazy=True)  # タスクとのリレーション
    reviews = db.relationship('Review', backref='user', lazy=True)  # レビューとのリレーション

# Taskクラス: タスク管理
class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)  # タスクID (主キー)
    title = db.Column(db.String(100), nullable=False)  # タスクのタイトル
    description = db.Column(db.Text, nullable=False)  # タスクの詳細
    status = db.Column(db.String(20), nullable=False, default="pending")  # 状態 (例: pending, in_progress, completed)
    due_date = db.Column(db.DateTime, nullable=False)  # 期限
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # 作成日時
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # ユーザーID (外部キー)
    reviews = db.relationship('Review', backref='task', lazy=True)  # レビューとのリレーション

# Reviewクラス: レビュー管理
class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)  # レビューID (主キー)
    content = db.Column(db.Text, nullable=False)  # レビュー内容
    title = db.Column(db.String(100), nullable=False)  # のタイトル
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # 作成日時
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # ユーザーID (外部キー)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)  # タスクID (外部キー)
