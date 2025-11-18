from urllib import request
from flask import Flask, render_template, redirect, url_for, session, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField
from wtforms.validators import DataRequired, Email, ValidationError
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL
import pandas as pd
import joblib
from utils import preprocess_text
from neputils import remove_stopwords_and_stem as nepali_preprocess

model = joblib.load("data/fake_news_model.pkl")
vectorizer = joblib.load("data/tfidf_vectorizer.pkl")
nep_model = joblib.load("data/nepali/nep_fake_news_model.pkl")
nep_vectorizer = joblib.load("data/nepali/nep_tfidf_vectorizer.pkl")


app = Flask(__name__)
bcrypt = Bcrypt(app)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'mydatabase'
app.secret_key = 'your_secret_key_here'

mysql = MySQL(app)

class RegisterForm(FlaskForm):
    name = StringField("Name",validators=[DataRequired()])
    email = StringField("Email",validators=[DataRequired(), Email()])
    password = PasswordField("Password",validators=[DataRequired()])
    submit = SubmitField("Register")

    def validate_email(self,field):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users where email=%s",(field.data,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            raise ValidationError('Email Already Taken')

class LoginForm(FlaskForm):
    email = StringField("Email",validators=[DataRequired(), Email()])
    password = PasswordField("Password",validators=[DataRequired()])
    submit = SubmitField("Login")



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register',methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # store data into database 
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (name,email,password) VALUES (%s,%s,%s)",(name,email,hashed_password))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('login'))

    return render_template('register.html',form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Admin login check first
        if email == 'admin@gmail.com' and password == 'admin123':
            session['user_id'] = 'admin'
            flash("Welcome, Admin!", "success")
            return redirect(url_for('admin_home'))

        # Normal user login
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()

        # Assuming user[3] is password hash column
        if user and bcrypt.check_password_hash(user[3], password):
            session['user_id'] = user[0]
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Login failed. Please check your email and password", "danger")
            return redirect(url_for('login'))

    return render_template('login.html', form=form)



@app.route('/admin_home')
def admin_home():
    if 'user_id' not in session or session['user_id'] != 'admin':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()

    # 1. News categories for pie chart
    cursor.execute("SELECT category, COUNT(*) FROM news GROUP BY category")
    category_data = cursor.fetchall()  # [(category1, count1), (category2, count2), ...]

    categories = [row[0] for row in category_data]
    category_counts = [row[1] for row in category_data]

    # 2. Number of users
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    # 3. Number of news portals
    cursor.execute("SELECT COUNT(*) FROM websites")
    portal_count = cursor.fetchone()[0]

    cursor.close()

    return render_template('admin_home.html',
                           categories=categories,
                           category_counts=category_counts,
                           user_count=user_count,
                           portal_count=portal_count)





@app.route('/add_URLs', methods=['GET', 'POST'])
def add_URLs():
    if 'user_id' not in session or session['user_id'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        url = request.form.get('url')

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO websites (name, url) VALUES (%s, %s)", (name, url))
        mysql.connection.commit()
        cursor.close()

        flash(f"URL '{name}' added successfully!", "success")
        return redirect(url_for('add_URLs'))

    # GET request → show the form
    return render_template('add_URLs.html')

@app.route('/users', methods=['GET', 'POST'])
def users_page():
    if 'user_id' not in session or session['user_id'] != 'admin':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()

    # ---- Handle Delete Request ----
    if request.method == 'POST' and 'delete_id' in request.form:
        delete_id = request.form['delete_id']
        cursor.execute("DELETE FROM users WHERE id = %s", (delete_id,))
        mysql.connection.commit()

    # ---- Handle Edit Request ----
    elif request.method == 'POST' and 'edit_id' in request.form:
        edit_id = request.form['edit_id']
        name = request.form['name']
        email = request.form['email']
        cursor.execute("UPDATE users SET name=%s, email=%s WHERE id=%s", (name, email, edit_id))
        mysql.connection.commit()

    # ---- Fetch All Users ----
    cursor.execute("SELECT id, name, email FROM users")
    users = cursor.fetchall()
    cursor.close()

    return render_template('users_page.html', users=users)


@app.route('/newsportal')
def newsportals():
    if 'user_id' not in session or session['user_id'] != 'admin':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, name, url FROM websites")
    websites = cursor.fetchall()
    cursor.close()

    return render_template('newsportals.html', websites=websites)

@app.route('/news', methods=['GET', 'POST'])
def news():
    if 'user_id' not in session or session['user_id'] != 'admin':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()

    # If the delete button was clicked
    if request.method == 'POST':
        news_id = request.form.get('news_id')
        cursor.execute("DELETE FROM news WHERE id = %s", (news_id,))
        mysql.connection.commit()
        flash("News deleted successfully!", "success")
        return redirect(url_for('news'))

    # Otherwise, fetch and display all news
    cursor.execute("SELECT id, title, content, author_name, category FROM news")
    news_data = cursor.fetchall()
    cursor.close()

    return render_template('news.html', news_data=news_data)

@app.route('/insertnews', methods=['GET', 'POST'])
def insert_news_page():
    # Only admin can access
    if 'user_id' not in session or session['user_id'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get form data
        title = request.form['title']
        content = request.form['content']
        author_name = request.form['author_name']
        category = request.form['category']

        # Insert into database
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO news (title, content, author_name, category) VALUES (%s, %s, %s, %s)",
            (title, content, author_name, category)
        )
        mysql.connection.commit()
        cursor.close()

        flash('News added successfully!', 'success')
        return redirect(url_for('insert_news_page'))  # Redirect back to form

    # Render form page (GET request)
    return render_template('insert_news_page.html')



@app.route('/home')
@app.route('/home/<int:news_id>')
def home(news_id=None):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Admin redirect
    if user_id == 'admin':
        return redirect(url_for('admin_home'))

    cursor = mysql.connection.cursor()
    
    # Fetch user info
    cursor.execute("SELECT id, name, email FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()

    if news_id:  # If a specific news is requested
        cursor.execute("SELECT title, content, author_name, category FROM news WHERE id=%s", (news_id,))
        news = cursor.fetchone()
        cursor.close()

        if not news:
            return "News not found", 404

        return render_template('view_news.html', user=user, news=news)

    # Else, show home with all news
    cursor.execute("SELECT id, title, content, author_name, category FROM news ORDER BY category")
    news_items = cursor.fetchall()
    cursor.close()

    # Organize news by category
    news_by_category = {}
    for n in news_items:
        cat = n[4]  # category
        if cat not in news_by_category:
            news_by_category[cat] = []
        news_by_category[cat].append({
            'id': n[0],
            'title': n[1],
            'content': n[2],
            'author_name': n[3]
        })

    return render_template('home.html', user=user, news_by_category=news_by_category)





@app.route('/urltest', methods=['GET', 'POST'])
def urltest():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    message = None

    if request.method == 'POST':
        url_input = request.form.get('url')
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM websites")
        all_websites = cursor.fetchall()
        cursor.close()

        found = False
        for website in all_websites:
            db_url = website[2]  # assuming url is in column index 2
            if db_url in url_input:
                message = f"The URL provided is reliable and  from registered newsportal as '{website[1]}'."  # assuming name is in column 1
                found = True
                break

        if not found:
            message = f"The URL '{url_input}' is NOT from registered newsportal and may not be reliable."

    return render_template('urltest.html', message=message)






@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out successfully.")
    return redirect(url_for('login'))

@app.route('/english', methods=['GET', 'POST'])
def english():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, name, email FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close()

    if not user:
        return redirect(url_for('login'))

    prediction = None
    news_text = ""

    if request.method == 'POST':
        news_text = request.form['news_text']
        processed_text = preprocess_text(news_text)
        vectorized_text = vectorizer.transform([processed_text]).toarray()
        pred = model.predict(vectorized_text)
        prediction = "Real" if pred[0] == 1 else "Fake"

    return render_template('english.html', user=user, prediction=prediction, news_text=news_text)


@app.route('/nepali', methods=['GET', 'POST'])
def nepali():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, name, email FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close()

    if not user:
        return redirect(url_for('login'))

    prediction = None
    news_text = ""

    if request.method == 'POST':
        news_text = request.form['news_text']  # match the textarea name="news" in your form
        processed_text = nepali_preprocess(news_text)  # use neputils preprocessing
        vectorized_text = nep_vectorizer.transform([processed_text])  # use the Nepali vectorizer
        pred = nep_model.predict(vectorized_text)  # predict
        prediction = "Real News" if pred[0] == 1 else "Fake News"

    return render_template('nepali.html', user=user, prediction=prediction, news_text=news_text)



if __name__ == '__main__':
    app.run(debug=True)