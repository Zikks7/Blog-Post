from flask import jsonify, Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user, logout_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import datetime, os


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']=os.getenv("DATABASE_URL")
app.secret_key="ichascnchdcuncducbeduc"

db = SQLAlchemy(app)

migrate = Migrate(app,db)

@app.before_request
def make_session_short():
    session.permanent=True
    app.permanent_session_lifetime= datetime.timedelta(hours=24)

class Users(db.Model, UserMixin):
    __tablename__ = "users" 
    id = db.Column(db.Integer(), primary_key= True, unique=True)
    username = db.Column(db.String(50),nullable = False, unique = True) 
    email = db.Column(db.String(), nullable = False, unique = True)
    gender = db.Column (db.String(), nullable= False)
    password =db.Column(db.String(), nullable = False)
    
    def __repr__(self):
        return f"User: <{self.username}>"

    def get_id(self):
        return str(self.id)

class Posts(db.Model):
    __tablename__ = "post"
    id = db.Column(db.Integer(), primary_key = True, unique = True)
    title = db.Column(db.String(), nullable= False, unique = True)
    content = db.Column(db.Text(),nullable = False)
    created_on = db.Column(db.DateTime, default = datetime.datetime.now())
    user_id = db.Column(db.Integer(), db.ForeignKey("users.id"))
    author = db.Column(db.String(), nullable = False)
    created_by = db.relationship("Users", backref = "articles_by", lazy = True)

    def __repr__(self):
        return f"Title: <{self.title}>"



with app.app_context():
    db.create_all()

# initializing the login manager
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(user_id)

year = datetime.datetime.now().year

@app.route('/')
def home():
    blogs = Posts.query.all()
    return render_template('index.html', blogs = blogs, current_year = year)


@app.route('/signup',methods=["POST","GET"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        gender = request.form.get("gender")

        email_check=Users.query.filter_by(email=email).first()
        user_check= Users.query.filter_by(username=username).first()
        try:
            if user_check or email_check:
                return jsonify ({"user or email already exist"}),400
            new_user = Users(username=username, email =email, password =generate_password_hash(password), gender=gender)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except Exception as e:
            return jsonify ({"Error":f"Internal Server Error: {str(e)}"}), 500
    return render_template('signup.html', current_year = year)

@app.route('/login', methods= ["POST", "GET"])
def login():
    email= request.form.get("email")
    password = request.form.get("password")

    if request.method == "POST":
        email_check= Users.query.filter_by(email=email).first()
        if email_check and check_password_hash(email_check.password,password):
            login_user(email_check)
            return redirect (url_for('post'))
        else:
            return ("Invalid Email or password")

    return render_template('login.html', current_year = year)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for("home"))

 
@app.route('/post', methods=["POST", "GET"])
@login_required
def post():
    if request.method== "POST":
        title= request.form.get("title")
        content = request.form.get("content")
        author = request.form.get("author")
        user_id = current_user.id
        
        title_check = Posts.query.filter_by(title = title).first()
        if title_check:
            return (f" A post with {title} already exists")
        else:
            new_post = Posts(title = title, user_id = user_id, content= content, author= author)
            print (new_post)
            db.session.add(new_post)
            db.session.commit()
            return redirect (url_for('home'))
    return render_template('post.html', current_year = year)


@app.route('/blogs', methods =['GET', 'POST'])
def blogs():
    blogs = Posts.query.all()

    return render_template("view.html", blogs = blogs, current_year = year)

@app.route('/profile', methods = ['GET','POST'])
@login_required
def profile():
    user_id = current_user.id
    user_info = Users.query.filter_by(id=user_id).first()
    users_posts = Posts.query.filter_by(user_id=user_id).all()
    return render_template("dashboard.html", user_info= user_info, users_posts= users_posts, current_year = year)


@app.route('/edit/<int:post_id>', methods =['GET', 'POST'])
@login_required
def edit(post_id):
    post_to_edit = Posts.query.get_or_404(post_id)
    if request.method == "POST":
        title= request.form.get("title")
        content = request.form.get("content")

        if title:
            post_to_edit.title = title
        if content:
            post_to_edit.content = content
        else:
            post_to_edit.title=title
            post_to_edit.content=content
        db.session.commit()
        return redirect(url_for("profile"))
    return render_template("edit.html", posts=post_to_edit) 


@app.route('/delete', methods = ['GET','POST'])
def delete():
    post_id = request.args.get("post_id")
    if not post_id:
        return jsonify({"error": "Missing post_id parameter"}), 400
    post_to_delete = Posts.query.filter_by(id=post_id).first()
    if not post_to_delete:
        return jsonify({"error": "Post not found"}), 404
    try:
        db.session.delete(post_to_delete)
        db.session.commit()
        return redirect(url_for('profile'))
    except Exception as e:
        db.session.rollback()  # Rollback to avoid corruption
        return jsonify({"error": f"internal server error, Error: {str (e)}"}),500

if __name__ == '__main__':
    app.run(debug=True)

