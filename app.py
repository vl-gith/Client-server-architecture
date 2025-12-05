#import flask (web server + app server)
#import request (get, post)
#import render_template (Jinja2)

# run:
# source virt_environment/bin/activate
# export FLASK_APP=app.py
# flask run (flask run --debug)
# flask db init
# http://127.0.0.1:5000/

# create db:
# CREATE DATABASE my_db;
# CREATE USER 'vladislav'@'localhost' IDENTIFIED BY '!Hello_World123';
# GRANT ALL PRIVILEGES ON my_db.* TO 'vladislav'@'localhost';
# FLUSH PRIVILEGES;
# EXIT;

import os
from flask import Flask, request, render_template, jsonify

# не будем писать SQL вручную
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

#объект flask
app = Flask(__name__)
app.json.ensure_ascii = False

# настройки для переменных окружения
db_user = os.getenv('DB_USER', 'vladislav')
db_password = os.getenv('DB_PASSWORD', '!Hello_World123')
db_host = os.getenv('DB_HOST', 'localhost')
db_name = os.getenv('DB_NAME', 'my_db')
db_port = os.getenv('DB_PORT', '3306')

# конфиг для бд
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://vladislav:!Hello_World123@localhost/my_db'

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class ProcessedNumber(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # каждое число в этом столбце должно быть уникальным
    number = db.Column(db.Integer, unique=True, nullable=False)

    # временная метка
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<ProcessedNumber {self.number}>'

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # тип события
    event_type = db.Column(db.String(50), nullable=False)
    
    # сообщение в логе
    message = db.Column(db.String(255), nullable=False)
    
    # число, которое вызвало это событие
    received_number = db.Column(db.Integer)

    # временная метка
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'event_type': self.event_type,
            'message': self.message,
            'received_number': self.received_number,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

@app.route('/increment_num', methods=['POST'])
def increment_num():
    data = request.get_json()
    
    # проверка входных данных
    if not data or 'number' not in data:
        return jsonify({
            "status": "error",
            "message": "Field 'number' is required in JSON body",
            "data": None,
            "logs": []
        }), 400

    raw_number = data.get('number')

    try:
        number = int(raw_number)
        if number < 0:
            return jsonify({
                "status": "error",
                "message": "Number must be positive",
                "data": None,
                "logs": []
            }), 400
    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Invalid number format",
            "data": None,
            "logs": []
        }), 400
    
    # проверка последовательности
    last_processed = ProcessedNumber.query.order_by(ProcessedNumber.id.desc()).first()
    if last_processed and number == last_processed.number - 1:
        error_message = f"Ошибка: число {number} меньше уже обработанного числа {last_processed.number}."
        new_log = Log(event_type='ERROR_SEQUENCE', message=error_message, received_number=number)
        db.session.add(new_log)
        db.session.commit()
        
        # логи
        recent_logs = Log.query.order_by(Log.timestamp.desc()).limit(1).all()
        logs_json = [log.to_dict() for log in recent_logs]

        return jsonify({
            "status": "error",
            "message": error_message,
            "data": None,
            "logs": logs_json
        }), 400

    # проверка на дубликат
    existing_number = ProcessedNumber.query.filter_by(number=number).first()
    if existing_number:
        error_message = f"Ошибка: число {number} уже было обработано ранее."
        new_log = Log(event_type='ERROR_DUPLICATE', message=error_message, received_number=number)
        db.session.add(new_log)
        db.session.commit()
        # логи
        recent_logs = Log.query.order_by(Log.timestamp.desc()).limit(1).all()
        logs_json = [log.to_dict() for log in recent_logs]

        return jsonify({
            "status": "error",
            "message": error_message,
            "data": None,
            "logs": logs_json
        }), 409
    
    # успешная обработка, инкрементируем
    result = number + 1

    # сохраняем число
    new_processed_number = ProcessedNumber(number=number)
    
    # логируем
    success_message = f"Число {number} успешно обработано. Результат: {result}."
    new_log = Log(event_type='SUCCESS', message=success_message, received_number=number)
    
    # добавляем обе записи в сессию и сохраняем
    db.session.add(new_processed_number)
    db.session.add(new_log)
    db.session.commit()

    # возвращаем результат
    return jsonify({
        "status": "success",
        "message": success_message,
        "data": {
            "original_number": number,
            "result": result
        },
        "logs": []
    }), 200