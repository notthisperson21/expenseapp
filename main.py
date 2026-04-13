from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def root():
    return {'message': 'Expense app backend running'}

@app.get('/status')
def status():
    return {'status': 'ok'}
