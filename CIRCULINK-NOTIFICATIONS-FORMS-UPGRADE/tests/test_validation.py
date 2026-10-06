from app.utils.validation import phone,email
def test_phone(): assert phone('0712345678')=='254712345678'
def test_email(): assert email('x@example.com')
