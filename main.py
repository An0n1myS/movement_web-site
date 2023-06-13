import secrets
import base64

from flask import Flask, render_template, request, redirect, url_for, session
import pymysql

app = Flask(__name__, template_folder="./")

app.secret_key = secrets.token_hex(16)

# Конфігурація бази даних
db = pymysql.connect(host='localhost', user='root', password='', db='hotel_booking', charset='utf8mb4')
cursor = db.cursor()


@app.route('/demo')
def demo():

    return render_template('exportToHTML/main.py.html')

@app.route('/')
def index():
    # Отримання списку готелів з бази даних
    cursor.execute("SELECT * FROM hotels")
    hotels = cursor.fetchall()

    encoded_hotels = []
    for hotel in hotels:
        photo_data = base64.b64encode(hotel[5]).decode('utf-8')
        encoded_hotels.append((hotel[0], hotel[1], hotel[2], hotel[3], hotel[4], photo_data))

    return render_template('index.html', hotels=encoded_hotels)


# Додавання нового готелю
@app.route('/add_hotel', methods=['POST'])
def add_hotel():
    name = request.form['name']
    description = request.form['description']
    location = request.form['location']
    rating = request.form['rating']
    photo = request.form['photo']

    # Додавання нового готелю до бази даних
    cursor.execute("INSERT INTO hotels (name, description, location, rating, photo) VALUES (%s, %s, %s, %s, %s)",
                   (name, description, location, rating, photo))
    db.commit()

    return redirect(url_for('index'))


# Сторінка з усіма готелями
@app.route('/hotels')
def hotels():
    # Отримання списку готелів з бази даних
    cursor.execute("SELECT * FROM hotels")
    hotels = cursor.fetchall()

    encoded_hotels = []
    for hotel in hotels:
        photo_data = base64.b64encode(hotel[5]).decode('utf-8')
        encoded_hotels.append((hotel[0], hotel[1], hotel[2], hotel[3], hotel[4], photo_data))

    return render_template('hotels.html', hotels=encoded_hotels)


# Сторінка з деталями готелю
@app.route('/hotel/<int:hotel_id>')
def hotel(hotel_id):
    # Отримання інформації про готель з бази даних
    cursor.execute("SELECT * FROM hotels WHERE id_hotel = %s", (hotel_id,))
    hotel = cursor.fetchone()

    # Отримання інформації про кімнати готелю з бази даних
    cursor.execute("SELECT * FROM rooms WHERE id_hotel = %s", (hotel_id,))
    rooms = cursor.fetchall()

    encoded_hotels =[]
    photo_data = base64.b64encode(hotel[5]).decode('utf-8')
    encoded_hotels.append(hotel[0])
    encoded_hotels.append(hotel[1])
    encoded_hotels.append(hotel[2])
    encoded_hotels.append(hotel[3])
    encoded_hotels.append(hotel[4])
    encoded_hotels.append(photo_data)
    # Створення словника для збереження фотографій кімнат
    room_photos = {}

    for room in rooms:
        room_id = room[0]
        # Отримання фотографій кімнати з бази даних
        cursor.execute("SELECT * FROM room_photos WHERE id_room = %s", (room_id,))
        photos = cursor.fetchall()

        # Перекодування фотографій у base64
        encoded_photos = []
        for photo in photos:
            encoded_photo = base64.b64encode(photo[2]).decode('utf-8')
            encoded_photos.append(encoded_photo)

        room_photos[room_id] = encoded_photos

    # Отримання відгуків про готель з бази даних
    cursor.execute("SELECT * FROM reviews WHERE id_hotel = %s", (hotel_id,))
    reviews = cursor.fetchall()

    return render_template('hotel-details.html', hotel=encoded_hotels, rooms=rooms, room_photos=room_photos, reviews=reviews)


@app.route('/booking', methods=['POST'])
def handle_booking():
    # Получение данных из формы бронирования
    check_in = request.form['check-in']
    check_out = request.form['check-out']

    # Получение данных о пользователе из сессии
    user_id = session['username']

    # Получение данных о комнате из формы
    room_id = request.form['room-id']

    # SQL-запрос для вставки данных в таблицу booking
    insert_query = "INSERT INTO bookings (id_user, id_room, check_in_date, check_out_date) VALUES (%s, %s, %s, %s)"
    values = (user_id, room_id, check_in, check_out)
    cursor.execute(insert_query, values)
    db.commit()

    return redirect(url_for('index'))

# Обробка відправлення відгуку
@app.route('/submit-review', methods=['POST'])
def submit_review():
    # Отримання даних з форми
    rating = request.form.get('rating')
    comment = request.form.get('comment')

    # Перевірка чи заповнені обов'язкові поля
    if rating is None or comment is None:
        return 'Будь ласка, заповніть усі поля форми.'

    # Отримання ідентифікаторів користувача і готелю (якщо потрібно)
    hotel_id = request.form.get('hotel_id')  # Встановіть ідентифікатор користувача, якщо використовується авторизація
    user_id = session['username']  # Встановіть ідентифікатор готелю, якщо використовується відповідний готель

    # Збереження відгуку в базі даних
    cursor.execute("INSERT INTO reviews (id_user, id_hotel, rating, comment) VALUES (%s, %s, %s, %s)",
                   (user_id, hotel_id, rating, comment))
    db.commit()

    # Повернення перенаправлення на ту саму сторінку
    return redirect(url_for('hotel', hotel_id=hotel_id))


@app.route('/profile')
def profile():
     if 'username' not in session:
         return redirect(url_for('login'))
     else:
        # Отримання даних користувача з бази даних
        cursor.execute("SELECT * FROM users WHERE id_user = %s", (session['username'],))
        user = cursor.fetchone()

        # Отримання даних про бронювання користувача з бази даних
        cursor.execute("""
            SELECT bookings.id_booking, hotels.name, rooms.type, rooms.price, bookings.check_in_date, bookings.check_out_date
            FROM bookings
            INNER JOIN users ON bookings.id_user = users.id_user
            INNER JOIN rooms ON bookings.id_room = rooms.id_room
            INNER JOIN hotels ON rooms.id_hotel = hotels.id_hotel
            WHERE users.id_user = %s
        """, (session['username'],))
        bookings = cursor.fetchall()

        return render_template('profile.html', user=user, bookings=bookings)



# Сторінка авторизації
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Перевірка введених даних з базою даних
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()

        if user:
            # Авторизація успішна, збереження ідентифікатора користувача у сесії
            session['username'] = user[0]
            return redirect(url_for('index'))
        else:
            # Авторизація невдала, повідомлення про помилку
            error = 'Невірний електронний лист або пароль.'
            return render_template('templates/login.html', error=error)
    else:
        return render_template('templates/login_form.html')


# Сторінка реєстрації
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        country = request.form['country']
        language = request.form['language']

        # Перевірка, чи користувач з вказаним електронним листом вже існує
        cursor.execute("SELECT * FROM users WHERE email = %s", email)
        existing_user = cursor.fetchone()

        if existing_user:
            # Користувач вже існує, повідомлення про помилку
            error = 'Користувач з таким електронним листом уже існує.'
            return render_template('templates/register_form.html', error=error)
        else:
            # Додавання нового користувача до бази даних
            cursor.execute("INSERT INTO users (name, email, password, country, language) VALUES (%s, %s, %s, %s, %s)",
                           (name, email, password, country, language))
            db.commit()

            return redirect(url_for('login'))
    else:
        return render_template('templates/register_form.html')


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':

        session.pop('username', None)
        session.pop('user_id', None)

        return redirect('/')
    else:
        return render_template('error.html')


if __name__ == '__main__':
    app.run(debug=True)
