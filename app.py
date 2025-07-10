from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime
import os
import time

import boto3
import json
from boto3.dynamodb.conditions import Key

USE_DYNAMODB = os.environ.get('USE_DYNAMODB', 'False') == 'True'
AWS_REGION_NAME = os.environ.get('AWS_REGION_NAME', 'us-east-1')
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'PickleUsers')
ORDERS_TABLE_NAME = os.environ.get('ORDERS_TABLE_NAME', 'PickleOrders')
PRODUCTS_TABLE_NAME = os.environ.get('PRODUCTS_TABLE_NAME', 'PickleProducts')
CART_TABLE_NAME = os.environ.get('CART_TABLE_NAME', 'PickleCart')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
ENABLE_SNS = os.environ.get('ENABLE_SNS', 'False').lower() == 'true'
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@pickleapp.com')

if USE_DYNAMODB:
    try:
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        users_table = dynamodb.Table(USERS_TABLE_NAME)
        orders_table = dynamodb.Table(ORDERS_TABLE_NAME)
        products_table = dynamodb.Table(PRODUCTS_TABLE_NAME)
        cart_table = dynamodb.Table(CART_TABLE_NAME)
        if ENABLE_SNS and SNS_TOPIC_ARN:
            sns = boto3.client('sns', region_name=AWS_REGION_NAME)
    except Exception as e:
        print(f"AWS connection error: {e}")
        USE_DYNAMODB = False

# Fallback to simple in-memory storage
if not USE_DYNAMODB:
    users = {}
    orders = []
    mock_orders = []
    # Define dummy table objects for when DynamoDB is not used
    products_table = None
    cart_table = None

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')

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
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        phone = request.form['phone'].strip()
        
        if not name or not email or not password or not confirm_password or not phone:
            flash("All fields are mandatory! Please fill out the entire form.", "danger")
            return render_template('register.html')
            
        if password != confirm_password:
            flash("Passwords do not match! Please try again.", "danger")
            return render_template('register.html')
            
        hashed_password = generate_password_hash(password)
        
        if USE_DYNAMODB:
            # Check if user exists
            try:
                resp = users_table.get_item(Key={'email': email})
                if 'Item' in resp:
                    flash("User already exists! Please log in.", "info")
                    return redirect(url_for('login'))
                    
                users_table.put_item(Item={
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
                })
            except Exception as e:
                print(f"DynamoDB error: {e}")
                flash("Registration failed. Please try again.", "danger")
                return render_template('register.html')
        else:
            if email in users:
                flash("User already exists! Please log in.", "info")
                return redirect(url_for('login'))
                
            users[email] = {
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
            
        session['user_email'] = email
        session['user_name'] = name
        session['phone'] = phone
        flash("Registration successful!", "success")
        return redirect(url_for('profile'))
    return render_template('register.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        
        if USE_DYNAMODB:
            # Check if user exists by username
            try:
                resp = users_table.get_item(Key={'username': username})
                if 'Item' in resp:
                    return render_template('signup.html', error='Username already exists')
                    
                users_table.put_item(Item={
                    'username': username,
                    'email': email,
                    'password': hashed_password
                })
            except Exception as e:
                print(f"DynamoDB error: {e}")
                return render_template('signup.html', error='Signup failed. Please try again.')
        else:
            if username in users:
                return render_template('signup.html', error='Username already exists')
            users[username] = {
                'email': email,
                'password': hashed_password
            }
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']
        
        if not email or not password:
            flash("Email and password are required!", "danger")
            return render_template('login.html')
            
        if USE_DYNAMODB:
            try:
                resp = users_table.get_item(Key={'email': email})
                user = resp.get('Item')
                if not user:
                    flash("Incorrect email or password! Please try again.", "danger")
                    return render_template('login.html')
                if not check_password_hash(user['password'], password):
                    flash("Incorrect email or password! Please try again.", "danger")
                    return render_template('login.html')
                    
                # Update login count
                try:
                    users_table.update_item(
                        Key={'email': email},
                        UpdateExpression='SET login_count = if_not_exists(login_count, :zero) + :inc',
                        ExpressionAttributeValues={':inc': 1, ':zero': 0}
                    )
                except Exception as e:
                    print(f"DynamoDB update error: {e}")
            except Exception as e:
                print(f"DynamoDB error: {e}")
                flash("Login failed. Please try again.", "danger")
                return render_template('login.html')
        else:
            if email not in users:
                flash("Incorrect email or password! Please try again.", "danger")
                return render_template('login.html')
                
            user = users[email]
            if not check_password_hash(user['password'], password):
                flash("Incorrect email or password! Please try again.", "danger")
                return render_template('login.html')
                
            # Update login count
            users[email]['login_count'] = users[email].get('login_count', 0) + 1
            
        session['user_email'] = email
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
        
    if USE_DYNAMODB:
        try:
            resp = users_table.get_item(Key={'email': session['user_email']})
            user = resp.get('Item')
            if not user:
                flash("User not found! Please log in again.", "danger")
                return redirect(url_for('login'))
        except Exception as e:
            print(f"DynamoDB error: {e}")
            flash("Error loading profile. Please try again.", "danger")
            return redirect(url_for('login'))
    else:
        user_email = session['user_email']
        if user_email not in users:
            flash("User not found! Please log in again.", "danger")
            return redirect(url_for('login'))
        user = users[user_email]
        user['email'] = user_email  # Add email to user object for template
        
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
        if USE_DYNAMODB and products_table:
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
        if USE_DYNAMODB and products_table:
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
        if USE_DYNAMODB and products_table:
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
            if USE_DYNAMODB and orders_table:
                # Get the current max order id for this user from DynamoDB
                response = orders_table.query(
                    IndexName='user_email-index',
                    KeyConditionExpression=Key('user_email').eq(session['user_email']),
                    ProjectionExpression='id'
                )
                items = response.get('Items', [])
                max_id = max([int(item['id']) for item in items], default=0)
                order['id'] = max_id + 1
            else:
                orders = load_orders()
                order['id'] = len(orders) + 1
        except Exception as e:
            print(f"DynamoDB order id error: {e}")
            orders = load_orders()
            order['id'] = len(orders) + 1
        # Add user_email for GSI
        order['user_email'] = session['user_email']
        # Save to DynamoDB
        try:
            if USE_DYNAMODB and orders_table:
                orders_table.put_item(Item=order)
            else:
                # Fallback to local file
                orders = load_orders()
                orders.append(order)
                save_orders(orders)
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
        if USE_DYNAMODB and orders_table:
            response = orders_table.query(
                IndexName='user_email-index',
                KeyConditionExpression=Key('user_email').eq(session['user_email'])
            )
            user_orders = response.get('Items', [])
            # Remove user_email field for response
            for o in user_orders:
                o.pop('user_email', None)
            return jsonify(user_orders)
        else:
            orders = load_orders()
            user_orders = [o for o in orders if o.get('user', {}).get('email') == session['user_email']]
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
        if USE_DYNAMODB and cart_table:
            response = cart_table.query(
                KeyConditionExpression=Key('user_email').eq(session['user_email'])
            )
            items = response.get('Items', [])
            return jsonify(items)
        else:
            # Return empty cart for non-DynamoDB mode
            return jsonify([])
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
        if USE_DYNAMODB and cart_table:
            cart_table.put_item(Item=item)
            return jsonify({'success': True})
        else:
            # For non-DynamoDB mode, just return success
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
        if USE_DYNAMODB and cart_table:
            cart_table.delete_item(
                Key={
                    'user_email': session['user_email'],
                    'product_id': str(product_id)
                }
            )
            return jsonify({'success': True})
        else:
            # For non-DynamoDB mode, just return success
            return jsonify({'success': True})
    except Exception as e:
        print(f"DynamoDB cart delete error: {e}")
        return jsonify({'success': False}), 500

# Utility functions for file operations
def load_users():
    """Load users from file or return empty list"""
    try:
        if os.path.exists('users.json'):
            with open('users.json', 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading users: {e}")
    return []

def save_users(users_list):
    """Save users to file"""
    try:
        with open('users.json', 'w') as f:
            json.dump(users_list, f, indent=2)
    except Exception as e:
        print(f"Error saving users: {e}")

def load_orders():
    """Load orders from file or return empty list"""
    try:
        if os.path.exists('orders.json'):
            with open('orders.json', 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading orders: {e}")
    return []

def save_orders(orders_list):
    """Save orders to file"""
    try:
        with open('orders.json', 'w') as f:
            json.dump(orders_list, f, indent=2)
    except Exception as e:
        print(f"Error saving orders: {e}")

def send_email(to_email, subject, body):
    """Send email - placeholder function"""
    try:
        # This is a placeholder - in production you would use AWS SES or similar
        print(f"EMAIL TO: {to_email}")
        print(f"SUBJECT: {subject}")
        print(f"BODY: {body}")
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_sns_message(phone, message):
    """Send SMS via SNS - placeholder function"""
    try:
        if ENABLE_SNS and SNS_TOPIC_ARN:
            response = sns.publish(
                PhoneNumber=phone,
                Message=message
            )
            return response
        else:
            print(f"SMS TO: {phone}, MESSAGE: {message}")
            return {"MessageId": "mock-message-id"}
    except Exception as e:
        print(f"SNS error: {e}")
        return None

def list_ec2_instances():
    """List EC2 instances - placeholder function"""
    try:
        ec2 = boto3.client('ec2', region_name=AWS_REGION_NAME)
        response = ec2.describe_instances()
        instance_ids = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_ids.append(instance['InstanceId'])
        return instance_ids
    except Exception as e:
        print(f"EC2 error: {e}")
        return []

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000, debug=True)
