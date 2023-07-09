#######
# Delete? using tr01-modules...
#######
from sqlalchemy import create_engine, inspect
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

from app.package.config import ConfigLocal, ConfigDev, ConfigProd
# from app.package.config import config
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

if os.environ.get('FLASK_CONFIG_TYPE')=='local':
    config = ConfigLocal()
    
    print('* modelsBase: Development - Local')
    print('SQL_URI: ',config.SQL_URI)
elif os.environ.get('FLASK_CONFIG_TYPE')=='dev':
    config = ConfigDev()
    print('* modelsBase: Development')
elif os.environ.get('FLASK_CONFIG_TYPE')=='prod':
    config = ConfigProd()
    print('* modelsBase: Configured for Production')

if not os.path.exists(config.PROJ_DB_PATH):
    os.mkdir(config.PROJ_DB_PATH)

Base = declarative_base()
engine = create_engine(config.SQL_URI, echo = False, connect_args={"check_same_thread": False})
Session = sessionmaker(bind = engine)
sess = Session()


class Users(Base, UserMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key = True)
    email = Column(Text, unique = True, nullable = False)
    password = Column(Text, nullable = False)
    username = Column(Text, nullable = False)
    time_stamp_utc = Column(DateTime, nullable = False, default = datetime.utcnow)

    def get_reset_token(self, expires_sec=1800):
        s=Serializer(config.SECRET_KEY, expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s=Serializer(config.SECRET_KEY)
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return sess.query(Users).get(user_id)

    def __repr__(self):
        return f'Users(id: {self.id}, email: {self.email}, share: {self.share})'


class communityposts(Base):
    __tablename__ = 'communityposts'
    id = Column(Integer, primary_key = True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id_name_string = Column(Text)
    title = Column(Text)
    description = Column(Text)
    date_published = Column(DateTime, nullable=False, default=datetime.now)
    edited = Column(Text)
    post_html_filename = Column(Text)
    notes = Column(Text)
    time_stamp_utc = Column(DateTime, nullable = False, default = datetime.utcnow)
    comments = relationship('communitycomments', backref='comments', lazy=True)

    def __repr__(self):
        return f'communityposts(id: {self.id}, user_id: {self.user_id}, title: {self.title})'


class communitycomments(Base):
    __tablename__ = 'communitycomments'
    id = Column(Integer, primary_key = True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("communityposts.id"), nullable=False)
    comment = Column(Text)
    date_published = Column(DateTime, nullable=False, default=datetime.now)
    edited = Column(Text)
    post_html_filename = Column(Text)
    notes = Column(Text)
    time_stamp_utc = Column(DateTime, nullable = False, default = datetime.utcnow)

    def __repr__(self):
        return f'communitycomments(id: {self.id}, user_id: {self.user_id}, date_published: {self.date_published})'


if 'users' in inspect(engine).get_table_names():
    print("db already exists")
else:

    Base.metadata.create_all(engine)
    print("NEW db created.")