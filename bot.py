import os
import hashlib
import time
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = '7663699162:AAFBc9Yy5ilib3ff0p3ncNecsmH9PgSLGOo'
ADMIN_USER_ID = 8161279210  # Your Telegram user ID
ADMIN_USERNAME = 'kloreooo'  # Your Telegram username

# Smile One API Configuration
SMILE_API_URL = 'https://frontsmie.smile.one'
SMILE_EMAIL = 'rcsexplaination@gmail.com'
SMILE_UID = '1202586'
SMILE_API_KEY = '992d767e3266edc7f46643b38fe8dc97'
PRODUCT_NAME = 'mobilelegends'

# Payment Configuration (Editable by admin)
payment_config = {
    'upi_id': '7629088530@ptyes',
    'wallet_enabled': True
}

# Database simulation (in production, use SQLite or similar)
users_db = {}
orders_db = {}
transactions_db = {}
wallet_db = {}
products_db = {
    '13': {'name': '78 Diamonds', 'price': 5.00},
    '23': {'name': '156 Diamonds', 'price': 10.00}
}

def generate_sign(params, key):
    """Generate MD5 sign for API requests"""
    sorted_params = sorted(params.items())
    param_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
    sign_str = param_str + key
    return hashlib.md5(hashlib.md5(sign_str.encode()).hexdigest().encode()).hexdigest()

def get_products():
    """Get product list from Smile One API"""
    params = {
        'uid': SMILE_UID,
        'email': SMILE_EMAIL,
        'product': PRODUCT_NAME,
        'time': int(time.time())
    }
    params['sign'] = generate_sign(params, SMILE_API_KEY)
    
    try:
        response = requests.post(f"{SMILE_API_URL}/smilecoin/api/productlist", data=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200:
                return data.get('data', {}).get('product', [])
    except Exception as e:
        logger.error(f"Error getting products: {e}")
    return []

def verify_role(userid, zoneid):
    """Verify user role with Smile One API"""
    params = {
        'uid': SMILE_UID,
        'email': SMILE_EMAIL,
        'userid': userid,
        'zoneid': zoneid,
        'product': PRODUCT_NAME,
        'productid': '13',  # Any product ID for verification
        'time': int(time.time())
    }
    params['sign'] = generate_sign(params, SMILE_API_KEY)
    
    try:
        response = requests.post(f"{SMILE_API_URL}/smilecoin/api/getrole", data=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200:
                return True, data.get('username', '')
    except Exception as e:
        logger.error(f"Error verifying role: {e}")
    return False, ''

def create_order(userid, zoneid, productid):
    """Create order with Smile One API"""
    params = {
        'uid': SMILE_UID,
        'email': SMILE_EMAIL,
        'userid': userid,
        'zoneid': zoneid,
        'product': PRODUCT_NAME,
        'productid': productid,
        'time': int(time.time())
    }
    params['sign'] = generate_sign(params, SMILE_API_KEY)
    
    try:
        response = requests.post(f"{SMILE_API_URL}/smilecoin/api/createorder", data=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200:
                return True, data.get('order_id', '')
    except Exception as e:
        logger.error(f"Error creating order: {e}")
    return False, ''

# Wallet Functions
def get_wallet_balance(user_id):
    return wallet_db.get(str(user_id), 0.00)

def update_wallet(user_id, amount, transaction_type):
    user_id = str(user_id)
    current_balance = wallet_db.get(user_id, 0.00)
    
    if transaction_type == 'deposit':
        new_balance = current_balance + amount
    elif transaction_type == 'withdraw':
        if current_balance < amount:
            return False
        new_balance = current_balance - amount
    
    wallet_db[user_id] = new_balance
    
    # Record transaction
    transaction_id = f"txn_{int(time.time())}"
    transactions_db[transaction_id] = {
        'user_id': user_id,
        'amount': amount,
        'type': transaction_type,
        'balance': new_balance,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return True

# Telegram Bot Handlers
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    if user.id == ADMIN_USER_ID:
        update.message.reply_text(
            "👑 Admin Panel\n\n"
            "Available commands:\n"
            "/addproduct - Add new product\n"
            "/editproduct - Edit product\n"
            "/orders - View all orders\n"
            "/users - View all users\n"
            "/stats - View statistics\n"
            "/setupi - Change UPI ID\n"
            "/wallet - Manage user wallets"
        )
    else:
        if str(user.id) in users_db:
            balance = wallet_db.get(str(user.id), 0.00)
            update.message.reply_text(
                f"Welcome back, {user.first_name}!\n\n"
                f"💰 Wallet Balance: ₹{balance:.2f}\n"
                f"🎮 Game ID: {users_db[str(user.id)]['userid']}\n"
                f"🌐 Zone ID: {users_db[str(user.id)]['zoneid']}\n\n"
                "Use /topup to purchase diamonds\n"
                "/deposit to add funds to your wallet"
            )
        else:
            update.message.reply_text(
                "Welcome to Mobile Legends Diamond Top-Up Bot!\n\n"
                "Please register your game ID and zone ID first using:\n"
                "/register <game_id> <zone_id>\n\n"
                "Example: /register 123456 22001"
            )

def register(update: Update, context: CallbackContext):
    if len(context.args) != 2:
        update.message.reply_text("Please provide both game ID and zone ID.\nExample: /register 123456 22001")
        return
    
    userid = context.args[0]
    zoneid = context.args[1]
    user = update.effective_user
    
    # Verify the user's game ID and zone ID
    update.message.reply_text("Verifying your game ID...")
    success, username = verify_role(userid, zoneid)
    
    if success:
        users_db[str(user.id)] = {
            'userid': userid,
            'zoneid': zoneid,
            'username': username,
            'registered_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        wallet_db[str(user.id)] = 0.00  # Initialize wallet
        
        update.message.reply_text(
            f"✅ Verification successful!\n\n"
            f"Game ID: {userid}\n"
            f"Zone ID: {zoneid}\n"
            f"Username: {username}\n\n"
            f"Your wallet has been created with ₹0.00 balance.\n"
            f"Use /deposit to add funds, then /topup to purchase diamonds."
        )
    else:
        update.message.reply_text(
            "❌ Verification failed. Please check your game ID and zone ID and try again."
        )

def deposit(update: Update, context: CallbackContext):
    user = update.effective_user
    if str(user.id) not in users_db:
        update.message.reply_text("Please register first using /register <game_id> <zone_id>")
        return
    
    if len(context.args) != 1:
        update.message.reply_text("Please specify the amount to deposit.\nExample: /deposit 500")
        return
    
    try:
        amount = float(context.args[0])
        if amount <= 0:
            update.message.reply_text("Amount must be greater than 0")
            return
    except ValueError:
        update.message.reply_text("Please enter a valid amount")
        return
    
    # Create deposit request
    transaction_id = f"dep_{int(time.time())}"
    transactions_db[transaction_id] = {
        'user_id': str(user.id),
        'amount': amount,
        'status': 'pending',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    update.message.reply_text(
        f"💳 Deposit Request\n\n"
        f"Amount: ₹{amount:.2f}\n"
        f"UPI ID: {payment_config['upi_id']}\n\n"
        f"Please send the amount to the above UPI ID and then send a screenshot of the payment to @{ADMIN_USERNAME} for verification.\n\n"
        f"Your transaction ID: {transaction_id}"
    )
    
    # Notify admin
    context.bot.send_message(
        chat_id=ADMIN_USER_ID,
        text=f"💵 New Deposit Request\n\n"
             f"User: @{user.username}\n"
             f"Amount: ₹{amount:.2f}\n"
             f"Transaction ID: {transaction_id}\n\n"
             f"After receiving payment, confirm with:\n"
             f"/confirm {transaction_id}"
    )

def topup(update: Update, context: CallbackContext):
    user = update.effective_user
    if str(user.id) not in users_db:
        update.message.reply_text("Please register first using /register <game_id> <zone_id>")
        return
    
    # Get available products
    products = get_products()
    if not products:
        products = [
            {'id': '13', 'spu': '78 Diamonds', 'price': '5.00'},
            {'id': '23', 'spu': '156 Diamonds', 'price': '10.00'}
        ]
    
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                f"{product['spu']} - ₹{product['price']}",
                callback_data=f"product_{product['id']}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Please select a diamond package:", reply_markup=reply_markup)

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    if query.data.startswith('product_'):
        product_id = query.data.split('_')[1]
        process_purchase(query, product_id)
    elif query.data == 'confirm_purchase':
        confirm_purchase(query)

def process_purchase(query, product_id):
    user = query.from_user
    user_data = users_db.get(str(user.id), {})
    
    # Find product details
    product = None
    products = get_products()
    for p in products:
        if p['id'] == product_id:
            product = p
            break
    
    if not product:
        query.edit_message_text("Product not found. Please try again.")
        return
    
    price = float(product['price'])
    balance = wallet_db.get(str(user.id), 0.00)
    
    if balance < price:
        query.edit_message_text(
            f"❌ Insufficient wallet balance.\n\n"
            f"Package price: ₹{price:.2f}\n"
            f"Your balance: ₹{balance:.2f}\n\n"
            f"Please deposit funds using /deposit"
        )
        return
    
    # Show confirmation
    keyboard = [
        [InlineKeyboardButton("Confirm Purchase", callback_data=f"confirm_{product_id}")],
        [InlineKeyboardButton("Cancel", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        f"💎 Package: {product['spu']}\n"
        f"💰 Price: ₹{price:.2f}\n"
        f"💳 Wallet Balance: ₹{balance:.2f}\n\n"
        f"After purchase, your new balance will be: ₹{balance - price:.2f}\n\n"
        f"Confirm purchase?",
        reply_markup=reply_markup
    )

def confirm_purchase(query):
    user = query.from_user
    user_data = users_db.get(str(user.id), {})
    product_id = query.data.split('_')[1]
    
    # Get product details
    product = None
    products = get_products()
    for p in products:
        if p['id'] == product_id:
            product = p
            break
    
    if not product:
        query.edit_message_text("Product not found. Please try again.")
        return
    
    price = float(product['price'])
    
    # Deduct from wallet
    if not update_wallet(user.id, price, 'withdraw'):
        query.edit_message_text("Insufficient balance. Please deposit funds.")
        return
    
    # Create order
    success, order_id = create_order(user_data['userid'], user_data['zoneid'], product_id)
    
    if success:
        orders_db[order_id] = {
            'user_id': user.id,
            'game_id': user_data['userid'],
            'zone_id': user_data['zoneid'],
            'product': product['spu'],
            'amount': price,
            'status': 'completed',
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        query.edit_message_text(
            "🎉 Purchase successful!\n\n"
            f"Order ID: {order_id}\n"
            f"Product: {product['spu']}\n"
            f"Amount: ₹{price:.2f}\n"
            f"New Wallet Balance: ₹{wallet_db.get(str(user.id), 0.00):.2f}\n\n"
            "Your diamonds will be credited shortly.\n\n"
            "You can check your order history with /history"
        )
        
        # Notify admin
        context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"🛒 New Order\n\n"
                 f"User: @{user.username}\n"
                 f"Game ID: {user_data['userid']}\n"
                 f"Zone ID: {user_data['zoneid']}\n"
                 f"Product: {product['spu']}\n"
                 f"Amount: ₹{price:.2f}\n"
                 f"Order ID: {order_id}"
        )
    else:
        # Refund if order failed
        update_wallet(user.id, price, 'deposit')
        query.edit_message_text("❌ Order failed. Your funds have been refunded to your wallet.")

# Admin commands
def admin_set_upi(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID:
        update.message.reply_text("You don't have permission to use this command.")
        return
    
    if len(context.args) < 1:
        update.message.reply_text("Usage: /setupi <new_upi_id>")
        return
    
    new_upi = context.args[0]
    payment_config['upi_id'] = new_upi
    update.message.reply_text(f"✅ UPI ID updated to: {new_upi}")

def admin_confirm_deposit(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID:
        update.message.reply_text("You don't have permission to use this command.")
        return
    
    if len(context.args) != 1:
        update.message.reply_text("Usage: /confirm <transaction_id>")
        return
    
    txn_id = context.args[0]
    if txn_id not in transactions_db:
        update.message.reply_text("Transaction ID not found")
        return
    
    txn = transactions_db[txn_id]
    if txn['status'] != 'pending':
        update.message.reply_text("Transaction already processed")
        return
    
    # Update wallet
    user_id = txn['user_id']
    amount = txn['amount']
    update_wallet(user_id, amount, 'deposit')
    
    # Update transaction status
    txn['status'] = 'completed'
    txn['processed_by'] = update.effective_user.username
    txn['processed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    update.message.reply_text(
        f"✅ Deposit confirmed\n\n"
        f"User ID: {user_id}\n"
        f"Amount: ₹{amount:.2f}\n"
        f"New Balance: ₹{wallet_db.get(user_id, 0.00):.2f}"
    )
    
    # Notify user
    context.bot.send_message(
        chat_id=int(user_id),
        text=f"💰 Deposit Successful!\n\n"
             f"Amount: ₹{amount:.2f}\n"
             f"New Balance: ₹{wallet_db.get(user_id, 0.00):.2f}\n\n"
             f"Thank you for your deposit!"
    )

def admin_wallet_management(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID:
        update.message.reply_text("You don't have permission to use this command.")
        return
    
    if len(context.args) < 2:
        update.message.reply_text("Usage: /wallet <user_id> <amount> [add/remove/set]")
        return
    
    try:
        user_id = context.args[0]
        amount = float(context.args[1])
        action = context.args[2] if len(context.args) > 2 else 'add'
        
        if action not in ['add', 'remove', 'set']:
            update.message.reply_text("Invalid action. Use add, remove, or set")
            return
        
        if action == 'add':
            update_wallet(user_id, amount, 'deposit')
            message = f"Added ₹{amount:.2f} to wallet"
        elif action == 'remove':
            if update_wallet(user_id, amount, 'withdraw'):
                message = f"Removed ₹{amount:.2f} from wallet"
            else:
                message = "Insufficient balance"
        elif action == 'set':
            wallet_db[user_id] = amount
            message = f"Wallet set to ₹{amount:.2f}"
        
        update.message.reply_text(
            f"{message}\n\n"
            f"User ID: {user_id}\n"
            f"New Balance: ₹{wallet_db.get(user_id, 0.00):.2f}"
        )
    except ValueError:
        update.message.reply_text("Invalid amount")

def error_handler(update: Update, context: CallbackContext):
    logger.error(msg="Exception while handling update:", exc_info=context.error)
    if update.effective_message:
        update.effective_message.reply_text('An error occurred. Please try again.')

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Add handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("register", register))
    dp.add_handler(CommandHandler("deposit", deposit))
    dp.add_handler(CommandHandler("topup", topup))
    dp.add_handler(CommandHandler("history", lambda u, c: u.message.reply_text("Order history feature will be implemented")))
    dp.add_handler(CommandHandler("setupi", admin_set_upi))
    dp.add_handler(CommandHandler("confirm", admin_confirm_deposit))
    dp.add_handler(CommandHandler("wallet", admin_wallet_management))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_error_handler(error_handler)
    
    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
