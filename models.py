from peewee import *
import datetime
from flask import Flask
from flask_login import UserMixin
from werkzeug.utils import secure_filename



app = Flask(__name__)
db = PostgresqlDatabase(
    'space',
    host = 'localhost',
    port = '5432',
    user = 'ladasedan',
    password = 'qwe123'
)

db.connect()

class BaseModel(Model):
    class Meta:
        database = db

class Users(UserMixin, BaseModel):
    username = CharField(max_length=255, null=False, unique=True)
    email = CharField(max_length=255, null=False, unique=True)
    age = IntegerField()
    full_name = CharField(max_length=255, null=True)
    password = CharField(max_length=255, null=False)
    image = CharField(max_length=255, default='media/avatars/default_avatar.png')

    def __repr__(self):
        return self.email

class Post(BaseModel):
    author = ForeignKeyField(Users, on_delete='CASCADE')
    title = CharField(max_length=255, null=False)
    content = TextField()
    created_date = DateTimeField(default=datetime.datetime.now)
    image = CharField(max_length=255, default='media/images_post/default_image.jpg')
    likes_count = IntegerField(default=0)


    def __repr__(self):
        return self.title
    
class Likes(BaseModel):
    post = ForeignKeyField(Post, backref='likes')
    user = ForeignKeyField(Users, backref='likes')

    class Meta:
        indexes = ((('post', 'user'), True),)


# db.create_tables([Likes])
# db.create_tables([Users, Post])






