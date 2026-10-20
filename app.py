from flask import Flask, request, jsonify,session, redirect, url_for,send_from_directory, session,send_file,after_this_request
from flask_cors import CORS
import mysql.connector
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME,SECRET_KEY
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_session import Session
import secrets
import re,csv
from io import StringIO
from datetime import datetime
import os


print("Testing Python Print")
app = Flask(__name__, static_folder="../frontend/static", template_folder="../frontend")
print("Static folder:", os.path.abspath(app.static_folder))

CORS(app, supports_credentials=True)


# Configure session storage
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Required for cross-origin cookies
app.config['SESSION_COOKIE_SECURE'] = True  # Use HTTPS for cookies (set to False for local testing)
app.config['SECRET_KEY'] = '7767473a6cd39e60a2e7599eed78334c3d9bdab913cdf585' 
Session(app)

# Define public routes
PUBLIC_ROUTES = ['api_login', 'register_user', 'login',None]  

@app.before_request
def before_request_logic():
    print("Request Path:", request.path)
    print("Request Endpoint:", request.endpoint)
    print("Session:", session)
    print(f"Requested URL: {request.url}")
    print(f"Request Method: {request.method}")
    print(f"Session: {session}")

    # Allow OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers["Access-Control-Allow-Origin"] = "http://127.0.0.1:5500"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    # Allow access to public routes
    if request.endpoint in PUBLIC_ROUTES:
        print("Public route accessed.")
        return

    # Enforce session check for private API routes
    if request.path.startswith('/api') and 'user_id' not in session:
        print("Unauthorized API request.")
        return jsonify({"error": "Unauthorized access"}), 401




# Database Connection
def get_db_connection():
    try:
        db = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        print(f"Database connected successfully")
        return db
    except mysql.connector.Error as err:
        print(f"Database connection error: {str(err)}")
        return None



# Test Database Connection
@app.route('/dbtest', methods=['GET'])
def db_test():
    try:
        db = get_db_connection()
        if db is None:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT DATABASE();")
        current_db = cursor.fetchone()
        cursor.close()
        db.close()
        return f"Connected to database: {current_db[0]}"
    except Exception as e:
        return jsonify({"error": "An error occurred while connecting to the database"}), 500
    
# Home Endpoint
@app.route('/')
def home():
    return send_from_directory(app.template_folder, 'index.html')

# Serve the register page 
@app.route('/register', methods=['GET'])
def serve_register():
    return send_from_directory(app.template_folder, 'register.html')

@app.route('/login', methods=['GET'])
def serve_login():
    return send_from_directory(app.template_folder, 'login.html')

@app.route('/resetpassword', methods=['GET'])
def serve_resetpassword():
    return send_from_directory(app.template_folder, 'reset-password.html')


@app.route('/dashboard', methods=['GET'])
def serve_dashboardpage():
    if 'user_id' not in session:
        return redirect('/login')
    return send_from_directory(app.template_folder, 'dashboard.html') 

@app.route('/expenseform', methods=['GET'])
def serve_expenseformpage():
    if 'user_id' not in session:
        return redirect('/login')
    return send_from_directory(app.template_folder, 'expense_form.html')

@app.route('/report', methods=['GET'])
def serve_reportpage():
    if 'user_id' not in session:
        return redirect('/login')
    return send_from_directory(app.template_folder, 'report.html')
  


# Fetch Predefined Categories
@app.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        db = get_db_connection()
        if db is None:
            return jsonify({"error": "Database connection failed"}), 500
        
        # Create a cursor using dictionary=True for fetching results as key-value pairs
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT name FROM categories")
        categories = [row[0] for row in cursor.fetchall()]
        cursor.close()
        db.close()
        return jsonify(categories), 200
    except Exception as e:
        return jsonify({"error": "An error occurred while fetching categories"}), 500
# Predefined Categories End 

# Add an Expense
@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.json
    user_id = session.get('user_id')
    
    # Check if user_id is present in session
    if not user_id:
        return jsonify({"message": "Add your expense! user_id is not found"}), 200

    try:
        # Retrieve expense details from the POST data
        expense_date = data.get('date')
        category = data.get('category').upper()
        description = data.get('description', '')
        amount = data.get('amount')

        # Check if all required fields are provided
        if not expense_date or not category or not amount:
            return jsonify({"message": "Missing required fields (date, category, or amount)"}), 400
        
        # Get the database connection
        db = get_db_connection()
        if db is None:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = db.cursor()

        # Insert the expense into the expenses table
        query = """
            INSERT INTO expenses (user_id, date, category, description, amount)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, expense_date, category, description, amount))

        # Update the spent_amount for the corresponding category in the budget_goals table
        update_query = """
            UPDATE budget_goals
            SET spent_amount = spent_amount + %s
            WHERE user_id = %s AND category = %s
        """
        cursor.execute(update_query, (amount, user_id, category))

        # If no rows were affected (i.e., no existing budget goal for that category), create a new one
        if cursor.rowcount == 0:
            # Here we assume the initial spent_amount is 0 and the user has a budget goal set.
            insert_budget_query = """
                INSERT INTO budget_goals (user_id, category, budget_goal, spent_amount)
                VALUES (%s, %s, 0, %s)  # Default budget_goal can be set as 0 or any default value you want
            """
            cursor.execute(insert_budget_query, (user_id, category, amount))

        # Check the updated spent_amount and budget_goal to determine the status
        status_check_query = """
            SELECT spent_amount, budget_goal FROM budget_goals
            WHERE user_id = %s AND category = %s
        """
        cursor.execute(status_check_query, (user_id, category))
        budget_data = cursor.fetchone()

        if budget_data:
            spent_amount = budget_data[0]
            budget_goal = budget_data[1]
            
            # Check if the user is over budget and update the status
            if spent_amount > budget_goal:
                status = 'Over Budget'
            else:
                status = 'On Track'

            # Update the status in the budget_goals table
            status_update_query = """
                UPDATE budget_goals
                SET status = %s
                WHERE user_id = %s AND category = %s
            """
            cursor.execute(status_update_query, (status, user_id, category))

        db.commit()
        cursor.close()
        db.close()

        return jsonify({"message": "Expense added successfully!"}), 201  # Successfully added

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
# Add User Expenses End - API Working


# Retrieve User Expenses 
@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    # Ensure the user is logged in by checking session
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized access. Please log in."}), 401
    
    user_id = session['user_id']  # Retrieve user_id from the session
    
    try:
        db = get_db_connection()
        if db is None:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = db.cursor()
        # Query expenses for the logged-in user
        cursor.execute("SELECT * FROM expenses WHERE user_id = %s", (int(user_id),))
        expenses = cursor.fetchall()

        if not expenses:
            return jsonify({"message": "Add your expense!"}), 200  # No expenses found for the user
        
        # If expenses are found, map them to a JSON-friendly format
        result = [
            {
                "id": expense[0],
                "user_id": expense[1],
                "date": expense[2].isoformat(),  # Convert date to ISO 8601 format
                "category": expense[3],
                "description": expense[4],
                "amount": float(expense[5]),  # Explicitly cast amount to float
                "created_at": expense[6].isoformat() if expense[6] else None,  # Handle created_at
            }
            for expense in expenses
        ]

        cursor.close()
        db.close()

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# Retrieve User Expenses End - API Working


#Delete expense
@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized access. Please log in."}), 401

    user_id = session['user_id']

    try:
        db = get_db_connection()
        if db is None:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = db.cursor()

        # Check if the expense exists and belongs to the user
        cursor.execute("SELECT * FROM expenses WHERE id = %s AND user_id = %s", (expense_id, user_id))
        expense = cursor.fetchone()

        if not expense:
            return jsonify({"message": "Expense not found or not authorized to delete"}), 404

        # Get the category and amount of the expense
        category = expense[3]  # 'category' is the 4th field in 'expenses' table
        amount = expense[5]    # 'amount' is the 6th field in 'expenses' table

        # Start a transaction
        cursor.execute("BEGIN")

        # Delete the expense from the 'expenses' table
        cursor.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))

        # Update the 'spent_amount' in the 'budget_goals' table
        update_query = """
            UPDATE budget_goals
            SET spent_amount = GREATEST(spent_amount - %s, 0)  # Avoid negative spending
            WHERE user_id = %s AND category = %s
        """
        cursor.execute(update_query, (amount, user_id, category))

        # After deleting, we need to check the new spent_amount and update the status
        status_check_query = """
            SELECT spent_amount, budget_goal FROM budget_goals
            WHERE user_id = %s AND category = %s
        """
        cursor.execute(status_check_query, (user_id, category))
        budget_data = cursor.fetchone()

        if budget_data:
            spent_amount = budget_data[0]
            budget_goal = budget_data[1]
            
            # Check if the user is over budget and update the status
            if spent_amount > budget_goal:
                status = 'Over Budget'
            else:
                status = 'On Track'

            # Update the status in the budget_goals table
            status_update_query = """
                UPDATE budget_goals
                SET status = %s
                WHERE user_id = %s AND category = %s
            """
            cursor.execute(status_update_query, (status, user_id, category))

        # Commit the transaction
        db.commit()

        cursor.close()
        db.close()

        return jsonify({"message": "Expense deleted successfully, and budget goal updated!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#Update Expense
@app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
def update_expense(expense_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized access. Please log in."}), 401

    user_id = session['user_id']
    data = request.json

    try:
        db = get_db_connection()
        if db is None:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = db.cursor()

        # Check if the expense exists and belongs to the user
        cursor.execute("SELECT * FROM expenses WHERE id = %s AND user_id = %s", (expense_id, user_id))
        expense = cursor.fetchone()

        if not expense:
            return jsonify({"message": "Expense not found or not authorized to update"}), 404

        # Extract new data from request
        expense_date = data.get('date', expense[2])  # Default to current value if not provided
        category = data.get('category', expense[3]).upper()  # Convert category to uppercase
        description = data.get('description', expense[4])
        new_amount = data.get('amount', expense[5])

        # Ensure required fields are present
        if not expense_date or not category or not new_amount:
            return jsonify({"message": "Missing required fields (date, category, or amount)"}), 400

        # Calculate the difference in the amounts (old - new)
        old_amount = expense[5]
        amount_difference = new_amount - old_amount

        # Update the expense record in the 'expenses' table
        query = """
            UPDATE expenses 
            SET date = %s, category = %s, description = %s, amount = %s
            WHERE id = %s AND user_id = %s
        """
        cursor.execute(query, (expense_date, category, description, new_amount, expense_id, user_id))

        # Update the spent_amount in the 'budget_goals' table for the old category
        if old_amount != new_amount:
            # Decrease the spent amount for the old category (if the category is changed or the amount is reduced)
            update_old_category_query = """
                UPDATE budget_goals
                SET spent_amount = GREATEST(spent_amount - %s, 0)
                WHERE user_id = %s AND category = %s
            """
            cursor.execute(update_old_category_query, (old_amount, user_id, expense[3]))  # old category

            # Increase the spent amount for the new category
            update_new_category_query = """
                UPDATE budget_goals
                SET spent_amount = spent_amount + %s
                WHERE user_id = %s AND category = %s
            """
            cursor.execute(update_new_category_query, (new_amount, user_id, category))  # new category

        # After updating the spent amounts, check the status of the budget goal
        status_check_query = """
            SELECT spent_amount, budget_goal FROM budget_goals
            WHERE user_id = %s AND category = %s
        """
        cursor.execute(status_check_query, (user_id, category))
        budget_data = cursor.fetchone()

        if budget_data:
            spent_amount = budget_data[0]
            budget_goal = budget_data[1]
            
            # Check if the user is over budget and update the status
            if spent_amount > budget_goal:
                status = 'Over Budget'
            else:
                status = 'On Track'

            # Update the status in the budget_goals table
            status_update_query = """
                UPDATE budget_goals
                SET status = %s
                WHERE user_id = %s AND category = %s
            """
            cursor.execute(status_update_query, (status, user_id, category))

        db.commit()

        cursor.close()
        db.close()

        return jsonify({"message": "Expense updated successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Analytics Logic
@app.route('/api/analytics', methods=['GET'])
def analytics():
    user_id = session.get('user_id')  # Get user ID from request query
    start_date = request.args.get('start_date')  # Optional start date filter
    end_date = request.args.get('end_date')  # Optional end date filter
    category = request.args.get('category')

    if not user_id:
        return jsonify({"error": "'user_id' is required"}), 400

    try:
        # Establish database connection
        db = get_db_connection()  # Assuming this is your function for DB connection
        if db is None:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = db.cursor(dictionary=True)  # Using dictionary=True for easier row access

        # Construct the query
        query = "SELECT * FROM expenses WHERE user_id = %s"
        params = [user_id]

        if category:
            query += " AND category = %s"
            params.append(category)

        if start_date:
            query += " AND date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND date <= %s"
            params.append(end_date)

        # Execute the query
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        if not rows:
            return jsonify({"message": "No expenses found for this user."}), 200 

        # Transform the results into a JSON-friendly format
        expenses = []
        for row in rows:
            expenses.append({
                "date": row['date'],
                "category": row['category'],
                "description": row['description'],
                "amount": float(row['amount'])  # Explicitly casting to float for consistency
            })

        # Close the cursor and connection after use
        cursor.close()
        db.close()

        return jsonify(expenses), 200

    except Exception as e:
        # Handle any exception that occurs during the process
        return jsonify({"error": str(e)}), 500


# User Registration API

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    security_question1 = data.get('security_question1')
    security_answer1 = data.get('security_answer1')
    security_answer1_lower=security_answer1.lower()
    security_question2 = data.get('security_question2')
    security_answer2 = data.get('security_answer2')
    security_answer2_lower=security_answer2.lower()
   

    # Basic validation
    if not username or not email or not password or not security_question1 or not security_answer1 or not security_question2 or not security_answer2:
        return jsonify({"error": "All fields are required"}), 400

    # Validate email format
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not re.match(email_regex, email):
        return jsonify({"error": "Invalid email format"}), 400

    # Validate password strength
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters long"}), 400

    try:
        # Hash password and security answers
        password_hash = generate_password_hash(password)
        security_answer1_hash = generate_password_hash(security_answer1_lower)
        security_answer2_hash = generate_password_hash(security_answer2_lower)

        db = get_db_connection()  # Assuming get_db_connection() returns a valid DB connection
        if db is None:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = db.cursor(dictionary=True)

        # Check if the email already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            return jsonify({"error": "Email is already registered"}), 409  # Conflict

        # Insert the new user into the database, including the security questions and their hashed answers
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, security_question1, security_answer1_hash, security_question2, security_answer2_hash) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (username, email, password_hash, security_question1, security_answer1_hash, security_question2, security_answer2_hash)
        )

        db.commit()
        cursor.close()
        db.close()

        return jsonify({"message": "User registered successfully!"}), 201

    except Exception as e:
        print("Registration error:", e)  # Log the full exception
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

#End - Registration API 

# User Login API
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        db = get_db_connection()  
        if db is None:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        print("Database user fetched:", user)

        if not user or not check_password_hash(user['password_hash'], password):
            print("Invalid credentials for email:", email)
            return jsonify({"error": "Invalid email or password"}), 401

        # Save user info in the session
        session['user_id'] = user['id']
        session['username'] = user['username']
        print("Session set for user_id:", session['user_id'])

        cursor.close()
        db.close()
        return jsonify({"message": "Login successful", "user": {"id": user['id'], "username": user['username']}}), 200

    except Exception as e:
        print("Login error:", e)
        return jsonify({"error": str(e)}), 500

 #End - Login API    


# User Logout API
@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        
        session.clear()  
        # Optionally, you can use session.pop('key', None) to remove specific keys from the session.     
        return jsonify({"message": "Logout successful"}), 200

    except Exception as e:
        print("Logout error:", e)
        return jsonify({"error": str(e)}), 500
    
 #End - Logout API Working 


# Check Session API
@app.route('/api/check_session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({"message": "Session active", "user_id": session['user_id']}), 200
    return jsonify({"error": "Session expired"}), 401

# Function to check if the security answer matches the hash stored in the database
def check_security_answer(stored_answer_hash, provided_answer):
    return check_password_hash(stored_answer_hash, provided_answer)

#Reset Password Api
@app.route('/api/reset_password', methods=['POST'])
def reset_password():
    data = request.json  # Get the data sent in the POST request
    email = data.get('email')
    security_answer1 = data.get('security_answer1')
    security_answer2 = data.get('security_answer2')
    security_answer1_lower = security_answer1.lower()
    security_answer2_lower = security_answer2.lower()
    
    new_password = data.get('new_password')

    # Validate the data
    if not email or not security_answer1 or not security_answer2 or not new_password:
        return jsonify({"error": "All fields are required"}), 400

    db = None
    cursor = None
    try:
        
        # Get database connection
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        

        if not user:
            return jsonify({"error": "Email not found"}), 404

        # If the user is logged in, check session
        if 'user_id' in session:
            if session['user_id'] != user['id']:
                return jsonify({"error": "You are not authorized to reset this password"}), 403
            # Proceed with password reset for logged-in user
            password_hash = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s", (password_hash, email))
            db.commit()
            return jsonify({"message": "Password reset successfully!"}), 200
        else:
            
            is_correct1 = check_password_hash(user['security_answer1_hash'], security_answer1_lower)
            is_correct2 = check_password_hash(user['security_answer2_hash'], security_answer2_lower)
            # Check security questions
            if (is_correct1 and is_correct2):
                print("The answer is correct.")
                # If answers are correct, reset password
                password_hash = generate_password_hash(new_password)
                cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s", (password_hash, email))
                db.commit()
                return jsonify({"message": "Password reset successfully!"}), 200
            else:
                return jsonify({"error": "Incorrect security answers"}), 400
    except Exception as e:
        # Log the error for debugging
        print(f"Error resetting password: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()
#Api Reset Password - End


#Export CSV - Start
@app.route('/api/export', methods=['GET'])
def export_csv():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized access"}), 401

    category = request.args.get('category')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = "SELECT date, category, description, amount FROM expenses WHERE user_id = %s"
    params = [user_id]

    if category:
        query += " AND category = %s"
        params.append(category)
    if start_date:
        query += " AND date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND date <= %s"
        params.append(end_date)

    try:
        connection = get_db_connection()
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        if not rows:
            return jsonify({"message": "No expenses found to export"}), 200

        # Specify the required fieldnames
        fieldnames = ["date", "category", "description", "amount"]

        # Generate a secure CSV file name
        csv_file = f"expenses_user_{user_id}.csv"

        # Write data to CSV
        with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        @after_this_request
        def cleanup(response):
            try:
                os.remove(csv_file)  # Delete the file after sending it
            except Exception as e:
                print(f"Error deleting file {csv_file}: {e}")
            return response

        return send_file(csv_file, as_attachment=True, mimetype='text/csv')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        connection.close()


#Export CSV - End

#Set Budget
@app.route('/api/set_budget', methods=['POST'])
def set_budget():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401

    data = request.json
    budget_amount = data.get('budget')

    if not budget_amount or float(budget_amount) < 0:
        return jsonify({"error": "Invalid budget amount"}), 400

    try:
        db = get_db_connection()
        cursor = db.cursor()

        # Check if budget already exists
        cursor.execute("SELECT id FROM budget WHERE user_id = %s", (user_id,))
        existing_budget = cursor.fetchone()

        if existing_budget:
            # Update existing budget
            cursor.execute("UPDATE budget SET amount = %s WHERE user_id = %s", (budget_amount, user_id))
        else:
            # Insert new budget
            cursor.execute("INSERT INTO budget (user_id, amount) VALUES (%s, %s)", (user_id, budget_amount))

        db.commit()
        cursor.close()
        db.close()

        return jsonify({"message": "Budget set successfully!", "budget": f"{float(budget_amount):.2f}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Get Budget Status
@app.route('/api/budget_status', methods=['GET'])
def get_budget_status():
    # Ensure the user is logged in by checking session
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized access. Please log in."}), 401
    
    user_id = session['user_id']

    try:
        db = get_db_connection()
        if db is None:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = db.cursor(dictionary=True)
        
        # Compute the total expenses using SUM query
        cursor.execute("SELECT COALESCE(SUM(amount), 0) AS total_expenses FROM expenses WHERE user_id = %s", (user_id,))
        expense_result = cursor.fetchone()
        total_expenses = float(expense_result['total_expenses'])
        
        # Fetch the user's budget from the budget table
        cursor.execute("SELECT amount FROM budget WHERE user_id = %s", (user_id,))
        budget_result = cursor.fetchone()
        budget = float(budget_result['amount']) if budget_result else 0.0
        
        remaining_budget = budget - total_expenses
        status = "Within Budget" if remaining_budget >= 0 else "Over Budget"
        
        cursor.close()
        db.close()
        
        return jsonify({
            "budget": f"{budget:.2f}",
            "total_expenses": f"{total_expenses:.2f}",
            "remaining_budget": f"{remaining_budget:.2f}",
            "status": status
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# Get Budget Status End

#Reset Budget 
@app.route('/api/reset_budget', methods=['POST'])
def reset_budget():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401

    try:
        db = get_db_connection()
        cursor = db.cursor()

        # Reset budget for the user
        cursor.execute("UPDATE budget SET amount = 0 WHERE user_id = %s", (user_id,))
        db.commit()
        cursor.close()
        db.close()

        return jsonify({"message": "Budget reset successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
#Reset Budget End

#Set Budget Goal
@app.route('/api/set_budget_goal', methods=['POST'])
def set_budget_goal():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401

    data = request.json
    category = data.get('category')
    budget_goal = data.get('budget_goal')

    if not category or not budget_goal or float(budget_goal) <= 0:
        return jsonify({"error": "Invalid input"}), 400

    try:
        db = get_db_connection()
        cursor = db.cursor()

        # Check if the goal already exists for this user and category
        cursor.execute("SELECT id FROM budget_goals WHERE user_id = %s AND category = %s", (user_id, category))
        existing_goal = cursor.fetchone()

        if existing_goal:
            # Update the existing budget goal
            cursor.execute("UPDATE budget_goals SET budget_goal = %s WHERE user_id = %s AND category = %s", 
                           (budget_goal, user_id, category))
        else:
            # Insert new goal
            cursor.execute("INSERT INTO budget_goals (user_id, category, budget_goal) VALUES (%s, %s, %s)", 
                           (user_id, category, budget_goal))

        db.commit()
        cursor.close()
        db.close()

        return jsonify({"message": "Budget goal set successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#end

#Fetch Budget Goal
@app.route('/api/get_budget_goals', methods=['GET'])
def get_budget_goals():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401

    try:
        db = get_db_connection()
        cursor = db.cursor()

        # Fetch budget goals for the user
        cursor.execute("SELECT id, category, budget_goal, spent_amount, status FROM budget_goals WHERE user_id = %s", (user_id,))
        goals = cursor.fetchall()

        # Format the results
        result = [{"id": goal[0],"category": goal[1], "budget_goal": goal[2], "spent_amount": goal[3], "status": goal[4]} for goal in goals]

        db.close()
        return jsonify({"budget_goals": result}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#end

# Delete budget goal API
@app.route('/api/delete_budget_goal/<int:goal_id>', methods=['DELETE'])
def delete_budget_goal(goal_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized access. Please log in."}), 401

    user_id = session['user_id']
    

    try:
        db = get_db_connection()
        if db is None:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = db.cursor()

        # Check if the goal exists and belongs to the user
        cursor.execute("SELECT * FROM budget_goals WHERE id = %s AND user_id = %s", (goal_id, user_id))
        goal = cursor.fetchone()

        if not goal:
            print(f"Goal not found or not authorized to delete: goal_id={goal_id}, user_id={user_id}")  # Debugging log
            return jsonify({"error": "Goal not found or not authorized to delete"}), 404

        print(f"Found goal to delete: {goal}")  # Debugging log

        # Delete the goal from the 'budget_goals' table
        cursor.execute("DELETE FROM budget_goals WHERE id = %s AND user_id = %s", (goal_id, user_id))

        
        db.commit()        
        cursor.close()
        db.close()

        return jsonify({"message": "Budget goal deleted successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


#end



# Run the Application
if __name__ == "__main__":
    app.run(debug=True)

