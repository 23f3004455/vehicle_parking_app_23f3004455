from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# User table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(8), nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    pin_code = db.Column(db.String(10))
    phone_number = db.Column(db.String(15), nullable=False)
    #User can have multiple reservations
    reservations = db.relationship('Reservation', backref='user') 
    #backref: Creates a user attribute on the Reservation model, allowing you to access the User object from a Reservation object

# Parking lot table
class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pin_code = db.Column(db.String(10), nullable=False)
    price = db.Column(db.Float, nullable=False)
    max_spots = db.Column(db.Integer, nullable=False)
    #Parking lot can have multiple spots
    spots = db.relationship('ParkingSpot', backref='lot') 
    #backref: Creates a lot attribute on the ParkingSpot model, allowing you to access the ParkingLot object from a ParkingSpot object.

# Parking spot table
class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key linking to parking lot
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    status = db.Column(db.String(1), nullable=False, default='A')  # A = Available, O = Occupied
    #Parking spot can have multiple reservations
    reservations = db.relationship('Reservation', backref='spot')

# Reservation table
class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key linking to parking spot
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
    # Foreign key linking to user
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parking_time = db.Column(db.DateTime, default=datetime.utcnow)
    leaving_time = db.Column(db.DateTime, nullable=True)
