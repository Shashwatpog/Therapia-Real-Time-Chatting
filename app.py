import asyncio
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from flask import render_template
from flask_login import login_required
from flask import redirect, url_for

app = Flask(__name__)
app.secret_key = 'SECRET_KEY'  # Replace with your secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.db'  # Change to a different database (SQLite for testing)
app.static_folder = 'static'
db = SQLAlchemy(app)
socketio = SocketIO(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# Define User model with password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)  # Store password hash

    # Implement UserMixin properties and methods
    @property
    def is_authenticated(self):
        return True  # You can customize this logic based on your app's requirements

    @property
    def is_active(self):
        return True  # You can customize this logic based on your app's requirements

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


# Create the database tables
with app.app_context():
    db.create_all()

# Define Message model
class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    

# Configure your user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# WebSocket route for handling WebSocket connections
@socketio.on('connect')
@login_required
def handle_connect():
    emit('connected', {'data': 'Connected to WebSocket'})

# WebSocket route for handling WebSocket messages
@socketio.on("message")
@login_required
def handle_message(message):
    if "message" in message:
        text = message["message"]
        if current_user.is_authenticated:
            sender_username = current_user.username

            # Find the user sending the message
            sender = User.query.filter_by(username=sender_username).first()
            if not sender:
                emit('error', {'error': f"Sender '{sender_username}' not found."})
            else:
                # Store the message in the database
                new_message = Message(sender_id=sender.id, receiver_id=current_user.id, text=text)
                db.session.add(new_message)
                db.session.commit()
        
                # Broadcast the received message to all connected clients
                emit("message", {"message": f"{current_user.username}: {text}"}, broadcast=True)


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('login'))
    return redirect(url_for('register'))


@app.route('/chat', methods=['GET'])
@login_required
def chat():
    # Retrieve previous messages from the database
    messages = Message.query.filter(
        (Message.sender_id == current_user.id) |
        (Message.receiver_id == current_user.id)
    ).all()

    return render_template('chat.html', messages=messages)


# Route for sending messages
@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    receiver_username = data['receiver']
    text = data['text']
    receiver = User.query.filter_by(username=receiver_username).first()
    
    if not receiver:
        return jsonify({'error': 'Receiver not found'}), 404
    
    # Store the message in the database
    new_message = Message(sender_id=current_user.id, receiver_id=receiver.id, text=text)
    db.session.add(new_message)
    db.session.commit()
    
    return jsonify({'message': 'Message sent successfully'})



# Route for retrieving messages
@app.route('/get_messages', methods=['GET'])
@login_required
def get_messages():
    receiver_username = request.args.get('receiver')
    receiver = User.query.filter_by(username=receiver_username).first()
    
    if not receiver:
        return jsonify({'error': 'Receiver not found'}), 404
    
    # Query the database for messages between the sender and receiver
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == receiver.id)) |
        ((Message.sender_id == receiver.id) & (Message.receiver_id == current_user.id))
    ).all()
    
    message_list = [{'sender': msg.sender.username, 'receiver': msg.receiver.username, 'text': msg.text} for msg in messages]
    
    return jsonify({'conversation': message_list})

# Route for registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 400
        
        # Hash the password before storing it
        password_hash = generate_password_hash(password)
        
        new_user = User(username=username, password_hash=password_hash)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Retrieve user from the database
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            # Log the user in
            login_user(user)
            return redirect(url_for('chat'))  # Redirect to the chat page upon successful login
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
    
    return render_template('login.html')

# Route for user logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        socketio.run(app, debug=True)
