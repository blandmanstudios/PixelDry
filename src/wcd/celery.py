#!/usr/bin/env python3

from celery import Celery

app = Celery('wcd',
             broker='redis://localhost:6379/0',
             include=['wcd.tasks'])

# Optional configuration, see the application user guide.
app.conf.update(
    result_expires=3600,
)

if __name__ == '__main__':
    app.start()

