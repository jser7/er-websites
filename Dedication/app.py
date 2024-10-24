from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace this with your actual secret key
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from functools import wraps
from flask import abort

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = db.session.get(User, session.get('user_id'))
            if user is None or user.role != role:
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    xp = db.Column(db.Integer, default=0)
    role = db.Column(db.String(50), default='owner')  # Ensure role is added

    # Relationship with Task (one-to-many)
    tasks = db.relationship('Task', backref='user', lazy=True)

    # Relationship with UserInventory (one-to-many)
    inventory = db.relationship('UserInventory', back_populates='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    difficulty = db.Column(db.String(10), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completion_date = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


    def calculate_xp(self):
        base_xp = {'easy': 10, 'medium': 25, 'hard': 50}
        
        # If completion_date is None, return base XP (task not completed)
        if self.completion_date is None:
            return 0

        # Calculate time difference between due date and completion date
        time_diff = (self.due_date - self.completion_date).days
        xp = base_xp.get(self.difficulty, 0)  # Default to 0 XP if difficulty is unknown

        if time_diff > 0:  # Task completed before the due date
            xp += 10  # Bonus XP for early completion
        elif time_diff < 0:  # Task completed after the due date
            xp -= 5  # Penalty XP for late completion

        return max(xp, 0)  # Ensure XP doesn't go below 0

        # Function to determine the rewards based on completion time
    def calculate_rewards(self):
        # Define rarity percentages based on task difficulty
        rarity_chances = {
            'easy': {'Common': 70, 'Uncommon': 20, 'Rare': 7, 'Epic': 2, 'Legendary': 1, 'Mythic': 0.5, 'Supreme': 0.5},
            'medium': {'Common': 50, 'Uncommon': 25, 'Rare': 15, 'Epic': 5, 'Legendary': 3, 'Mythic': 1, 'Supreme': 1},
            'hard': {'Common': 30, 'Uncommon': 25, 'Rare': 20, 'Epic': 10, 'Legendary': 8, 'Mythic': 5, 'Supreme': 2}
        }

        # Adjust for early completion by increasing higher rarity chances
        early_completion = (self.due_date - self.completion_date).days > 0
        if early_completion:
            # Increase rare and above chances slightly
            rarity_chances[self.difficulty]['Epic'] += 2
            rarity_chances[self.difficulty]['Legendary'] += 1
            rarity_chances[self.difficulty]['Mythic'] += 1
            rarity_chances[self.difficulty]['Supreme'] += 1

        # Flatten rewards for current difficulty
        rewards = Reward.query.all()  # Fetch rewards from the database
        rewards_by_rarity = {
            'Common': [r for r in rewards if r.rarity == 'Common'],
            'Uncommon': [r for r in rewards if r.rarity == 'Uncommon'],
            'Rare': [r for r in rewards if r.rarity == 'Rare'],
            'Epic': [r for r in rewards if r.rarity == 'Epic'],
            'Legendary': [r for r in rewards if r.rarity == 'Legendary'],
            'Mythic': [r for r in rewards if r.rarity == 'Mythic'],
            'Supreme': [r for r in rewards if r.rarity == 'Supreme']
        }

        # Select the first reward based on rarity percentages
        def select_reward():
            rarity_choice = random.choices(
                population=list(rarity_chances[self.difficulty].keys()),
                weights=list(rarity_chances[self.difficulty].values()),
                k=1
            )[0]
            available_rewards = rewards_by_rarity[rarity_choice]
            return random.choice(available_rewards) if available_rewards else None

        first_reward = select_reward()

        # If completed early, reward a second item
        second_reward = select_reward() if early_completion else None

        return [first_reward, second_reward] if second_reward else [first_reward]



class Reward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rarity = db.Column(db.String(50))
    type = db.Column(db.String(50))

    user_inventory = db.relationship('UserInventory', back_populates='reward')

class UserInventory(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    reward_id = db.Column(db.Integer, db.ForeignKey('reward.id'), primary_key=True)
    acquired_at = db.Column(db.DateTime, nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)  # Ensure quantity defaults to 1 and is never None

    user = db.relationship('User', back_populates='inventory')
    reward = db.relationship('Reward', back_populates='user_inventory')

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
@role_required('owner')
def admin_panel():
    user_id = session.get('user_id')
    if user_id is None:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))
    
    user = db.session.get(User, user_id)
    if not user or user.role != 'owner':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    users = User.query.all()
    rewards = Reward.query.all()

    return render_template('admin_panel.html', users=users, rewards=rewards)

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@role_required('owner')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        # Retrieve the form data
        role = request.form['role']
        xp = request.form['xp']
        
        # Update user's role and XP
        user.role = role
        user.xp = xp
        
        db.session.commit()
        return redirect(url_for('admin_panel'))

    # Render edit page
    return render_template('edit_user.html', user=user)
@app.route('/admin/delete_user/<int:user_id>', methods=['GET', 'POST'])
@role_required('owner')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/assign_reward', methods=['POST'])
@role_required('owner')
def assign_reward():
    user_id = request.form['user_id']
    reward_id = request.form['reward_id']
    
    # Check if the user and reward exist
    user = User.query.get(user_id)
    reward = Reward.query.get(reward_id)
    
    if user and reward:
        # Add reward to user's inventory
        inventory_item = UserInventory(user_id=user.id, reward_id=reward.id, acquired_at=datetime.utcnow())
        db.session.add(inventory_item)
        db.session.commit()
        
        flash('Reward assigned successfully!', 'success')
    else:
        flash('User or Reward not found.', 'danger')
    
    return redirect(url_for('admin_panel'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(email=email).first() is None:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email already registered!', 'danger')
    
    return render_template('register.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Retrieve form data
        email = request.form['email']
        password = request.form['password']

        # Check if user exists
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            # Log the user in (store user ID in session)
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if user_id is None:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))

    tasks = Task.query.filter_by(user_id=user.id).all()

    # Debugging output to check if tasks are being fetched
    if not tasks:
        print(f"No tasks found for user {user_id}")
    else:
        for task in tasks:
            print(f"Task Title: {task.title}, Due Date: {task.due_date}, Completed: {task.completed}")

    # Fetch notifications from session
    notifications = session.pop('notifications', [])

    return render_template('dashboard.html', user=user, tasks=tasks, notifications=notifications)



def add_notification(message):
    """Helper function to add a notification to the session."""
    if 'notifications' not in session:
        session['notifications'] = []
    session['notifications'].append(message)

def clear_notifications():
    """Clear notifications after they are displayed."""
    session.pop('notifications', None)


@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if request.method == 'POST':
        # Handle form submission
        user = db.session.get(User, session['user_id'])
        title = request.form['title']
        description = request.form['description']
        difficulty = request.form['difficulty']
        due_date_str = request.form['due_date']

        # Convert due_date string to datetime
        try:
            print(type(due_date_str))
            due_date = datetime.fromisoformat(due_date_str)
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('dashboard'))

        # Create new task
        new_task = Task(
            title=title,
            description=description,
            difficulty=difficulty,
            due_date=due_date,
            user_id=user.id
        )

        db.session.add(new_task)
        db.session.commit()

        flash('Task added successfully!', 'success')
        return redirect(url_for('dashboard'))
    else:
        # Render the add task form
        return render_template('add_task.html')

@app.route('/complete_task/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    task = Task.query.get(task_id)

    user = User.query.get(session['user_id'])

    if task and not task.completed:
        task.completed = True
        task.completion_date = datetime.utcnow()

        # Get rewards based on the task's difficulty and completion date
        rewards = task.calculate_rewards()
        print(rewards)
        # Add each reward to the user's inventory
        for reward in rewards:
            if reward:
                # Check if the user already has this reward in their inventory
                existing_inventory_item = UserInventory.query.filter_by(user_id=user.id, reward_id=reward.id).first()
                
                if existing_inventory_item:
                    # If the user already has the reward, increase the quantity
                    existing_inventory_item.quantity += 1
                else:
                    # If the reward doesn't exist in the user's inventory, add it
                    new_inventory_item = UserInventory(
                        user_id=user.id,
                        reward_id=reward.id,
                        quantity=1,
                        acquired_at=datetime.utcnow()
                    )
                    db.session.add(new_inventory_item)

        db.session.commit()

        # Serialize rewards for session storage
        serialized_rewards = [{'id': r.id, 'name': r.name, 'rarity': r.rarity} for r in rewards if r is not None]

        session['notifications'] = serialized_rewards
        
        flash('Task completed and rewards added to your inventory!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Task not found or already completed.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)

    if task.user_id != session['user_id']:
        flash('You are not authorized to delete this task.', 'danger')
        return redirect(url_for('dashboard'))

    db.session.delete(task)
    db.session.commit()

    flash('Task deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.context_processor
def inject_user():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        return dict(logged_in_user=user)
    return dict(logged_in_user=None)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'your_secret_key'

if __name__ == '__main__':
    app.run(debug=True)
