from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import time
import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from bcrypt import hashpw, gensalt, checkpw
import boto3
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key') 

mock_orders = []

aws_session = boto3.Session(
    region_name=os.environ.get('AWS_REGION', 'ap-south-1')
)

dynamodb = aws_session.resource('dynamodb')
users_table = dynamodb.Table('PickleApp_Users')
products_table = dynamodb.Table('PickleApp_Products')
orders_table = dynamodb.Table('PickleApp_Orders')
cart_table = dynamodb.Table('PickleApp_Cart')

sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')

# SNS (Simple Notification Service)
sns = aws_session.client('sns')
def send_sns_message(phone_number, message):
    try:
        response = sns.publish(
            PhoneNumber=phone_number,
            Message=message
        )
        return response
    except Exception as e:
        print(f"SNS error: {e}")
        return None

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', "dileepexample@gmail.com")
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', "vcbx stsp yvgi dyhn")

def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        import smtplib
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, to_email, text)
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")

# EC2 (Elastic Compute Cloud)
ec2 = aws_session.resource('ec2')
def list_ec2_instances():
    try:
        instances = ec2.instances.all()
        return [instance.id for instance in instances]
    except Exception as e:
        print(f"EC2 error: {e}")
        return []



def load_users():
    with open('data/users.json', 'r') as f:
        users = json.load(f)
        # Migrate existing users to include address fields
        migrated = False
        for user in users:
            if 'street' not in user:
                user['street'] = ''
                migrated = True
            if 'city' not in user:
                user['city'] = ''
                migrated = True
            if 'pincode' not in user:
                user['pincode'] = ''
                migrated = True
            if 'country' not in user:
                user['country'] = 'India'
                migrated = True
        if migrated:
            save_users(users)
        return users

def save_users(users):
    with open('data/users.json', 'w') as f:
        json.dump(users, f, indent=2)

ORDERS_FILE = 'data/orders.json'

def load_orders():
    if not os.path.exists(ORDERS_FILE):
        return []
    with open(ORDERS_FILE, 'r') as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_orders(orders):
    with open(ORDERS_FILE, 'w') as f:
        json.dump(orders, f, indent=2)

sns_topic_arn = os.environ.get('SNS_TOPIC_ARN', 'srn-key')

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', "pickleshop@example.com")  # Update to your PickleApp email
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', "vcbx stsp yvgi dyhn")  # Update to your PickleApp app password


def get_user_by_email(email):
    # Try DynamoDB first
    try:
        response = users_table.get_item(Key={'email': email})
        if 'Item' in response:
            return response['Item'], 'dynamodb'
    except Exception as e:
        print(f"DynamoDB user fetch error: {e}")
    # Fallback to local file
    users = load_users()
    user = next((u for u in users if u['email'] == email), None)
    return user, 'local' if user else (None, None)

def save_user(user, mode):
    if mode == 'dynamodb':
        try:
            users_table.put_item(Item=user)
        except Exception as e:
            print(f"DynamoDB user save error: {e}")
    elif mode == 'local':
        users = load_users()
        users.append(user)
        save_users(users)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/products')
def products_page():
    return render_template('products.html')

@app.route('/products/<int:product_id>')
def product_detail(product_id):
    return render_template('product_detail.html', product_id=product_id)

@app.route('/products/map')
def products_map():
    return render_template('products_map.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/checkout')
def checkout():
    if not session.get('user_email'):
        flash("Please log in to proceed with checkout.", "danger")
        return redirect(url_for('login', next='/checkout'))
    return render_template('checkout.html')

@app.route('/order-confirmation')
def order_confirmation():
    if not session.get('user_email'):
        flash("Please log in to view order confirmation.", "danger")
        return redirect(url_for('login', next='/order-confirmation'))
    return render_template('order_confirmation.html')

@app.route('/orders')
def orders():
    if not session.get('user_email'):
        flash("Please log in to view your orders.", "danger")
        return redirect(url_for('login', next='/orders'))
    return render_template('orders.html')

@app.route('/orders/<int:order_id>')
def order_detail(order_id):
    if not session.get('user_email'):
        flash("Please log in to view order details.", "danger")
        return redirect(url_for('login', next=f'/orders/{order_id}'))
    return render_template('order_detail.html', order_id=order_id)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        phone = request.form['phone']
        if not name or not email or not password or not confirm_password or not phone:
            flash("All fields are mandatory! Please fill out the entire form.", "danger")
            return redirect(url_for('register'))
        if password != confirm_password:
            flash("Passwords do not match! Please try again.", "danger")
            return redirect(url_for('register'))
        user, mode = get_user_by_email(email)
        if user:
            flash("User already exists! Please log in.", "info")
            return redirect(url_for('login'))
        hashed_password = hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')
        user_obj = {
            'email': email,
            'name': name,
            'password': hashed_password,
            'phone': phone,
            'login_count': 0,
            'street': '',
            'city': '',
            'pincode': '',
            'country': 'India',
            'registration_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_user(user_obj, 'dynamodb' if mode == 'dynamodb' else 'local')
        try:
            sns.publish(
                TopicArn=sns_topic_arn,
                Message=f'New user registered: {name} ({email})',
                Subject='New User Registration'
            )
        except Exception as e:
            print(f"SNS error: {e}")
        try:
            send_email(email, "Welcome to PickleApp!", f"Hi {name},\n\nThank you for registering at PickleApp!")
        except Exception as e:
            print(f"Email error: {e}")
        session['user_email'] = email
        session['user_name'] = name
        session['phone'] = phone
        flash("Registration successful!", "success")
        return redirect(url_for('profile'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if not email or not password:
            flash("Email and password are required!", "danger")
            return redirect(url_for('login'))
        user, mode = get_user_by_email(email)
        if not user or not checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            flash("Incorrect email or password! Please try again.", "danger")
            return redirect(url_for('login'))
        if mode == 'dynamodb':
            try:
                users_table.update_item(
                    Key={'email': email},
                    UpdateExpression='SET login_count = if_not_exists(login_count, :zero) + :inc',
                    ExpressionAttributeValues={':inc': 1, ':zero': 0}
                )
            except Exception as e:
                print(f"DynamoDB update error: {e}")
        elif mode == 'local':
            users = load_users()
            for u in users:
                if u['email'] == email:
                    u['login_count'] = u.get('login_count', 0) + 1
            save_users(users)
        session['user_email'] = user['email']
        session['user_name'] = user['name']
        session['phone'] = user.get('phone', '')
        flash("Login successful!", "success")
        next_page = request.form.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('profile'))
    return render_template('login.html')

@app.route('/profile')
def profile():
    if not session.get('user_email'):
        flash("Please log in to view your profile.", "danger")
        return redirect(url_for('login'))
    users = load_users()
    user = next((u for u in users if u['email'] == session['user_email']), None)
    if not user:
        flash("User not found! Please log in again.", "danger")
        return redirect(url_for('login'))
    return render_template('profile.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))

@app.route('/browse')
def browse():
    return render_template('browse.html')

@app.route('/artisan-handbook')
def artisan_handbook():
    return render_template('artisan_handbook.html')

@app.route('/seller-forum')
def seller_forum():
    return render_template('seller_forum.html')


def get_products_by_category(category):
    img_map = {
        'Chicken Pickle': '/static/img/chicken-pickle.jpg',
        'Fish Pickle': '/static/img/fish-pickle.jpg',
        'Gongura Mutton': '/static/img/gongura-mutton-pickle.webp',
        'Mutton Pickle': '/static/img/mutton-pickle.jpg',
        'Prawns Pickle': '/static/img/prawn-pickle.webp',
        'Chicken Pickle (Gongura)': '/static/img/gongura-chicken-pickle.jpg',
        'Traditional Mango Pickle': '/static/img/mango-pickle.jpg',
        'Zesty Lemon Pickle': '/static/img/zesty-lemon-pickle.png',
        'Tomato Pickle': '/static/img/tomato-pickle.webp',
        'Mix Veg Pickle': '/static/img/mixed-veg-pickle.jpg',
        'Spicy Pandu Mirchi': '/static/img/red-chilli-pickle.jpg',
        'Banana Chips': '/static/img/banana-chips.jpg',
        'Crispy Aam-Papad': '/static/img/crispy-aam-papad.jpg',
        'Sweet Boondhi': '/static/img/sweet-boondhi.jpg',
        'Chekkalu': '/static/img/chekkalu.jpg',
        'Ragi Laddu': '/static/img/ragi-ladoo.jpg',
        'Dry Fruit Laddu': '/static/img/dry-fruit.jpg',
        'Kara Boondi': '/static/img/kaaraa-boondhi.jpg',
        'Gavvalu': '/static/img/gavvalu.jpg',
    }
    desc_map = {
        'non_veg_pickles': 'Authentic homemade non-veg pickles, rich in flavor and tradition.',
        'veg_pickles': 'Classic vegetarian pickles made with fresh ingredients.',
        'snacks': 'Crispy, crunchy, and delicious snacks for every occasion.',
    }
    
    category_products = []
    
    # Try DynamoDB first, fallback to local if empty or error
    try:
        response = products_table.scan(
            FilterExpression='category = :cat',
            ExpressionAttributeValues={':cat': category}
        )
        items = response.get('Items', [])
        if items:
            for item in items:
                prod = {
                    'id': item.get('id'),
                    'base_id': item.get('base_id', item.get('id')),
                    'name': item.get('name'),
                    'price': item.get('price'),
                    'img': img_map.get(item.get('name'), '/static/img/default.jpg'),
                    'desc': desc_map.get(item.get('category'), ''),
                    'type': item.get('type', 'Pickles' if item.get('category') in ['non_veg_pickles', 'veg_pickles'] else 'Snacks'),
                    'veg': item.get('category') == 'veg_pickles' or item.get('category') == 'snacks',
                    'stock': item.get('stock', 20),
                    'category': item.get('category'),
                    'weight': item.get('weight')
                }
                category_products.append(prod)
            return category_products
    except Exception as e:
        print(f"DynamoDB error: {e}")
    # Fallback to local products for specific category
    if category in products_fallback:
        for p in products_fallback[category]:
            for w, price in p['weights'].items():
                prod_type = 'Pickles' if category in ['non_veg_pickles', 'veg_pickles'] else 'Snacks'
                prod = {
                    'id': int(f"{p['id']}{w}"),
                    'base_id': p['id'],
                    'name': f"{p['name']} {w}g",
                    'price': price,
                    'img': img_map.get(p['name'], '/static/img/default.jpg'),
                    'desc': desc_map.get(category, ''),
                    'type': prod_type,
                    'veg': category == 'veg_pickles' or category == 'snacks',
                    'stock': 20,
                    'category': category,
                    'weight': w
                }
                category_products.append(prod)
    
    return category_products

@app.route('/veg-pickles')
def veg_pickles():
    products = get_products_by_category('veg_pickles')
    return render_template('veg_pickles.html', products=products, category='veg_pickles')

@app.route('/non-veg-pickles')
def non_veg_pickles():
    products = get_products_by_category('non_veg_pickles')
    return render_template('non_veg_pickles.html', products=products, category='non_veg_pickles')

@app.route('/snacks')
def snacks():
    products = get_products_by_category('snacks')
    return render_template('snacks.html', products=products, category='snacks')

products_fallback = {
    'non_veg_pickles': [
        {'id': 1, 'name': 'Chicken Pickle', 'weights': {'250': 600, '500': 1200, '1000': 1800}},
        {'id': 2, 'name': 'Fish Pickle', 'weights': {'250': 200, '500': 400, '1000': 800}},
        {'id': 3, 'name': 'Gongura Mutton', 'weights': {'250': 400, '500': 800, '1000': 1600}},
        {'id': 4, 'name': 'Mutton Pickle', 'weights': {'250': 400, '500': 800, '1000': 1600}},
        {'id': 5, 'name': 'Prawns Pickle', 'weights': {'250': 600, '500': 1200, '1000': 1800}},
        {'id': 6, 'name': 'Chicken Pickle (Gongura)', 'weights': {'250': 350, '500': 700, '1000': 1050}},
    ],
    'veg_pickles': [
        {'id': 7, 'name': 'Traditional Mango Pickle', 'weights': {'250': 150, '500': 280, '1000': 500}},
        {'id': 8, 'name': 'Zesty Lemon Pickle', 'weights': {'250': 120, '500': 220, '1000': 400}},
        {'id': 9, 'name': 'Tomato Pickle', 'weights': {'250': 130, '500': 240, '1000': 450}},
        {'id': 10, 'name': 'Mix Veg Pickle', 'weights': {'250': 130, '500': 240, '1000': 450}},
        {'id': 12, 'name': 'Spicy Pandu Mirchi', 'weights': {'250': 130, '500': 240, '1000': 450}},
    ],
    'snacks': [
        {'id': 13, 'name': 'Banana Chips', 'weights': {'250': 300, '500': 600, '1000': 800}},
        {'id': 14, 'name': 'Crispy Aam-Papad', 'weights': {'250': 150, '500': 300, '1000': 600}},
        {'id': 16, 'name': 'Sweet Boondhi', 'weights': {'250': 300, '500': 600, '1000': 900}},
        {'id': 17, 'name': 'Chekkalu', 'weights': {'250': 350, '500': 700, '1000': 1000}},
        {'id': 18, 'name': 'Ragi Laddu', 'weights': {'250': 350, '500': 700, '1000': 1000}},
        {'id': 19, 'name': 'Dry Fruit Laddu', 'weights': {'250': 500, '500': 1000, '1000': 1500}},
        {'id': 20, 'name': 'Kara Boondi', 'weights': {'250': 250, '500': 500, '1000': 750}},
        {'id': 21, 'name': 'Gavvalu', 'weights': {'250': 250, '500': 500, '1000': 750}},
    ]
}
@app.route('/api/products')
def api_products():
    time.sleep(1) # Simulate delay
    all_products = []
    img_map = {
        'Chicken Pickle': '/static/img/chicken-pickle.jpg',
        'Fish Pickle': '/static/img/fish-pickle.jpg',
        'Gongura Mutton': '/static/img/gongura-mutton-pickle.webp',
        'Mutton Pickle': '/static/img/mutton-pickle.jpg',
        'Prawns Pickle': '/static/img/prawn-pickle.webp',
        'Chicken Pickle (Gongura)': '/static/img/gongura-chicken-pickle.jpg',
        'Traditional Mango Pickle': '/static/img/mango-pickle.jpg',
        'Zesty Lemon Pickle': '/static/img/zesty-lemon-pickle.png',
        'Tomato Pickle': '/static/img/tomato-pickle.webp',
        'Mix Veg Pickle': '/static/img/mixed-veg-pickle.jpg',
        'Spicy Pandu Mirchi': '/static/img/red-chilli-pickle.jpg',
        'Banana Chips': '/static/img/banana-chips.jpg',
        'Crispy Aam-Papad': '/static/img/crispy-aam-papad.jpg',
        'Sweet Boondhi': '/static/img/sweet-boondhi.jpg',
        'Chekkalu': '/static/img/chekkalu.jpg',
        'Ragi Laddu': '/static/img/ragi-ladoo.jpg',
        'Dry Fruit Laddu': '/static/img/dry-fruit.jpg',
        'Kara Boondi': '/static/img/kaaraa-boondhi.jpg',
        'Gavvalu': '/static/img/gavvalu.jpg',
    }
    desc_map = {
        'non_veg_pickles': 'Authentic homemade non-veg pickles, rich in flavor and tradition.',
        'veg_pickles': 'Classic vegetarian pickles made with fresh ingredients.',
        'snacks': 'Crispy, crunchy, and delicious snacks for every occasion.',
    }
    # Try DynamoDB first, fallback to local if empty or error
    try:
        response = products_table.scan()
        items = response.get('Items', [])
        if items:
            for item in items:
                prod = {
                    'id': item.get('id'),
                    'base_id': item.get('base_id', item.get('id')),
                    'name': item.get('name'),
                    'price': item.get('price'),
                    'img': img_map.get(item.get('name'), '/static/img/default.jpg'),
                    'desc': desc_map.get(item.get('category'), ''),
                    'type': item.get('type', 'Pickles' if item.get('category') in ['non_veg_pickles', 'veg_pickles'] else 'Snacks'),
                    'veg': item.get('category') == 'veg_pickles' or item.get('category') == 'snacks',
                    'stock': item.get('stock', 20),
                    'category': item.get('category'),
                    'weight': item.get('weight')
                }
                all_products.append(prod)
            return jsonify(all_products)
    except Exception as e:
        print(f"DynamoDB error: {e}")
    # Fallback to local products
    for cat, plist in products_fallback.items():
        for p in plist:
            for w, price in p['weights'].items():
                prod_type = 'Pickles' if cat in ['non_veg_pickles', 'veg_pickles'] else 'Snacks'
                prod = {
                    'id': int(f"{p['id']}{w}"),
                    'base_id': p['id'],
                    'name': f"{p['name']} {w}g",
                    'price': price,
                    'img': img_map.get(p['name'], '/static/img/default.jpg'),
                    'desc': desc_map.get(cat, ''),
                    'type': prod_type,
                    'veg': cat == 'veg_pickles' or cat == 'snacks',
                    'stock': 20,
                    'category': cat,
                    'weight': w
                }
                all_products.append(prod)
    return jsonify(all_products)

@app.route('/api/product/<int:product_id>')
def api_product(product_id):
    time.sleep(1)
    img_map = {
        'Chicken Pickle': '/static/img/chicken-pickle.jpg',
        'Fish Pickle': '/static/img/fish-pickle.jpg',
        'Gongura Mutton': '/static/img/gongura-mutton-pickle.webp',
        'Mutton Pickle': '/static/img/mutton-pickle.jpg',
        'Prawns Pickle': '/static/img/prawn-pickle.webp',
        'Chicken Pickle (Gongura)': '/static/img/gongura-chicken-pickle.jpg',
        'Traditional Mango Pickle': '/static/img/mango-pickle.jpg',
        'Zesty Lemon Pickle': '/static/img/zesty-lemon-pickle.png',
        'Tomato Pickle': '/static/img/tomato-pickle.webp',
        'Mix Veg Pickle': '/static/img/mixed-veg-pickle.jpg',
        'Spicy Pandu Mirchi': '/static/img/red-chilli-pickle.jpg',
        'Banana Chips': '/static/img/banana-chips.jpg',
        'Crispy Aam-Papad': '/static/img/crispy-aam-papad.jpg',
        'Sweet Boondhi': '/static/img/sweet-boondhi.jpg',
        'Chekkalu': '/static/img/chekkalu.jpg',
        'Ragi Laddu': '/static/img/ragi-ladoo.jpg',
        'Dry Fruit Laddu': '/static/img/dry-fruit.jpg',
        'Kara Boondi': '/static/img/kaaraa-boondhi.jpg',
        'Gavvalu': '/static/img/gavvalu.jpg',
    }
    desc_map = {
        'non_veg_pickles': 'Authentic homemade non-veg pickles, rich in flavor and tradition.',
        'veg_pickles': 'Classic vegetarian pickles made with fresh ingredients.',
        'snacks': 'Crispy, crunchy, and delicious snacks for every occasion.',
    }
    # Try DynamoDB first
    try:
        response = products_table.get_item(Key={'id': product_id})
        item = response.get('Item')
        if item:
            prod = {
                'id': item.get('id'),
                'base_id': item.get('base_id', item.get('id')),
                'name': item.get('name'),
                'price': item.get('price'),
                'img': img_map.get(item.get('name'), '/static/img/default.jpg'),
                'desc': desc_map.get(item.get('category'), ''),
                'type': item.get('type', 'Pickles' if item.get('category') in ['non_veg_pickles', 'veg_pickles'] else 'Snacks'),
                'veg': item.get('category') == 'veg_pickles' or item.get('category') == 'snacks',
                'stock': item.get('stock', 20),
                'category': item.get('category'),
                'weight': item.get('weight')
            }
            return jsonify(prod)
    except Exception as e:
        print(f"DynamoDB error: {e}")
    # Fallback to local products
    for cat, plist in products_fallback.items():
        for p in plist:
            for w, price in p['weights'].items():
                pid = int(f"{p['id']}{w}")
                if pid == product_id:
                    prod_type = 'Pickles' if cat in ['non_veg_pickles', 'veg_pickles'] else 'Snacks'
                    prod = {
                        'id': pid,
                        'base_id': p['id'],
                        'name': f"{p['name']} {w}g",
                        'price': price,
                        'img': img_map.get(p['name'], '/static/img/default.jpg'),
                        'desc': desc_map.get(cat, ''),
                        'type': prod_type,
                        'veg': cat == 'veg_pickles' or cat == 'snacks',
                        'stock': 20,
                        'category': cat,
                        'weight': w
                    }
                    return jsonify(prod)
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/orders', methods=['GET', 'POST'])
def api_orders():
    if not session.get('user_email'):
        return {'error': 'Unauthorized'}, 401
    if request.method == 'POST':
        order = request.json
        # Add user info from session
        order['user'] = {
            'email': session['user_email'],
            'name': session.get('user_name', '')
        }
        # Assign order ID (from DynamoDB count or fallback to local)
        try:
            # Get the current max order id for this user from DynamoDB
            response = orders_table.query(
                IndexName='user_email-index',
                KeyConditionExpression=Key('user_email').eq(session['user_email']),
                ProjectionExpression='id'
            )
            items = response.get('Items', [])
            max_id = max([int(item['id']) for item in items], default=0)
            order['id'] = max_id + 1
        except Exception as e:
            print(f"DynamoDB order id error: {e}")
            orders = load_orders()
            order['id'] = len(orders) + 1
        # Add user_email for GSI
        order['user_email'] = session['user_email']
        # Save to DynamoDB
        try:
            orders_table.put_item(Item=order)
        except Exception as e:
            print(f"DynamoDB order save error: {e}")
            # Fallback to local file
            orders = load_orders()
            orders.append(order)
            save_orders(orders)
        mock_orders.append(order)  # keep in-memory for compatibility
        # Send order confirmation email
        user_email = session['user_email']
        user_name = session.get('user_name', 'Customer')
        email_subject = f"PickleApp Order #{order['id']} Confirmation"
        email_body = f"""
Hello {user_name},

Thank you for your order with PickleApp!

Order ID: #{order['id']}
Order Date: {order['date']}
Total Amount: Rs.{order['total']}

Your order is being processed and will be shipped soon.

Thank you for choosing PickleApp!
        """
        send_email(user_email, email_subject, email_body)
        return jsonify({'success': True, 'orderId': order['id']})
    # GET: Try DynamoDB first, fallback to local
    try:
        response = orders_table.query(
            IndexName='user_email-index',
            KeyConditionExpression=Key('user_email').eq(session['user_email'])
        )
        user_orders = response.get('Items', [])
        # Remove user_email field for response
        for o in user_orders:
            o.pop('user_email', None)
        return jsonify(user_orders)
    except Exception as e:
        print(f"DynamoDB order fetch error: {e}")
        orders = load_orders()
        user_orders = [o for o in orders if o.get('user', {}).get('email') == session['user_email']]
        return jsonify(user_orders)

@app.route('/api/order/<int:order_id>')
def api_order(order_id):
    if not session.get('user_email'):
        return {'error': 'Unauthorized'}, 401
    
    # Load from file and filter by user
    orders = load_orders()
    order = next((o for o in orders if o['id'] == order_id and o.get('user', {}).get('email') == session['user_email']), None)
    if order:
        return jsonify(order)
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/aws/sns/send', methods=['POST'])
def api_send_sms():
    data = request.json
    phone = data.get('phone')
    message = data.get('message')
    if not phone or not message:
        return jsonify({'error': 'Phone and message required'}), 400
    resp = send_sns_message(phone, message)
    if resp:
        return jsonify({'success': True, 'response': str(resp)})
    return jsonify({'success': False}), 500

@app.route('/api/aws/ec2/instances')
def api_list_ec2():
    ids = list_ec2_instances()
    return jsonify({'instance_ids': ids})



@app.route('/api/user/profile', methods=['GET', 'POST'])
def api_user_profile():
    if not session.get('user_email'):
        return jsonify({'error': 'Unauthorized'}), 401
    users = load_users()
    user = next((u for u in users if u['email'] == session['user_email']), None)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if request.method == 'GET':
        # Return user profile data (excluding password)
        profile = {
            'email': user['email'],
            'name': user.get('name', ''),
            'phone': user.get('phone', ''),
            'street': user.get('street', ''),
            'city': user.get('city', ''),
            'pincode': user.get('pincode', ''),
            'country': user.get('country', 'India')
        }
        return jsonify(profile)
    elif request.method == 'POST':
        data = request.get_json()
        # Update only name and phone (address fields are handled during checkout)
        user['name'] = data.get('name', user.get('name', ''))
        user['phone'] = data.get('phone', user.get('phone', ''))
        save_users(users)
        # Update session name/phone if changed
        session['user_name'] = user['name']
        session['phone'] = user['phone']
        return jsonify({'success': True})

@app.route('/contact', methods=['GET'])
def contact():
   
    return render_template('contact.html')

@app.route('/api/contact', methods=['POST'])
def api_contact():
    data = request.form if request.form else request.get_json()
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')
    if not name or not email or not message:
        return jsonify({'success': False, 'error': 'All fields are required.'}), 400
    # Send email to admin
    admin_email = SENDER_EMAIL  # Or set a specific admin email
    subject = f"Contact Us Message from {name} ({email})"
    body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
    try:
        send_email(admin_email, subject, body)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Contact form email error: {e}")
        return jsonify({'success': False, 'error': 'Failed to send message.'}), 500

# Category-specific API endpoints
@app.route('/api/products/veg-pickles')
def api_veg_pickles():
    products = get_products_by_category('veg_pickles')
    return jsonify(products)

@app.route('/api/products/non-veg-pickles')
def api_non_veg_pickles():
    products = get_products_by_category('non_veg_pickles')
    return jsonify(products)

@app.route('/api/products/snacks')
def api_snacks():
    products = get_products_by_category('snacks')
    return jsonify(products)

from boto3.dynamodb.conditions import Key

@app.route('/api/cart', methods=['GET'])
def api_get_cart():
    if not session.get('user_email'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        response = cart_table.query(
            KeyConditionExpression=Key('user_email').eq(session['user_email'])
        )
        items = response.get('Items', [])
        return jsonify(items)
    except Exception as e:
        print(f"DynamoDB cart fetch error: {e}")
        return jsonify([])

@app.route('/api/cart', methods=['POST'])
def api_add_update_cart():
    if not session.get('user_email'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    if not product_id:
        return jsonify({'error': 'Product ID required'}), 400
    item = {
        'user_email': session['user_email'],
        'product_id': str(product_id),
        'quantity': int(quantity)
    }
    try:
        cart_table.put_item(Item=item)
        return jsonify({'success': True})
    except Exception as e:
        print(f"DynamoDB cart put error: {e}")
        return jsonify({'success': False}), 500

@app.route('/api/cart', methods=['DELETE'])
def api_remove_cart_item():
    if not session.get('user_email'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    product_id = data.get('product_id')
    if not product_id:
        return jsonify({'error': 'Product ID required'}), 400
    try:
        cart_table.delete_item(
            Key={
                'user_email': session['user_email'],
                'product_id': str(product_id)
            }
        )
        return jsonify({'success': True})
    except Exception as e:
        print(f"DynamoDB cart delete error: {e}")
        return jsonify({'success': False}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000, debug=True)
