## run worker
### linux
```shell
$ celery -A tasks worker --loglevel=INFO
```
### windows
```cmd
pip install eventlet
celery -A tasks worker --loglevel=INFO -P eventlet
```

## calling the task
```python
>>> from tasks import add
>>> result = add.delay(1, 1)
>>> result.ready()
>>> result.get(timeout=1)

>>> result = add.delay(1, '1')
>>> result.get(propagate=False)
>>> result.traceback
```

## canvas
### groups
```python
>>> from celery import group
>>> from proj.tasks import add

>>> group(add.s(i, i) for i in range(10))().get()
[0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
```
### chains
```python
>>> from celery import chain
>>> from proj.tasks import add, mul

# (4 + 4) * 8
>>> chain(add.s(4, 4) | mul.s(8))().get()
64
```
### chords
```python
>>> from celery import chord
>>> from proj.tasks import add, xsum

>>> chord((add.s(i, i) for i in range(10)), xsum.s())().get()
90
```
## routing
```python
>>> from proj.tasks import add
>>> add.apply_async((2, 2), queue='hipri')
```

# django
## topics
### Ensuring a task is only executed one at a time
```python
import time
from celery import task
from celery.utils.log import get_task_logger
from contextlib import contextmanager
from django.core.cache import cache
from hashlib import md5
from djangofeeds.models import Feed

logger = get_task_logger(__name__)

LOCK_EXPIRE = 60 * 10  # Lock expires in 10 minutes

@contextmanager
def memcache_lock(lock_id, oid):
    timeout_at = time.monotonic() + LOCK_EXPIRE - 3
    # cache.add fails if the key already exists
    status = cache.add(lock_id, oid, LOCK_EXPIRE)
    try:
        yield status
    finally:
        # memcache delete is very slow, but we have to use it to take
        # advantage of using add() for atomic locking
        if time.monotonic() < timeout_at and status:
            # don't release the lock if we exceeded the timeout
            # to lessen the chance of releasing an expired lock
            # owned by someone else
            # also don't release the lock if we didn't acquire it
            cache.delete(lock_id)

@task(bind=True)
def import_feed(self, feed_url):
    # The cache key consists of the task name and the MD5 digest
    # of the feed URL.
    feed_url_hexdigest = md5(feed_url).hexdigest()
    lock_id = '{0}-lock-{1}'.format(self.name, feed_url_hexdigest)
    logger.debug('Importing feed: %s', feed_url)
    with memcache_lock(lock_id, self.app.oid) as acquired:
        if acquired:
            return Feed.objects.import_feed(feed_url).url
    logger.debug(
        'Feed %s is already being imported by another worker', feed_url)
```