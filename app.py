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



@app.route('/logout', methods=['GET','POST'])
def logout():
    session.clear()
    return redirect('/')



@app.route('/admin/lots/create', methods=['GET', 'POST'])
def create_parking_lot():
    if session.get('role') != 'admin':
        return redirect('/login')

    if request.method == 'POST':
        location = request.form['location_name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        price = float(request.form['price'])
        max_spots = int(request.form['max_spots'])

        # Create the parking lot
        new_lot = ParkingLot(
            name=location,
            address=address,
            pin_code=pin_code,
            price=price,
            max_spots=max_spots
        )
        db.session.add(new_lot)
        db.session.commit() 

        for i in range(1, max_spots + 1):
            spot = ParkingSpot(
                lot_id=new_lot.id,
                spot_number=i,  
                status='A'
            )
            db.session.add(spot)

        db.session.commit()

        return redirect('/admin/dashboard')

    return render_template('create_lot.html')


@app.route('/admin/lots/edit/<int:lot_id>', methods=['GET', 'POST'])
def edit_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    old_max_spots = lot.max_spots

    if request.method == 'POST':
        # Get updated data from form
        lot.location_name = request.form['location_name']
        lot.address = request.form['address']
        lot.pin_code = request.form['pin_code']
        lot.price = request.form['price']

        new_max_spots = int(request.form['max_spots'])

        # Update the lot's max_spots
        lot.max_spots = new_max_spots

        # Handle spot changes
        if new_max_spots > old_max_spots:
            # Add new spots
            for i in range(old_max_spots + 1, new_max_spots + 1):
                new_spot = ParkingSpot(lot_id=lot.id, spot_number=i, status='A')
                db.session.add(new_spot)

        elif new_max_spots < old_max_spots:
            # Get spots beyond new limit
            extra_spots = ParkingSpot.query.filter(
                ParkingSpot.lot_id == lot.id,
                ParkingSpot.spot_number > new_max_spots
            ).all()

            # Only delete if all extra spots are available
            if any(spot.status == 'O' for spot in extra_spots):
                flash('Cannot reduce spots. Some higher-numbered spots are still occupied.', 'danger')
                return redirect(url_for('edit_lot', lot_id=lot.id))

            for spot in extra_spots:
                db.session.delete(spot)

        # Save all changes
        db.session.commit()
        flash('Lot updated successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_lot.html', lot=lot)



@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect('/login')

    parking_lots = ParkingLot.query.all() #fetch all parking lots
    return render_template('admin_dashboard.html', parking_lots=parking_lots)



@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        return "Access not granted"
    
    return render_template('user_dashboard.html')


@app.route('/admin/users')
def admin_view_users():
    users = User.query.filter_by(role='user').all()  # Only normal users

    user_data = []

    for user in users:
        # Find active reservation (where leaving_time is None)
        active_reservation = Reservation.query.filter_by(user_id=user.id, leaving_time=None).first()
        
        if active_reservation:
            spot = ParkingSpot.query.get(active_reservation.spot_id)
            lot = ParkingLot.query.get(spot.lot_id)
            user_data.append({
                'fullname': user.fullname,
                'username': user.username,
                'phone': user.phone_number,
                'spot_number': spot.spot_number,
                'lot_name': lot.location_name,
                'status': 'Occupied'
            })
        else:
            user_data.append({
                'fullname': user.fullname,
                'username': user.username,
                'phone': user.phone_number,
                'spot_number': '-',
                'lot_name': '-',
                'status': 'No Active Booking'
            })

    return render_template('admin_users.html', users=user_data)


@app.route('/admin/lots/delete/<int:lot_id>', methods=['POST'])
def delete_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    # Check if any spot is occupied
    occupied_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').all()

    if occupied_spots:
        # Use flash to send error message
        flash('You can delete a lot only if all its spots are empty.', 'danger')
        return redirect(url_for('admin_dashboard'))

    try:
        # Delete all associated spots first
        ParkingSpot.query.filter_by(lot_id=lot.id).delete()

        # Then delete the lot itself
        db.session.delete(lot)
        db.session.commit()
        flash('Parking lot deleted successfully.', 'success')
    except Exception as e:
        print("Error deleting lot:", e)
        flash('Something went wrong while deleting the lot.', 'danger')

    return redirect(url_for('admin_dashboard'))




@app.route('/admin/lots/<int:lot_id>/spots')
def view_spots(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
    return render_template('view_spots.html', lot=lot, spots=spots)


if __name__ == "__main__":
    app.run(debug=True)  # debug=True enables auto-reload and error details