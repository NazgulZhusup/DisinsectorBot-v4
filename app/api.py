from flask import Blueprint, request, jsonify
from app.model import Order, Client, Disinsector
from database import db
from werkzeug.security import check_password_hash
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
import logging

api_bp = Blueprint('api', __name__)
logger = logging.getLogger('api_bp')


# Эндпоинт для входа в систему
@api_bp.route('/login', methods=['POST'])
def api_login():
    data = request.json
    if not data or not all(k in data for k in ('disinsector_id', 'password')):
        return jsonify({"error": "Недостаточно данных для входа"}), 400

    disinsector_id = data.get('disinsector_id')
    password = data.get('password')

    disinsector = Disinsector.query.filter_by(disinsector_id=disinsector_id).first()
    if not disinsector or not check_password_hash(disinsector.password, password):
        return jsonify({"error": "Неверный ID или пароль"}), 401

    # Генерация токена доступа
    access_token = create_access_token(identity=disinsector_id)
    return jsonify({"access_token": access_token}), 200


# Эндпоинт для получения заявок
@api_bp.route('/orders', methods=['GET'])
@jwt_required()
def get_orders():
    disinsector_id = get_jwt_identity()
    orders = Order.query.filter_by(disinsector_id=disinsector_id).all()

    if not orders:
        return jsonify({"message": "Нет заявок"}), 404

    orders_data = [
        {
            "order_id": order.id,
            "client_name": order.client.name,
            "address": order.client.address,
            "phone": order.client.phone,
            "status": order.order_status
        }
        for order in orders
    ]
    return jsonify({"orders": orders_data}), 200


# Эндпоинт для создания заявки
@api_bp.route('/create_order', methods=['POST'])
@jwt_required()
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['client_name', 'phone_number', 'address', 'object_type', 'insect_quantity']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing fields: {", ".join(missing_fields)}'}), 400

    client = Client.query.filter_by(phone=data['phone_number']).first()
    if not client:
        client = Client(name=data['client_name'], phone=data['phone_number'], address=data['address'])
        db.session.add(client)
        db.session.commit()

    disinsector_id = get_jwt_identity()
    new_order = Order(
        client_id=client.id,
        disinsector_id=disinsector_id,
        object_type=data['object_type'],
        insect_quantity=data['insect_quantity'],
        disinsect_experience=data.get('disinsect_experience', False),
        order_status='Новая'
    )
    db.session.add(new_order)
    db.session.commit()

    return jsonify({"message": "Заявка успешно создана"}), 201


# Эндпоинт для обновления статуса заявки
@api_bp.route('/update_order_status', methods=['POST'])
@jwt_required()
def update_order_status():
    data = request.json
    if not data or not all(k in data for k in ('order_id', 'new_status')):
        return jsonify({"error": "Недостаточно данных"}), 400

    disinsector_id = get_jwt_identity()
    order = Order.query.filter_by(id=data['order_id'], disinsector_id=disinsector_id).first()

    if not order:
        return jsonify({"error": "Заявка не найдена или у вас нет доступа"}), 404

    order.order_status = data['new_status']
    db.session.commit()

    return jsonify({"message": "Статус заявки обновлен"}), 200
