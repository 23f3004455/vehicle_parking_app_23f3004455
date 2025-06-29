from flask import Flask, flash, render_template, redirect, request, session, url_for
from datetime import datetime, timedelta
from models.models import db, User, ParkingLot, ParkingSpot, Reservation


app = Flask(__name__)
app.secret_key = 'secret-key' 

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


with app.app_context():  
    db.create_all()
    admin = User.query.filter_by(username='admin').first()
    
    if not admin: 
        admin_user = User(
            username='admin',
            password='admin', 
            fullname='Administrator',
            address='Admin Office',
            pin_code='000000',
            phone_number='0000000000',
            role = 'admin'
        )
        db.session.add(admin_user)
        db.session.commit()
    else:
        if admin.role != 'admin':
            admin.role = 'admin'
            db.session.commit()



@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/register', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        fullname = request.form['fullname']
        address = request.form['address']
        pin_code = request.form['pin_code']
        phone_number = request.form['phone_number']

        existing_user = User.query.filter_by(username = username).first()
        if existing_user: 
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
        
        return redirect('/login') 
    
    return render_template('register.html')


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


@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect('/login')

    parking_lots = ParkingLot.query.all()
    return render_template('admin_dashboard.html', parking_lots=parking_lots)


@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        return "Access not granted"
    
    return render_template('user_dashboard.html')


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
    lot = ParkingLot.query.get(lot_id)
    if lot is None:
        return "Parking Lot not found"
    old_max_spots = lot.max_spots

    if request.method == 'POST':
        lot.location_name = request.form['location_name']
        lot.address = request.form['address']
        lot.pin_code = request.form['pin_code']
        lot.price = request.form['price']
        new_max_spots = int(request.form['max_spots'])

        lot.max_spots = new_max_spots

        if new_max_spots > old_max_spots:
            for i in range(old_max_spots + 1, new_max_spots + 1):
                new_spot = ParkingSpot(lot_id=lot.id, spot_number=i, status='A')
                db.session.add(new_spot)
        elif new_max_spots < old_max_spots:
            extra_spots = ParkingSpot.query.filter(ParkingSpot.lot_id == lot.id, ParkingSpot.spot_number > new_max_spots).all()
            if any(spot.status == 'O' for spot in extra_spots):
                flash('Cannot reduce spots. Some higher-numbered spots are still occupied.', 'danger')
                return redirect(url_for('edit_lot', lot_id=lot.id))
            for spot in extra_spots:
                db.session.delete(spot)

        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_lot.html', lot=lot)


@app.route('/admin/users')
def admin_view_users():
    users = User.query.filter_by(role='user').all()
    user_data = []
    for user in users:
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
    lot = ParkingLot.query.get(lot_id)
    if lot is None:
        return "Parking Lot not found"
    occupied_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').all()

    if occupied_spots:
        flash('You can delete a lot only if all its spots are empty.', 'danger')
        return redirect(url_for('admin_dashboard'))

    try:
        ParkingSpot.query.filter_by(lot_id=lot.id).delete()
        db.session.delete(lot)
        db.session.commit()
        flash('Parking lot deleted successfully.', 'success')
    except Exception as e:
        flash('Something went wrong while deleting the lot.', 'danger')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/lots/<int:lot_id>/spots')
def view_spots(lot_id):
    lot = ParkingLot.query.get(lot_id)
    if lot is None:
        return "Parking Lot not found"
    spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
    
    return render_template('view_spots.html', lot=lot, spots=spots)


@app.route('/admin/history')
def admin_history():
    if session.get('role') != 'admin':
        return redirect('/login')
    reservations = Reservation.query.order_by(Reservation.parking_time.desc()).all()
    history = []
    for res in reservations:
        user = User.query.get(res.user_id)
        spot = ParkingSpot.query.get(res.spot_id)
        lot = ParkingLot.query.get(spot.lot_id) if spot else None
        if res.leaving_time:
            time = res.leaving_time - res.parking_time
            total_minutes = int(time.total_seconds() // 60)
        else:
            total_minutes = None

        history.append({
        'user_fullname': user.fullname if user else 'N/A',
        'lot_name': lot.name if lot else 'N/A',
        'spot_number': spot.spot_number if spot else '-',
        'start_time': res.parking_time,
        'end_time': res.leaving_time if res.leaving_time else 'Still Parked',
        'duration': f"{total_minutes} mins" if total_minutes is not None else "N/A",
        'cost': res.cost if res.cost is not None else 0.0
        })
        
    return render_template('admin_history.html', history=history)


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
    spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
    if spot:
        spot.status = 'O'
        ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
        new_res = Reservation(
            user_id=session.get('user_id'),
            spot_id=spot.id,
            parking_time=ist_time
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
    reservation = Reservation.query.filter_by(
        user_id=session.get('user_id'),
        leaving_time=None
    ).first()
    if reservation:
        reservation.leaving_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
        spot = ParkingSpot.query.get(reservation.spot_id)
        spot.status = 'A' 
        time = reservation.leaving_time - reservation.parking_time
        total_minutes = int(time.total_seconds() // 60)

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



if __name__ == "__main__":
    app.run(debug=True) 