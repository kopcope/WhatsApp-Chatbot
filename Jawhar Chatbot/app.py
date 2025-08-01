from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return 'Welcome to the Jawhar Chatbot Flask server!'

if __name__ == '__main__':
    app.run(port=8000) 