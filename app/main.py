from flask import Blueprint, render_template, redirect, url_for, session, flash, request, current_app
from app.model import Order, Disinsector, Admin
from database import db
from sqlalchemy.orm import joinedload
import logging
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)
logger = logging.getLogger('main')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('main.log')
stream_handler = logging.StreamHandler()

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/admin/dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    if not isinstance(current_user, Admin):
        flash("У вас нет доступа к этой странице.", 'danger')
        return redirect(url_for('auth.admin_login'))

    disinsector_id = request.args.get('disinsector_id', None)  # Фильтр по дезинсектору
    try:
        query = db.session.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.disinsector)
        )
        if disinsector_id:
            query = query.filter(Order.disinsector_id == disinsector_id)

        orders = query.all()
        return render_template('admin_dashboard.html', orders=orders)
    except Exception as e:
        current_app.logger.error(f"Ошибка загрузки админ-дэшборда: {e}")
        flash("Произошла ошибка при загрузке дэшборда.", 'danger')
        return redirect(url_for('auth.admin_login'))



@main_bp.route('/disinsector/dashboard', methods=['GET'])
@login_required
def disinsector_dashboard():

    current_app.logger.info(f"Текущий пользователь: {current_user}")
    current_app.logger.info(f"Тип пользователя: {type(current_user)}")

    if not isinstance(current_user, Disinsector):
        flash("У вас нет доступа к этой странице.", 'danger')
        return redirect(url_for('auth.disinsector_login'))

    try:
        current_app.logger.info(f"Дезинсектор {current_user.name} (ID: {current_user.id}) вошел в дашборд.")

        orders = db.session.query(Order).options(
            joinedload(Order.client)
        ).filter(Order.disinsector_id == current_user.id).all()

        # Логируем количество заявок
        current_app.logger.info(f"Количество заявок для дезинсектора {current_user.name}: {len(orders)}")
        current_app.logger.info(f"Дезинсектор: {current_user.name}, ID: {current_user.id}")

        # Передаём заявки в шаблон
        return render_template('disinsector_dashboard.html', disinsector=current_user, orders=orders)
    except Exception as e:
        current_app.logger.error(f"Ошибка при загрузке дашборда дезинсектора: {e}")
        flash("Произошла ошибка при загрузке заявок.", 'danger')
        return redirect(url_for('auth.disinsector_login'))

    for order in orders:
        current_app.logger.info(
            f"Заявка ID: {order.id}, Клиент: {order.client.name}, Адрес: {order.client.address}, Статус: {order.order_status}"
        )


@main_bp.route('/update_order_status', methods=['POST'])
@login_required
def update_order_status():
    if 'disinsector_id' in session:
        order_id = request.form.get('order_id')
        new_status = request.form.get('new_status')

        if not order_id or not new_status:
            flash("Неверные данные.", 'danger')
            return redirect(url_for('main.disinsector_dashboard'))

        try:
            disinsector = Disinsector.query.get(session['disinsector_id'])
            if not disinsector:
                flash("Дезинсектор не найден.", 'danger')
                return redirect(url_for('auth.disinsector_login'))

            order = Order.query.filter_by(id=order_id, disinsector_id=disinsector.id).first()
            if order:
                order.order_status = new_status
                db.session.commit()
                flash("Статус заявки обновлен.", 'success')
            else:
                flash("Заявка не найдена или у вас нет прав на её изменение.", 'danger')
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса заявки {order_id}: {e}")
            flash("Произошла ошибка при обновлении статуса заявки.", 'danger')

        return redirect(url_for('main.disinsector_dashboard'))
    else:
        flash("Неавторизованный доступ.", 'danger')
        return redirect(url_for('auth.disinsector_login'))
