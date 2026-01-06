try:
    from sqlalchemy import Column, Integer, String, DateTime
    from sqlalchemy.sql import func
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()
except ImportError:
    Base = object
    Column = lambda *args, **kwargs: None
    Integer = String = DateTime = None
    func = None

class User(Base):
    __tablename__ = "users"

    if Base is not object:
        id = Column(String, primary_key=True, index=True)
        username = Column(String, unique=True, index=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
    else:
        id = None
        username = None
        created_at = None

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
