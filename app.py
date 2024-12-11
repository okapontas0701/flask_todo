from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from models import db, User, Task, Review
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta

import os
from dotenv import load_dotenv
load_dotenv()

# Flaskアプリケーションの初期化
app = Flask(__name__)

# データベース接続設定
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
# データベースとマイグレーション設定の初期化
db.init_app(app)
migrate = Migrate(app, db)

# Flask-Loginの初期化
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # ログインが必要な場合にリダイレクトされるページ

# ユーザーをIDで取得する関数（Flask-Login用）
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# データベースの全データ削除用（デバッグ・開発時のみに使用）
@app.route('/delete_all_data')
@login_required
def delete_all_data():
    try:
        # 全てのレビュー、タスク、ユーザーを削除
        Review.query.delete()
        Task.query.delete()
        User.query.delete()
        db.session.commit()
        flash("全てのデータを削除しました。", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"データ削除中にエラーが発生しました: {e}", "danger")
    return redirect(url_for('list_tasks'))

# ユーザー登録ページ
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('user/register.html')  # 登録フォームを表示

    # ユーザー登録情報を取得
    name = request.form.get('name')
    email = request.form.get('email')
    role = request.form.get('role', 'staff')  # デフォルトは'staff'ロール
    password = request.form.get('password')

    # 入力値のバリデーション
    if not name or not email or not password:
        return "全てのフィールドに入力してください", 400

    # メールアドレスの重複確認
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return render_template('user/register.html', error="そのアドレスはすでに登録されています。")

    # パスワードのハッシュ化と新規ユーザーの作成
    password_hash = generate_password_hash(password)
    new_user = User(name=name, email=email, role=role, password_hash=password_hash)

    try:
        db.session.add(new_user)
        db.session.commit()
        print(f"新しいユーザーが登録されました: {new_user}")
    except Exception as e:
        db.session.rollback()
        print(f"エラー: {e}")
        return f"エラーが発生しました: {e}", 500

    return redirect(url_for('profile'))  # プロフィールページにリダイレクト

# ログイン処理
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('user/login.html')  # ログインフォームを表示

    # フォーム入力からメールアドレスとパスワードを取得
    email = request.form.get('email')
    password = request.form.get('password')

    # 入力値のバリデーション
    if not email or not password:
        flash("メールアドレスとパスワードを入力してください", "danger")
        return redirect(url_for('login'))

    # ユーザー認証
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        login_user(user)  # ユーザーをログイン状態にする
        flash("ログインに成功しました！", "success")
        next_page = request.args.get('next')  # ログイン後にリダイレクトするページ
        return redirect(next_page or url_for('list_tasks'))

    # 認証失敗時
    flash("メールアドレスまたはパスワードが間違っています。", "danger")
    return redirect(url_for('login'))

# ログアウト処理
@app.route("/logout")
@login_required
def logout():
    logout_user()  # ログアウト処理
    flash("ログアウトしました。", "info")
    return redirect(url_for('login'))

# ユーザープロフィールページ
@app.route("/profile")
@login_required
def profile():
    # ログインユーザーのタスク情報を取得
    user_tasks = Task.query.filter_by(user_id=current_user.id).all()
    in_progress_tasks = Task.query.filter_by(status='in_progress', user_id=current_user.id).count()
    completed_tasks = Task.query.filter_by(status='completed', user_id=current_user.id).count()
    pending_tasks = Task.query.filter_by(status='pending', user_id=current_user.id).count()
    review_count = Review.query.filter_by(user_id=current_user.id).count()

    # 近日の期限付きタスクを取得
    upcoming_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.due_date >= datetime.utcnow(),
        Task.due_date <= datetime.utcnow() + timedelta(days=3)
    ).order_by(Task.due_date).all()

    # 期限切れタスクを取得
    overdue_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.due_date < datetime.utcnow(),
        Task.status != 'completed'
    ).order_by(Task.due_date).all()

    return render_template('user/profile.html', 
                           user=current_user, 
                           tasks=user_tasks,
                           in_progress_tasks=in_progress_tasks,
                           completed_tasks=completed_tasks,
                           pending_tasks=pending_tasks,
                           review_count=review_count,
                           upcoming_tasks=upcoming_tasks,
                           overdue_tasks=overdue_tasks)

# タスク一覧表示と検索機能
@app.route('/tasks', methods=['GET', 'POST'])
@login_required
def list_tasks():
    # 検索クエリを取得
    search_query = request.args.get('search', '')
    # 検索条件に一致するタスクを取得（検索がない場合は全件取得）
    tasks = Task.query.filter(Task.title.ilike(f'%{search_query}%')).all() if search_query else Task.query.all()
    return render_template('task/tasks.html', tasks=tasks, search_query=search_query)

# 新しいタスクの作成
@app.route('/tasks/new', methods=['GET', 'POST'])
@login_required
def create_task():
    if request.method == 'GET':
        return render_template('task/new.html')  # 新規タスク作成フォームを表示

    # フォーム入力値を取得
    title = request.form.get('title')
    description = request.form.get('description')
    status = request.form.get('status')
    due_date_str = request.form.get('due_date')

    # 入力値のバリデーション
    if not title or not status:
        flash("必須項目を全て入力してください", "danger")
        return redirect(url_for('create_task'))

    # 締切日を変換
    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash("有効な日時を入力してください", "danger")
            return redirect(url_for('create_task'))

    # 新規タスクの作成
    new_task = Task(title=title, description=description, status=status, due_date=due_date, user_id=current_user.id)

    try:
        db.session.add(new_task)
        db.session.commit()
        flash("タスクが正常に作成されました！", "success")
        return redirect(url_for('list_tasks'))
    except Exception as e:
        db.session.rollback()
        flash(f"タスク作成中にエラーが発生しました: {e}", "danger")
        return redirect(url_for('list_tasks'))

# 特定のタスクの詳細表示
@app.route('/tasks/<int:task_id>', methods=['GET'])
@login_required
def show_task(task_id):
    # 指定されたタスクを取得
    task = Task.query.get_or_404(task_id)
    return render_template('task/show.html', task=task)

# タスクの編集
@app.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    # 指定されたタスクを取得
    task = Task.query.get_or_404(task_id)
    # 他のユーザーによる編集を防止
    if task.user_id != current_user.id:
        flash("編集権限がありません", "danger")
        return redirect(url_for('list_tasks'))

    if request.method == 'POST':
        # フォーム入力値でタスク情報を更新
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        task.status = request.form.get('status')
        due_date_str = request.form.get('due_date')

        try:
            # 締切日を変換
            task.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M') if due_date_str else None
            db.session.commit()
            flash("タスクが更新されました！", "success")
            return redirect(url_for('list_tasks'))
        except Exception as e:
            db.session.rollback()
            flash(f"更新中にエラーが発生しました: {e}", "danger")
            return redirect(url_for('edit_task', task_id=task_id))

    return render_template('task/edit.html', task=task)  # 編集フォームを表示

# タスクの削除
@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    # 指定されたタスクを取得
    task = Task.query.get_or_404(task_id)
    # 他のユーザーによる削除を防止
    if task.user_id != current_user.id:
        flash("削除権限がありません", "danger")
        return redirect(url_for('show_task', task_id=task_id))

    try:
        # タスクに関連するレビューも削除
        for review in task.reviews:
            db.session.delete(review)
        db.session.delete(task)
        db.session.commit()
        flash("タスクと関連するレビューを削除しました", "success")
        return redirect(url_for('list_tasks'))
    except Exception as e:
        db.session.rollback()
        flash(f"削除中にエラーが発生しました: {e}", "danger")
        return redirect(url_for('show_task', task_id=task_id))

# タスクに関連するレビューの作成
@app.route('/tasks/<int:task_id>/reviews', methods=['POST'])
@login_required
def create_review(task_id):
    # 対象のタスクを取得
    task = Task.query.get_or_404(task_id)
    title = request.form.get('title')
    content = request.form.get('content')

    # 入力値のバリデーション
    if not title or not content:
        flash("タイトルと内容は必須です。", "danger")
        return redirect(url_for('show_task', task_id=task_id))

    # 新規レビューの作成
    new_review = Review(title=title, content=content, user_id=current_user.id, task_id=task_id)

    try:
        db.session.add(new_review)
        db.session.commit()
        flash("レビューを投稿しました！", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"レビュー投稿中にエラーが発生しました: {e}", "danger")

    return redirect(url_for('show_task', task_id=task_id))

# レビューの削除
@app.route('/reviews/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_review(review_id):
    # 指定されたレビューを取得
    review = Review.query.get_or_404(review_id)
    # 他のユーザーによる削除を防止
    if review.user_id != current_user.id:
        flash("削除権限がありません。", "danger")
        return redirect(url_for('show_task', task_id=review.task_id))

    try:
        db.session.delete(review)
        db.session.commit()
        flash("レビューを削除しました。", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"レビュー削除中にエラーが発生しました: {e}", "danger")

    return redirect(url_for('show_task', task_id=review.task_id))
