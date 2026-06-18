from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from jinja2 import DictLoader
import requests
from datetime import datetime
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'werts_smm_secret_key_2024'

# Конфигурация API
API_KEY = "2af40926afe4cc8ab20ae1eb7839e428f396c1a0852888b4e420c4315a8fdfd0"
API_BASE_URL = "https://vestsmm.shop/api/v1"

# Хранилище заказов в памяти (для Vercel)
orders_storage = []

# Функции для работы с API
def get_services():
    try:
        response = requests.get(
            f"{API_BASE_URL}/services",
            params={"api_key": API_KEY},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error fetching services: {e}")
        return []

def create_order_api(service_id, link, quantity):
    try:
        payload = {
            "api_key": API_KEY,
            "service_id": service_id,
            "link": link,
            "quantity": quantity
        }
        response = requests.post(
            f"{API_BASE_URL}/order",
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error creating order: {e}")
        return None

def check_order_status(order_id):
    try:
        response = requests.get(
            f"{API_BASE_URL}/order/status",
            params={"api_key": API_KEY, "order_id": order_id},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error checking order status: {e}")
        return None

# HTML шаблоны
HTML_TEMPLATES = {
    'base': '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Werts Smm - Накрутка подписчиков</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .navbar { background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); box-shadow: 0 2px 10px rgba(0,0,0,0.1); padding: 1rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; }
        .navbar-brand { font-size: 1.5rem; font-weight: bold; color: #667eea; text-decoration: none; }
        .nav-links { display: flex; gap: 1rem; list-style: none; flex-wrap: wrap; }
        .nav-links a { color: #333; text-decoration: none; font-weight: 500; transition: color 0.3s; font-size: 0.95rem; padding: 0.5rem; }
        .nav-links a:hover { color: #667eea; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .flash-messages { margin-bottom: 1rem; }
        .flash { padding: 1rem; border-radius: 10px; margin-bottom: 0.5rem; }
        .flash.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .flash.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .card { background: white; border-radius: 15px; padding: 1.5rem; box-shadow: 0 10px 30px rgba(0,0,0,0.1); margin-bottom: 1.5rem; }
        .btn { background: #667eea; color: white; padding: 0.5rem 1rem; border: none; border-radius: 8px; cursor: pointer; text-decoration: none; display: inline-block; transition: transform 0.2s; font-size: 0.9rem; margin: 0.25rem; }
        .btn:hover { transform: translateY(-2px); opacity: 0.9; }
        .btn-success { background: #28a745; }
        .btn-info { background: #17a2b8; }
        .btn-warning { background: #ffc107; color: #000; }
        .btn-danger { background: #dc3545; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; margin-bottom: 0.5rem; color: #333; font-weight: 500; }
        .form-control { width: 100%; padding: 0.8rem; border: 1px solid #ddd; border-radius: 8px; font-size: 1rem; }
        .form-control:focus { outline: none; border-color: #667eea; }
        .table-responsive { overflow-x: auto; }
        .table { width: 100%; border-collapse: collapse; margin-top: 1rem; min-width: 600px; }
        .table th, .table td { padding: 0.8rem; text-align: left; border-bottom: 1px solid #eee; font-size: 0.9rem; }
        .table th { background: #f8f9fa; color: #667eea; font-weight: 600; }
        .status { padding: 0.3rem 0.6rem; border-radius: 20px; font-size: 0.8rem; font-weight: 500; }
        .status.pending { background: #ffc107; color: #000; }
        .status.completed { background: #28a745; color: white; }
        .status.processing { background: #17a2b8; color: white; }
        .status.in_progress { background: #6f42c1; color: white; }
        .status.partial { background: #fd7e14; color: white; }
        .status.canceled { background: #dc3545; color: white; }
        .hero { text-align: center; padding: 3rem 0; color: white; }
        .hero h1 { font-size: 2.5rem; margin-bottom: 1rem; }
        .hero p { font-size: 1.1rem; margin-bottom: 2rem; opacity: 0.9; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-top: 2rem; }
        .stat-card { background: rgba(255,255,255,0.1); padding: 1.5rem; border-radius: 15px; text-align: center; color: white; backdrop-filter: blur(10px); }
        .stat-number { font-size: 2rem; font-weight: bold; }
        .stat-label { font-size: 0.9rem; margin-top: 0.5rem; }
        .actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
        @media (max-width: 768px) {
            .hero h1 { font-size: 2rem; }
            .card { padding: 1rem; }
            .table th, .table td { padding: 0.5rem; font-size: 0.8rem; }
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <a href="/" class="navbar-brand">Werts Smm</a>
        <ul class="nav-links">
            <li><a href="/">Главная</a></li>
            <li><a href="/services">Услуги</a></li>
            <li><a href="/orders">Заказы</a></li>
            <li><a href="/order">Новый заказ</a></li>
        </ul>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="flash-messages">
                    {% for category, message in messages %}
                        <div class="flash {{ category }}">{{ message }}</div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>''',

    'index': '''{% extends "base.html" %}
{% block content %}
<div class="hero">
    <h1>Werts Smm</h1>
    <p>Профессиональная накрутка подписчиков и лайков в социальных сетях</p>
    <a href="/order" class="btn" style="font-size: 1.1rem; padding: 0.8rem 2rem;">Создать заказ</a>
</div>
<div class="stats">
    <div class="stat-card">
        <div class="stat-number">1000+</div>
        <div class="stat-label">Услуг</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">24/7</div>
        <div class="stat-label">Поддержка</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">Быстро</div>
        <div class="stat-label">Выполнение</div>
    </div>
</div>
{% endblock %}''',

    'services': '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Список доступных услуг</h2>
    {% if services %}
    <div class="table-responsive">
    <table class="table">
        <thead>
            <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Категория</th>
                <th>Цена</th>
                <th>Мин</th>
                <th>Макс</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>
            {% for service in services %}
            <tr>
                <td>{{ service.service_id }}</td>
                <td>{{ service.name }}</td>
                <td>{{ service.category }}</td>
                <td>{{ service.rate }} руб.</td>
                <td>{{ service.min }}</td>
                <td>{{ service.max }}</td>
                <td><a href="/order?service_id={{ service.service_id }}" class="btn btn-info" style="padding: 0.3rem 0.6rem; font-size: 0.8rem;">Заказать</a></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    </div>
    {% else %}
    <p>Не удалось загрузить список услуг. Попробуйте позже.</p>
    <a href="/services" class="btn">Обновить</a>
    {% endif %}
</div>
{% endblock %}''',

    'order': '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Создать новый заказ</h2>
    {% if services %}
    <form method="POST">
        <div class="form-group">
            <label for="service_id">Услуга</label>
            <select class="form-control" id="service_id" name="service_id" required>
                <option value="">Выберите услугу</option>
                {% for service in services %}
                <option value="{{ service.service_id }}" {% if selected_service == service.service_id|string %}selected{% endif %}>
                    {{ service.name }} ({{ service.rate }} руб.)
                </option>
                {% endfor %}
            </select>
        </div>
        <div class="form-group">
            <label for="link">Ссылка</label>
            <input type="url" class="form-control" id="link" name="link" placeholder="https://t.me/your_channel" required>
        </div>
        <div class="form-group">
            <label for="quantity">Количество</label>
            <input type="number" class="form-control" id="quantity" name="quantity" min="100" max="10000" placeholder="1000" required>
        </div>
        <button type="submit" class="btn">Создать заказ</button>
    </form>
    {% else %}
    <p>Не удалось загрузить список услуг. Попробуйте позже.</p>
    <a href="/order" class="btn">Обновить</a>
    {% endif %}
</div>
{% endblock %}''',

    'orders': '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;">
        <h2>Все заказы</h2>
        <div class="actions">
            <a href="/update-all-statuses" class="btn btn-success">Обновить все</a>
            <a href="/clear-orders" class="btn btn-danger" onclick="return confirm('Удалить все заказы?')">Очистить</a>
        </div>
    </div>
    {% if orders %}
    <div class="table-responsive">
    <table class="table">
        <thead>
            <tr>
                <th>ID</th>
                <th>Услуга</th>
                <th>Ссылка</th>
                <th>Кол-во</th>
                <th>Сумма</th>
                <th>Статус</th>
                <th>Дата</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {% for order in orders %}
            <tr>
                <td>{{ order.order_id }}</td>
                <td>{{ order.service_name }}</td>
                <td><a href="{{ order.link }}" target="_blank">{{ order.link[:20] }}...</a></td>
                <td>{{ order.quantity }}</td>
                <td>{{ order.charge }} руб.</td>
                <td><span class="status {{ order.status }}">{{ order.status }}</span></td>
                <td>{{ order.created_at }}</td>
                <td>
                    <div class="actions">
                        <a href="/update-order-status/{{ order.order_id }}" class="btn btn-info" style="padding: 0.2rem 0.4rem; font-size: 0.75rem;">Обновить</a>
                        <a href="/delete-order/{{ order.order_id }}" class="btn btn-danger" style="padding: 0.2rem 0.4rem; font-size: 0.75rem;" onclick="return confirm('Удалить заказ #{{ order.order_id }}?')">Удалить</a>
                    </div>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    </div>
    {% else %}
    <p>У вас пока нет заказов.</p>
    <a href="/order" class="btn">Создать первый заказ</a>
    {% endif %}
</div>
{% endblock %}'''
}

# Регистрация шаблонов
app.jinja_loader = DictLoader(HTML_TEMPLATES)

# Маршруты
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/services')
def services():
    try:
        services_list = get_services()
    except:
        services_list = []
    return render_template('services.html', services=services_list)

@app.route('/order', methods=['GET', 'POST'])
def order():
    if request.method == 'POST':
        try:
            service_id = int(request.form.get('service_id'))
            link = request.form.get('link')
            quantity = int(request.form.get('quantity'))
            
            result = create_order_api(service_id, link, quantity)
            
            if result and result.get('success'):
                new_order = {
                    'order_id': result['order_id'],
                    'service_id': result['service_id'],
                    'service_name': f"Service {result['service_id']}",
                    'link': result['link'],
                    'quantity': result['quantity'],
                    'charge': result['charge'],
                    'status': 'pending',
                    'created_at': datetime.now().strftime('%d.%m.%Y %H:%M')
                }
                orders_storage.append(new_order)
                
                flash('Заказ успешно создан!', 'success')
                return redirect(url_for('orders_list'))
            else:
                flash('Ошибка при создании заказа', 'error')
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'error')
    
    try:
        services_list = get_services()
    except:
        services_list = []
    selected_service = request.args.get('service_id', '')
    return render_template('order.html', services=services_list, selected_service=selected_service)

@app.route('/orders')
def orders_list():
    orders = list(reversed(orders_storage))
    return render_template('orders.html', orders=orders)

@app.route('/update-order-status/<int:order_id>')
def update_order_status(order_id):
    try:
        status_data = check_order_status(order_id)
        if status_data:
            for order in orders_storage:
                if order['order_id'] == order_id:
                    order['status'] = status_data.get('status', order['status'])
                    flash(f'Статус заказа #{order_id}: {order["status"]}', 'success')
                    break
        else:
            flash('Не удалось получить статус заказа', 'error')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
    
    return redirect(url_for('orders_list'))

@app.route('/update-all-statuses')
def update_all_statuses():
    updated = 0
    for order in orders_storage:
        if order['status'] != 'completed':
            try:
                status_data = check_order_status(order['order_id'])
                if status_data:
                    order['status'] = status_data.get('status', order['status'])
                    updated += 1
            except:
                pass
    
    flash(f'Обновлено заказов: {updated}', 'success')
    return redirect(url_for('orders_list'))

@app.route('/delete-order/<int:order_id>')
def delete_order(order_id):
    global orders_storage
    orders_storage = [order for order in orders_storage if order['order_id'] != order_id]
    flash(f'Заказ #{order_id} удален', 'success')
    return redirect(url_for('orders_list'))

@app.route('/clear-orders')
def clear_orders():
    global orders_storage
    orders_storage = []
    flash('История заказов очищена', 'success')
    return redirect(url_for('orders_list'))

@app.route('/api/orders')
def api_orders():
    return jsonify(list(reversed(orders_storage)))

# Для локального запуска
if __name__ == '__main__':
    app.run(debug=True)
