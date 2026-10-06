def test_factory():
 from app import create_app
 assert create_app() is not None
