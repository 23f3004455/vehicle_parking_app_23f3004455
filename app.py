from flask import Flask
from flask import render_template, redirect, request, session, url_for
from models.models import db, User, ParkingLot, ParkingSpot, Reservation


app = Flask(__name__)
app.secret_key = 'secret-key' #required for session---secret string that your app uses to secure data stored in the user's browser, especially for sessions and cookies.

# Configure SQLite database (creates app.db file in project root)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
# Disable modification tracking to save memory
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database with Flask app
db.init_app(app)

# Create database and tables
with app.app_context():  # Required for database operations outside routes
    
    # Create all tables based on our models (User, ParkingLot, ParkingSpot, Reservation)
    db.create_all()
    
    # Auto-create admin user
    # Check if admin already exists to avoid duplicates
    admin = User.query.filter_by(username='admin').first()
    
    if not admin:  # Admin doesn't exist, create it
        admin_user = User(
            username='admin',
            password='admin', 
            fullname='Administrator',
            address='Admin Office',
            pin_code='000000',
            phone_number='0000000000',
            role = 'admin'
        )
        # Add admin to database session
        db.session.add(admin_user)
        # Save changes to database
        db.session.commit()

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST': #user clicked register button
        username = request.form['username']
        password = request.form['password']
        fullname = request.form['fullname']
        address = request.form['address']
        pin_code = request.form['pin_code']
        phone_number = request.form['phone_number']

        existing_user = User.query.filter_by(username = username).first()
        if existing_user: #to check if user already exists during register
            return "User already exists."
        
        new_user = User(username = username, password = password, fullname = fullname, address = address, pin_code = pin_code, phone_number = phone_number)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login') #after registration, user is directed to login page
    
    return render_template('register.html') #when user types url or clicks link--- GET method

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST': 
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username = username, password = password).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role

            if user.role == 'admin':
                return redirect('/admin/dashboard')
            else:
                return redirect('/user/dashboard')
        
        else:
            return "Invalid credentials"
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return "Access not granted"
    
    return render_template('admin_dashboard.html')

@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        return "Access not granted"
    
    return render_template('user_dashboard.html')


if __name__ == "__main__":
    app.run(debug=True)  # debug=True enables auto-reload and error details