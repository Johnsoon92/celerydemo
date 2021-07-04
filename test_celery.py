from tasks import add
from celery import Task

def test_add():
    add: Task
    add.delay()