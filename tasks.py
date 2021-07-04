from celery import Celery

app = Celery('tasks', backend='redis://localhost', broker='amqp://zhangshun:123456@localhost:5672/')

@app.task
def add(x, y):
    return x + y