# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import datetime
import subprocess
import time

from celery import Celery
from celery import states as celery_states

from airflow.config_templates.default_celery import DEFAULT_CELERY_CONFIG
from airflow.exceptions import AirflowException
from airflow.executors.base_executor import BaseExecutor
from airflow import configuration
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.module_loading import import_string

PARALLELISM = configuration.get('core', 'PARALLELISM')

'''
To start the celery worker, run the command:
airflow worker
'''

if configuration.has_option('celery', 'celery_config_options'):
    celery_configuration = import_string(
        configuration.get('celery', 'celery_config_options')
    )
else:
    celery_configuration = DEFAULT_CELERY_CONFIG

app = Celery(
    configuration.get('celery', 'CELERY_APP_NAME'),
    config_source=celery_configuration)


@app.task
def execute_command(command):
    log = LoggingMixin().log
    log.info("Executing command in Celery: %s", command)
    try:
        subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        log.error(e)
        raise AirflowException('Celery command failed')


class CeleryExecutor(BaseExecutor):
    """
    CeleryExecutor is recommended for production use of Airflow. It allows
    distributing the execution of task instances to multiple worker nodes.

    Celery is a simple, flexible and reliable distributed system to process
    vast amounts of messages, while providing operations with the tools
    required to maintain such a system.
    """
    def start(self):
        self.tasks = {}
        self.last_state = {}
        self.enqueue_time = {}
        self.command = {}
        self.queue = {}

    def execute_async(self, key, command,
                      queue=DEFAULT_CELERY_CONFIG['task_default_queue']):
        self.log.info( "[celery] queuing {key} through celery, "
                       "queue={queue}".format(**locals()))
        self.tasks[key] = execute_command.apply_async(
            args=[command], queue=queue)
        self.last_state[key] = celery_states.PENDING
        self.enqueue_time[key] = datetime.datetime.now()
        self.command[key] = command
        self.queue[key] = queue

    def _get_reserved_task_ids(self):
        global app
        inspector = app.control.inspect()
        return [item['id'] for sublist in inspector.reserved().values() for item in sublist]

    def sync(self):
<<<<<<< 1aa203d1a2f3f149eff75fe397da5cb0cf96c750
        self.log.debug("Inquiring about %s celery task(s)", len(self.tasks))
=======
        self.logger.debug(
            "Inquiring about {} celery task(s)".format(len(self.tasks)))
        reserved_task_ids = self._get_reserved_task_ids()
>>>>>>> fix issue
        for key, async in list(self.tasks.items()):
            try:
                state = async.state
                if self.last_state[key] != state:
                    if state == celery_states.SUCCESS:
                        self.success(key)
                        del self.tasks[key]
                        del self.last_state[key]
                    elif state == celery_states.FAILURE:
                        self.fail(key)
                        del self.tasks[key]
                        del self.last_state[key]
                    elif state == celery_states.REVOKED:
                        self.fail(key)
                        del self.tasks[key]
                        del self.last_state[key]
                    else:
                        self.log.info("Unexpected state: %s", async.state)
                    self.last_state[key] = async.state
                elif async.task_id in reserved_task_ids:
                    last_acceptable_time = (
                            self.enqueue_time[key] +
                            datetime.timedelta(seconds=conf.getint('scheduler', 'JOB_HEARTBEAT_SEC') * 2.1))
                    if datetime.datetime.now() > last_acceptable_time:
                        self.logger.warning("Requeueing task with key {key} as "
                                            "it has been reserved for too long."
                                            .format(key=key))
                        async.revoke()
                        self.execute_async(key, self.command[key], queue=self.queue[key])
            except Exception as e:
                self.log.error("Error syncing the celery executor, ignoring it:")
                self.log.exception(e)

    def end(self, synchronous=False):
        if synchronous:
            while any([
                    async.state not in celery_states.READY_STATES
                    for async in self.tasks.values()]):
                time.sleep(5)
        self.sync()
