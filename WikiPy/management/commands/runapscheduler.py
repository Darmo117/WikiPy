"""
This module defines a command that runs backgroud database tasks.

This command should be run after starting the server.
"""
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution

import WikiPy.api.db_tasks as api_db_tasks

logger = logging.getLogger(__name__)


def delete_old_job_executions(max_age=604_800):
    """This job deletes all apscheduler job executions older than "max_age" from the database."""
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


class Command(BaseCommand):
    help = 'Runs apscheduler.'

    # TODO
    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), 'default')

        scheduler.add_job(
            api_db_tasks.execute_pending_tasks,
            # TODO every hour?
            trigger=CronTrigger(second='*/10'),  # Every 10 seconds
            id='db_background_task',
            max_instances=1,
            replace_existing=True
        )
        logger.info('Added job "db_background_task".')

        scheduler.add_job(
            delete_old_job_executions,
            trigger=CronTrigger(
                day_of_week='mon', hour='00', minute='00'
            ),  # Midnight on Monday, before start of the next work week.
            id='delete_old_job_executions',
            max_instances=1,
            replace_existing=True
        )
        logger.info('Added weekly job: "delete_old_job_executions".')

        try:
            logger.info('Starting scheduler…')
            scheduler.start()
        except KeyboardInterrupt:
            logger.info('Stopping scheduler…')
            scheduler.shutdown()
            logger.info('Scheduler shut down successfully!')
