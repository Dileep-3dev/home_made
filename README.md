<div align="center">

# HomeMade Pickles & Snacks: Taste the Best

*A Flask-AWS integrated e-commerce web application for traditional food ordering*

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com)
[![AWS](https://img.shields.io/badge/AWS-DynamoDB-orange.svg)](https://aws.amazon.com)

</div>

---

## 📋 Project Overview

This project is a **full-stack web application** that demonstrates the integration of modern web technologies with cloud services. Built using Flask framework and AWS cloud infrastructure, it provides a complete e-commerce solution for ordering traditional pickles and snacks online.

## ⚡ Key Features

**Product Management**
- Browse vegetarian pickles, non-vegetarian pickles, and snacks
- Multiple weight options (250g, 500g, 1kg) with different pricing
- Product search and category filtering
- Regional product discovery

**User System**
- User registration and login
- Profile management with address details
- Order history and tracking

### �️ Shopping Cart & Orders
- Add products to cart with quantity selection
- Multi-step checkout process
- Cash on Delivery payment
- Email order confirmations

**Web Interface**
- Responsive design for mobile and desktop
- Clean interface with real-time cart updates

## 🏗️ Technology Architecture

<div align="center">

### Backend Stack
![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-232F3E?style=flat-square&logo=amazon-aws&logoColor=white)

### Frontend Stack
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)

</div>

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Web Framework** | Flask | Backend API development |
| **Database** | AWS DynamoDB | NoSQL data storage |
| **Authentication** | Bcrypt + Flask-Session | Secure user management |
| **Notifications** | AWS SNS | SMS alerts |
| **Email Service** | SMTP Gmail | Order confirmations |
| **Frontend** | JS/CSS | Dynamic user interface |
| **Cloud Platform** | AWS EC2 | Application hosting |

## 📁 Project Architecture

```
home_made-main/
├── 📄 app.py                      # Flask application entry point
├── 📂 static/                     # Static assets
│   ├── 🎨 css/                    # Stylesheets
│   │   ├── general.css            # Global styles
│   │   ├── nav.css               # Navigation components
│   │   ├── product_card.css      # Product display
│   │   ├── cart_checkout.css     # Shopping cart UI
│   │   └── footer.css            # Footer styling
│   ├── ⚡ js/                     # Client-side logic
│   │   ├── main.js               # Core functionality
│   │   ├── cart.js               # Cart operations
│   │   ├── product.js            # Product interactions
│   │   ├── profile.js            # User profile
│   │   └── utils.js              # Helper functions
│   └── 🖼️ img/                    # Product images & assets
└── 📂 templates/                  # HTML templates
    ├── base.html                 # Base layout
    ├── index.html                # Landing page
    ├── products.html             # Product catalog
    ├── cart.html                 # Shopping cart
    ├── checkout.html             # Order processing
    ├── profile.html              # User dashboard
    ├── orders.html               # Order history
    └── [additional pages]        # Feature pages
```

## 🚀 Quick Start Guide

### 📋 Prerequisites
```
✅ Python 3.7+
✅ AWS Account with DynamoDB access
✅ SMTP-enabled email account
✅ Modern web browser
```

### ⚡ Installation Steps

<details>
<summary><b>🔧 Environment Setup</b></summary>

**1. Clone & Navigate**
```bash
git clone <repository-url>
cd home_made-main
```

**2. Dependencies Installation**
```bash
pip install flask boto3 bcrypt
```

**3. Environment Configuration**
```bash
# Windows PowerShell
$env:SECRET_KEY="your-secret-key"
$env:AWS_REGION="ap-south-1"
$env:SENDER_EMAIL="your-email@gmail.com"
$env:SENDER_PASSWORD="your-app-password"

# Linux/Mac
export SECRET_KEY="your-secret-key"
export AWS_REGION="ap-south-1"
export SENDER_EMAIL="your-email@gmail.com"
export SENDER_PASSWORD="your-app-password"
```

</details>

<details>
<summary><b>☁️ AWS Configuration</b></summary>

**DynamoDB Tables Setup:**
- `PickleApp_Users` - User authentication data
- `PickleApp_Products` - Product catalog
- `PickleApp_Orders` - Order management
- `PickleApp_Cart` - Shopping cart sessions

**SNS Setup:**
- Configure SMS notifications for order updates

</details>

**🏃‍♂️ Run Application**
```bash
python app.py
```

**🌐 Access Point**
```
http://localhost:5000
```

## 🗄️ Database Design

<table>
<tr>
<td width="50%">

**👤 Users Table**
```
Primary Key: email
├── name (String)
├── password (Encrypted)
├── phone (String)
├── street (String)
├── city (String)
├── pincode (String)
└── country (String)
```

**📦 Products Table**
```
Primary Key: id
├── base_id (Number)
├── name (String)
├── price (Number)
├── weight (Number)
├── img (String)
├── desc (String)
├── type (String)
├── veg (Boolean)
└── stock (Number)
```

</td>
<td width="50%">

**📋 Orders Table**
```
Primary Key: id
├── user_email (String)
├── items (JSON Array)
├── total (Number)
├── date (DateTime)
├── status (String)
└── shipping_info (JSON)
```

**🛒 Cart Table**
```
Composite Key: user_email + product_id
├── user_email (String)
├── product_id (String)
└── quantity (Number)
```

</td>
</tr>
</table>

## 🔧 System Configuration

<details>
<summary><b>☁️ AWS Integration</b></summary>

```python
# DynamoDB Connection
aws_session = boto3.Session(region_name='ap-south-1')
dynamodb = aws_session.resource('dynamodb')

# Table References
users_table = dynamodb.Table('PickleApp_Users')
products_table = dynamodb.Table('PickleApp_Products')
orders_table = dynamodb.Table('PickleApp_Orders')
cart_table = dynamodb.Table('PickleApp_Cart')
```

</details>

<details>
<summary><b>📧 Email Service Setup</b></summary>

```python
# SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD')
```

</details>

## 📊 API Documentation

<details>
<summary><b>🛒 Product Management APIs</b></summary>

| Method | Endpoint | Description | Response |
|:------:|:---------|:------------|:---------|
| `GET` | `/api/products` | Retrieve all products | JSON array of products |
| `GET` | `/api/product/<id>` | Get specific product details | Product object |
| `GET` | `/api/products/veg-pickles` | Vegetarian pickles only | Filtered product array |
| `GET` | `/api/products/non-veg-pickles` | Non-vegetarian pickles | Filtered product array |
| `GET` | `/api/products/snacks` | Traditional snacks | Filtered product array |

</details>

<details>
<summary><b>🛍️ Shopping Cart APIs</b></summary>

| Method | Endpoint | Description | Payload |
|:------:|:---------|:------------|:--------|
| `GET` | `/api/cart` | Get user's cart items | - |
| `POST` | `/api/cart` | Add/update cart item | `{product_id, quantity}` |
| `DELETE` | `/api/cart` | Remove item from cart | `{product_id}` |

</details>

<details>
<summary><b>📦 Order Management APIs</b></summary>

| Method | Endpoint | Description | Authentication |
|:------:|:---------|:------------|:---------------|
| `GET` | `/api/orders` | User's order history | Required |
| `POST` | `/api/orders` | Place new order | Required |
| `GET` | `/api/order/<id>` | Specific order details | Required |

</details>

<details>
<summary><b>👤 User Management APIs</b></summary>

| Method | Endpoint | Description | Fields |
|:------:|:---------|:------------|:-------|
| `GET` | `/api/user/profile` | Get user profile | All profile data |
| `POST` | `/api/user/profile` | Update profile | `{name, phone, address}` |

</details>

## 🔒 Security Implementation

<div align="center">

| Security Layer | Implementation | Purpose |
|:--------------:|:---------------|:--------|
| 🔐 | **Bcrypt Hashing** | Password encryption |
| 🎫 | **Flask Sessions** | User state management |
| ✅ | **Input Validation** | XSS & injection prevention |
| 🔒 | **Environment Variables** | Sensitive data protection |

</div>

## ☁️ AWS Cloud Integration

- **🗄️ DynamoDB**: Scalable NoSQL database for all application data
- **📱 SNS**: SMS notification service for order updates  
- **🖥️ EC2**: Cloud deployment infrastructure

---
