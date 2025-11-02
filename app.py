#import flask (web server + app server)
#import request (get, post)
#import render_template (Jinja2)

# run:
# source virt_environment/bin/activate
# export FLASK_APP=app.py
# flask run (flask run --debug)
# flask db init
# http://127.0.0.1:5000/

from flask import Flask, request, render_template

# не будем писать SQL вручную
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

#объект flask
app = Flask(__name__)

# конфиг для бд
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://vladislav:!Hello_World123@localhost/my_db'
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

    def __repr__(self):
        return f'<Log {self.id}: {self.event_type}>'
    
@app.route('/')
def index_page():
    # если кто-то зайдет на главную страницу, то эта функция будет выполняться
    return render_template('index.html')

@app.route('/increment_num', methods=['POST'])
def increment_num():
    number_str = request.form.get('number')

    # проверка входных данных
    if number_str is None:
        return "Ошибка: число не было передано в теле запроса", 400
    try:
        number = int(number_str)
        if number < 0:
            return "Число должно быть больше нуля", 400
    except ValueError:
        return "Ошибка: передано не число", 400

    # проверка последовательности
    last_processed = ProcessedNumber.query.order_by(ProcessedNumber.id.desc()).first()
    if last_processed and number == last_processed.number - 1:
        error_message = f"Ошибка: число {number} меньше уже обработанного числа {last_processed.number}."
        new_log = Log(event_type='ERROR_SEQUENCE', message=error_message, received_number=number)
        db.session.add(new_log)
        db.session.commit()

        # забираем логи, в лимите можно установить сколько логов выводить
        recent_logs = Log.query.order_by(Log.timestamp.desc()).limit(1).all()

        return render_template('error.html', error_message=error_message, logs=recent_logs), 400
    
    # проверка на дубликат
    existing_number = ProcessedNumber.query.filter_by(number=number).first()
    if existing_number:
        # если дубликат
        error_message = f"Ошибка: число {number} уже было обработано ранее."
        new_log = Log(event_type='ERROR_DUPLICATE', message=error_message, received_number=number)
        db.session.add(new_log)
        db.session.commit()
        
        # забираем логи, в лимите можно установить сколько логов выводить
        recent_logs = Log.query.order_by(Log.timestamp.desc()).limit(1).all()

        return render_template('error.html', error_message=error_message, logs=recent_logs), 409

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

    # возвращаем страницу с результатом
    return render_template('result.html', final_result=result, original_number=number)