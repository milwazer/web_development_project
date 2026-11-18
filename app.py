from flask import Flask, render_template

app = Flask(__name__)
# загружаем настройки из config.py (секретный ключ сессии и параметры БД)
app.config.from_object('config')


@app.route('/')
def index():
    """Главная страница. Пока заглушка, список задач появится позже."""
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
