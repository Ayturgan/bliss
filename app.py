from flask import Flask, render_template, request, redirect, flash, jsonify
from flask_login import login_required, current_user, LoginManager, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import re
from models import db, Post, Users, Likes
import time

def current_time():
    return int(time.time())


app = Flask(__name__, static_url_path='/static')
app.secret_key = os.urandom(24)


app.config['UPLOAD_FOLDER'] = 'static/media/avatars'
app.config['UPLOAD_FOLDER_POST'] = 'static/media/images_post'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}


login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def save_avatar(avatar):
    if avatar and allowed_file(avatar.filename):
        filename = secure_filename(avatar.filename)
        avatar.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return f'media/avatars/{filename}'  # Вернем путь к файлу для сохранения в базе данных
    else:
        return 'media/avatars/default_avatar.png'  # Возвращаем путь к дефолтной аватарке, если загрузка не удалась

def save_image_post(image):
    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER_POST'], filename))
        return f'media/images_post/{filename}'  
    else:
        return 'media/images_post/default_image.jpg'  
    


@login_manager.user_loader
def load_user(user_id):
    return Users.select().where(Users.id==int(user_id)).first()

@app.context_processor
def user_context_processor():
    return dict(user=current_user)


@app.before_request
def before_request():
    db.connect()

@app.after_request
def after_request(response):
    db.close()
    return response

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        email = request.form['email']
        password = request.form['password']
        user = Users.select().where(Users.email==email).first()
        if not user or not check_password_hash(user.password, password):
            flash('Please check you login details and try again.')
            return redirect('/login/')
        else:
            login_user(user)
            return redirect('/current_profile/')
    return render_template('login.html')

@app.route('/logout/')
def logout():
    logout_user()
    return redirect('/login/')


def validate_password(password):
    if len(password) < 8:
        return False
    if not re.search("[a-z]", password):
        return False
    if not re.search("[A-Z]", password):
        return False
    if not re.search("[0-9]", password):
        return False
    return True
    
    

@app.route('/register/', methods=('GET', 'POST'))
def register():
    if request.method=='POST':
        email = request.form['email']
        username = request.form['username']
        age = request.form['age']
        full_name = request.form['full_name']
        password = request.form['password']
        avatar = request.files['avatar']
        user = Users.select().where(Users.email==email).first()
        if user:
            flash('email addres already exists')
            return redirect('/register/')
        if Users.select().where(Users.username==username).first():
            flash('username already exists')
            return redirect('/register/')
        else:
            if validate_password(password):
                avatar_path = save_avatar(avatar) if avatar else 'media/avatars/default_avatar.png'
                Users.create(
                    email=email,
                    username=username,
                    age=age,
                    full_name=full_name,
                    password=generate_password_hash(password),
                    image=avatar_path,
                )
                return redirect('/login/')
            else:
                flash('Wrong password')
                return redirect('/register/')
            
    return render_template('register.html')

@app.route('/create/', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == "POST":
        if 'title' in request.form and 'content' in request.form and 'image' in request.files:
            title = request.form['title']
            content = request.form['content']
            image = request.files['image']
            
            image_post_path = save_image_post(image) if image and allowed_file(image.filename) else 'media/images_post/default_image.jpg'
            
            Post.create(
                title=title,
                author=current_user,
                content=content,
                image=image_post_path,
            )
            
            return redirect('/')
        else:
            flash('Please fill all required fields and select a valid image file.')
    return render_template('create.html', user=current_user)

# @app.route('/like/<int:id>/', methods=['POST'])
# def like_post(id):
#     post = Post.get_or_none(Post.id == id)
#     if post:
#         post.likes_count += 1
#         post.save()
#         return jsonify({'likes_count': post.likes_count})
#     return jsonify({'error': 'Post not found'}), 404

@app.route('/like/<int:id>/', methods=['POST'])
def like_post(id):
    if request.method == 'POST':
        post = Post.get_or_none(Post.id == id)
        if post:
            user = current_user._get_current_object()
            like = Likes.get_or_none(post=post, user=user)

            if like:
                # Если пользователь уже поставил лайк, удаляем его
                like.delete_instance()
                post.likes_count -= 1
            else:
                # Если пользователь еще не лайкнул, добавляем лайк
                Likes.create(post=post, user=user)
                post.likes_count += 1

            post.save()

            return jsonify({'likes_count': post.likes_count})
    return jsonify({'error': 'Invalid request'}), 400


@app.route('/<int:id>/', methods=['GET', 'POST'])
def post_detail(id):
    post = Post.select().where(Post.id == id).first()

    # Если метод запроса GET, то отобразить страницу с деталями поста
    if post:
        return render_template('post_detail.html', post=post, user=current_user)
    
    return f'Post with id = {id} does not exist'


@app.route('/')
def index():
    all_posts = Post.select()
    return render_template('index.html', posts=all_posts)






@app.route('/<int:id>/update/', methods=('GET', 'POST'))
@login_required
def update(id):
    post = Post.select().where(Post.id==id).first()
    if request.method == "POST":
        if post:
            if current_user==post.author:

                title = request.form['title']
                content = request.form['content']
                image = request.files['image']

                # if image:  # Если загружено новое изображение
                #     # Удаление старого изображения (если необходимо)
                #     if post.image and post.image != 'static/media/images_post/default_image.jpg':
                #         os.remove(os.path.join(app.root_path, 'static', post.image))

                    # Сохранение нового изображения
                image_post_path = save_image_post(image)
                post.image = image_post_path

                # Обновление других полей
                post.title = title
                post.content = content
                post.save()
                return redirect(f'/{id}/')
            return f'You are not author of this post'
        return f'Post with id = {id} does not exists'
    return render_template('update.html', post=post, user=current_user)



@app.route('/<int:id>/delete/', methods=('GET', 'POST'))
@login_required
def delete(id):
    post = Post.select().where(Post.id==id).first()
    if request.method == "POST":
        if post:
            if current_user==post.author:
                post.delete_instance()
                return redirect('/')
            return f'You are not author of this post'
        return f'Post with id = {id} does not exists'
    return render_template('delete.html', post=post, user=current_user)


@app.route('/profile/<int:id>/', methods=('GET', 'POST'))
def profile(id):
    profile_user = Users.select().where(Users.id == id).first()
    posts = Post.select().where(Post.author_id == id)
    return render_template('profile_base.html', user=profile_user, posts=posts)



@app.route('/current_profile/')
@login_required
def current_profile():
    posts = Post.select().where(Post.author_id==current_user.id)
    return render_template('profile.html', user=current_user, posts=posts)



@app.route('/<int:id>/update_profile/', methods=('GET', 'POST'))
@login_required
def update_profile(id):
    user = Users.select().where(Users.id == id).first()
    if request.method == "POST":
        if current_user==user:
            full_name = request.form['full_name']
            age = request.form['age']
            email = request.form['email']
            avatar = request.files['avatar']
            
            avatar_path = save_avatar(avatar)
            user.image = avatar_path

            user.full_name = full_name
            user.age = age
            user.email = email
            user.save()
            return redirect('/current_profile/')
    return render_template('update_profile.html', user=current_user)



if __name__ == '__main__':
    app.run(debug=True)
