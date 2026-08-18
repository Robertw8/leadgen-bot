from sqlalchemy import text

from app.db.base import Base
from app.db.session import engine


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
        conn.commit()
    print('db initialized')


if __name__ == '__main__':
    main()
