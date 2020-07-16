import base64
import os
from datetime import datetime
from hashlib import sha512

from peewee import (PostgresqlDatabase, BooleanField, CharField, DateTimeField,
    ForeignKeyField, Model) # TextField
from tornado.ioloop import IOLoop

from config import constants

peewee_db = PostgresqlDatabase(constants.DB_NAME, user=constants.DB_USER, password=constants.DB_PASS,
    host=constants.DB_HOST, port=constants.DB_PORT, sslmode=constants.DB_SSLMODE, autoconnect=False)


# NOTE: database functions are synchronous, so we have to run them in another thread to make them asynchronous
# while this can create additional overhead you SHOULD use these functions if you have a long running query
# if not, it can lock up the server
def threaded_db(func, *args):
    result = None
    with peewee_db.connection_context():
        result = func(*args)
    return result


# example use: async_db(list, User.select()) or async_db(User.select().count)
async def async_db(func, *args):
    result = await IOLoop.current().run_in_executor(None, threaded_db, func, *args)
    # NOTE: peewee is supposed to store connections per thread
    # and while you get an error about it not being open every time, it also looks like
    # closing the connection in the child can also close it in the main thread
    # so we check and re-open if needed - this assumes the connection is closed elsewhere (end of request)
    if peewee_db.is_closed():
        peewee_db.connect()
    return result


class BaseModel(Model):

    class Meta:
        database = peewee_db

    # used for backups on all model types
    created_dt = DateTimeField(default=datetime.utcnow)
    modified_dt = DateTimeField(default=datetime.utcnow)

    @property
    def slug(self):
        return str(self.id)

    @classmethod
    def getBySlug(cls, slug):
        # this is preferable to `get_by_id` because we can return None rather than an error
        return cls.select().where(cls.id == slug).first()

    def save(self, *args, **kwargs):
        self.modified_dt = datetime.utcnow()
        return super().save(*args, **kwargs)


class User(BaseModel):
    email = CharField()
    password_salt = CharField()
    hashed_password = CharField()
    token = CharField(null=True)
    token_dt = DateTimeField(null=True)
    # pic_url = CharField(null=True)
    is_admin = BooleanField(default=False)
    is_dev = BooleanField(default=False) # set this directly via the console

    @classmethod
    def getByAuth(cls, slug):
        auth = Auth.getBySlug(slug)
        return auth and auth.user or None

    @classmethod
    def getByEmail(cls, email):
        return cls.select().where(cls.email == email).first()

    @classmethod
    def hashPassword(cls, password, salt):
        return sha512(password.encode('utf8') + salt).hexdigest()

    @classmethod
    def changePassword(cls, password):
        salt = base64.b64encode(os.urandom(64))
        hashed_password = cls.hashPassword(password, salt)
        return salt, hashed_password

    def getAuth(self, user_agent):
        return self.auths.where(Auth.user_agent == user_agent).first()

    def resetPassword(self):
        # python b64 always ends in '==' so we remove them because this is for use in a URL
        self.token = base64.urlsafe_b64encode(os.urandom(16)).decode().replace('=', '')
        self.token_dt = datetime.utcnow()
        self.save()
        return self

    def toDict(self):
        return {'email': self.email}


class Auth(BaseModel):
    user_agent = CharField()
    os = CharField(null=True)
    browser = CharField(null=True)
    device = CharField(null=True)
    ip = CharField()
    user = ForeignKeyField(User, backref='auths')

    def toDict(self):
        return {
            'slug': self.slug,
            'user_agent': self.user_agent,
            'os': self.os,
            'browser': self.browser,
            'device': self.device,
            'ip': self.ip,
            'modified_dt': self.modified_dt.isoformat()
        }


def generateToken(size):
    return base64.urlsafe_b64encode(os.urandom(size)).decode().replace('=', '')


def reset():
    # order matters here - have to delete in the right direction given foreign key constraints
    tables = [Auth, User]

    for table in tables:
        table.drop_table()

    # order matters here too for establishing the foriegn keys, but it's reversed from above
    tables.reverse()
    for table in tables:
        table.create_table()


if __name__ == '__main__':
    ok = input('WARNING! This will drop all tables in the database. Continue? y/n ')

    if ok.lower() in ['y', 'yes']:
        peewee_db.connect()
        reset()
