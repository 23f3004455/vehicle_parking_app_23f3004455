from flask import Flask, flash
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
    db.drop_all()
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
    else:
        if admin.role != 'admin':
            print("Fixing admin role to 'admin'...")
            admin.role = 'admin'
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
        
        new_user = User(username = username, 
                        password = password, 
                        fullname = fullname, 
                        address = address, 
                        pin_code = pin_code, 
                        phone_number = phone_number, 
                        role = 'user')
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
                session['admin'] = True
                return redirect('/admin/dashboard')
            else:
                session['user'] = user.username
                return redirect('/user/dashboard')
        
        else:
            return "Invalid credentials"
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/admin/lots/create', methods=['GET', 'POST'])
def create_parking_lot():
    if 'admin' not in session:
        return redirect('/login')

    if request.method == 'POST':
        location = request.form['location_name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        price = float(request.form['price'])
        max_spots = int(request.form['max_spots'])

        #Create the parking lot
        new_lot = ParkingLot(
            name=location,
            address=address,
            pin_code=pin_code,
            price=price,
            max_spots=max_spots
        )
        db.session.add(new_lot)
        db.session.commit() 

        #Auto-create parking spots for this lot
        for _ in range(max_spots):
            spot = ParkingSpot(lot_id=new_lot.id, status='A')
            db.session.add(spot)

        db.session.commit()

        return redirect('/admin/dashboard')

    return render_template('create_lot.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return "Access not granted"
    
    all_lots = ParkingLot.query.all()  # fetch all parking lots
    return render_template('admin_dashboard.html', lots=all_lots)

@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        return "Access not granted"
    
    return render_template('user_dashboard.html')

@app.route('/admin/lots/create', methods=['GET', 'POST'])
def create_lot():
    if request.method == 'POST':
        name = request.form.get("location_name")
        address = request.form.get("address")
        pin_code = request.form.get("pin_code")
        price = request.form.get("price")
        max_spots = request.form.get("max_spots")

        if not name or not address or not pin_code or not price or not max_spots:
            return redirect(url_for('create_lot'))

        try:
            max_spots = int(max_spots)
        except ValueError:
            return redirect(url_for('create_lot'))

        try:
            lot = ParkingLot(
                name=name,
                address=address,
                pin_code=pin_code,
                price=float(price),
                max_spots=max_spots
            )
            db.session.add(lot)
            db.session.commit()

            # Create spots
            for i in range(1, max_spots + 1):
                print(f"Creating spot {i} for lot {lot.id}")  # Debug print
                spot = ParkingSpot(
                    lot_id=lot.id,
                    spot_number=i,
                    status='A'
                )
                db.session.add(spot)

            db.session.commit()
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            print("Error creating lot:", e)
            return redirect(url_for('create_lot'))

    return render_template('create_lot.html')



@app.route('/admin/lots/delete/<int:lot_id>', methods=['POST'])
def delete_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    try:
        # Delete all associated spots first
        ParkingSpot.query.filter_by(lot_id=lot.id).delete()

        # Then delete the lot itself
        db.session.delete(lot)
        db.session.commit()
    except Exception as e:
        print("Error deleting lot:", e)

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/lots/<int:lot_id>/spots')
def view_spots(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
    return render_template('view_spots.html', lot=lot, spots=spots)


if __name__ == "__main__":
    app.run(debug=True)  # debug=True enables auto-reload and error details