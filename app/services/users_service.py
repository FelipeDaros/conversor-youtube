from app.models.user import User
from sqlalchemy.exc import IntegrityError
import bcrypt

class UserService:
    def __init__(self, db_session):
        self.db = db_session

    async def create_user(self, username: str, email: str, password: str):
        """Cria um novo usuário no banco de dados."""
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password.decode('utf-8')
        )
        self.db.add(new_user)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Username or email already exists")
        return new_user