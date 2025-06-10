from flask import Flask
from models.models import db, User, ParkingLot, ParkingSpot, Reservation


app = Flask(__name__)

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
            phone_number='0000000000'
        )
        # Add admin to database session
        db.session.add(admin_user)
        # Save changes to database
        db.session.commit()

@app.route('/')
def home():
    return "Welcome to the Vehicle Parking App!"

if __name__ == "__main__":
    app.run(debug=True)  # debug=True enables auto-reload and error details