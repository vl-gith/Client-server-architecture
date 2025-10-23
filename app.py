#import flask
#import request (get, post)
#import render_template (Jinja2)

from flask import Flask, request, render_template

#object flask
app = Flask(__name__)

#connect in url-address in function hello-world
@app.route('/')
def index_page():
    #если кто-то зайдет на главную страницу, то эта функция будет выполняться
    return render_template('index.html')

@app.route('/increment_num', methods=['POST'])
def increment_num():
    #form data
    number_str = request.form.get('number')

    if number_str is None:
        return "Ошибка: число не было передано в теле запроса", 400

    try:
        number = int(number_str)
        if number < 0:
            return "Число должно быть больше нуля", 400
    except ValueError:
        return "Ошибка: передано не число", 400
    
    #далее можем взаимодействовать с бд
    result = number + 1

    #return f"Вы отправили число {number}. Результат: {result}"

    return render_template('result.html', final_result=result, original_number=number)