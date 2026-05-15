from browser_agent.db import get_engine, Base
from browser_agent import models  # noqa: F401

def main():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("tables created")

if __name__ == "__main__":
    main()
