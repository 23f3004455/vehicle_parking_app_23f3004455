from flask import Flask, flash
from datetime import datetime, timedelta
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
                'lot_name': lot.name,
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


@app.route('/user/lots')
def user_lots():
    if session.get('role') != 'user':
        return redirect('/login')
    lots = ParkingLot.query.all()
    available_lots = []
    for lot in lots:
        available_count = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
        available_lots.append({
            'lot': lot,
            'available_count': available_count
        })
    return render_template('user_lots.html', available_lots=available_lots)


@app.route('/user/reserve/<int:lot_id>')
def reserve_spot(lot_id):
    if session.get('role') != 'user':
        return redirect('/login')
    # Find the first available spot
    spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
    if spot:
        spot.status = 'O'  # Mark spot as occupied
        now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)  # IST time
        new_res = Reservation(
            user_id=session.get('user_id'),
            spot_id=spot.id,
            parking_time=now_ist
        )
        db.session.add(new_res)
        db.session.commit()
        flash(f'Reserved spot {spot.spot_number} in lot {spot.lot.name}.', 'success')
    else:
        flash('No available spots in this lot.', 'danger')
    return redirect(url_for('user_dashboard'))


@app.route('/user/release')
def release_spot():
    if session.get('role') != 'user':
        return redirect('/login')
    # Find active reservation for the user
    reservation = Reservation.query.filter_by(
        user_id=session.get('user_id'),
        leaving_time=None
    ).first()
    if reservation:
        reservation.leaving_time = datetime.utcnow() + timedelta(hours=5, minutes=30)  # IST time
        spot = ParkingSpot.query.get(reservation.spot_id)
        spot.status = 'A'  # Make spot available again

        # Calculate total minutes
        delta = reservation.leaving_time - reservation.parking_time
        total_minutes = int(delta.total_seconds() // 60)

        # Get price per hour for the lot
        lot = ParkingLot.query.get(spot.lot_id)
        price_per_hour = lot.price
        total_cost = (total_minutes / 60) * price_per_hour
        reservation.cost = total_cost

        db.session.commit()
        flash(f'Released spot {spot.spot_number}. Total cost: ₹{total_cost:.2f}', 'success')
    else:
        flash('No active reservation found.', 'danger')
    return redirect(url_for('user_dashboard'))


@app.route('/user/history')
def user_history():
    if session.get('role') != 'user':
        return redirect('/login')
    
    reservations = Reservation.query.filter_by(user_id=session.get('user_id')).all()
    history_data = []
    for res in reservations:
        spot = ParkingSpot.query.get(res.spot_id)
        lot = ParkingLot.query.get(spot.lot_id) if spot else None
        history_data.append({
            'lot_name': lot.name if lot else 'N/A',
            'spot_number': spot.spot_number if spot else '-',
            'start_time': res.parking_time,
            'end_time': res.leaving_time if res.leaving_time else 'Still Parked',
            'cost': res.cost if res.cost is not None else 0.0
        })
    return render_template('user_history.html', history_data=history_data)



@app.route('/admin/history')
def admin_history():
    if session.get('role') != 'admin':
        return redirect('/login')
    reservations = Reservation.query.order_by(Reservation.parking_time.desc()).all()

    all_history = []
    for res in reservations:
        user = User.query.get(res.user_id)
        spot = ParkingSpot.query.get(res.spot_id)
        lot = ParkingLot.query.get(spot.lot_id) if spot else None

        if res.leaving_time:
            delta = res.leaving_time - res.parking_time
            total_minutes = int(delta.total_seconds() // 60)
        else:
            total_minutes = None

        all_history.append({
        'user_fullname': user.fullname if user else 'N/A',
        'lot_name': lot.name if lot else 'N/A',
        'spot_number': spot.spot_number if spot else '-',
        'start_time': res.parking_time,
        'end_time': res.leaving_time if res.leaving_time else 'Still Parked',
        'duration': f"{total_minutes} mins" if total_minutes is not None else "N/A",
        'cost': res.cost if res.cost is not None else 0.0
        })
        
    return render_template('admin_history.html', history=all_history)


if __name__ == "__main__":
    app.run(debug=True)  # debug=True enables auto-reload and error details