"""Entry point for AWS Elastic Beanstalk. EB expects `application` as the WSGI callable."""
from app import app as application

if __name__ == "__main__":
    application.run()
