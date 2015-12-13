from __future__ import absolute_import
from datetime import datetime, timedelta

from grab.spider.error import SpiderMisuseError
from grab.base import copy_config


class BaseTask(object):
    pass


class Task(BaseTask):
    """
    Task for spider.
    """

    def __init__(self, name=None, url=None, grab=None, grab_config=None,
                 priority=None, priority_is_custom=True,
                 network_try_count=0, task_try_count=1,
                 disable_cache=False, refresh_cache=False,
                 valid_status=[], use_proxylist=True,
                 cache_timeout=None, delay=0,
                 raw=False, callback=None,
                 fallback_name=None,
                 error_callback=None,
                 **kwargs):
        """
        Create `Task` object.

        If more than one of url, grab and grab_config options are non-empty
        then they processed in following order:
        * grab overwrite grab_config
        * grab_config overwrite url

        Args:
            :param name: name of the task. After successful network operation
                task's result will be passed to `task_<name>` method.
            :param url: URL of network document. Any task requires `url` or
                `grab` option to be specified.
            :param grab: configured `Grab` instance. You can use that option in
                case when `url` option is not enough. Do not forget to
                configure `url` option of `Grab` instance because in this case
                the `url` option of `Task` constructor will be overwritten
                with `grab.config['url']`.
            :param priority: - priority of the Task. Tasks with lower priority
                will be processed earlier. By default each new task is assigned
                with random priority from (80, 100) range.
            :param priority_is_custom: - internal flag which tells if that task
                priority was assigned manually or generated by spider according
                to priority generation rules.
            :param network_try_count: you'll probably will not need to use it.
                It is used internally to control how many times this task was
                restarted due to network errors. The `Spider` instance has
                `network_try_limit` option. When `network_try_count` attribute
                of the task exceeds the `network_try_limit` attribute then
                processing of the task is abandoned.
            :param task_try_count: the as `network_try_count` but it increased
                only then you use `clone` method. Also you can set it manually.
                It is useful if you want to restart the task after it was
                cancelled due to multiple network errors. As you might guessed
                there is `task_try_limit` option in `Spider` instance. Both
                options `network_try_count` and `network_try_limit` guarantee
                you that you'll not get infinite loop of restarting some task.
            :param disable_cache: if `True` disable cache subsystem.
                The document will be fetched from the Network and it will not
                be saved to cache.
            :param refresh_cache: if `True` the document will be fetched from
                the Network and saved to cache.
            :param valid_status: extra status codes which counts as valid
            :param use_proxylist: it means to use proxylist which was
                configured via `setup_proxylist` method of spider
            :param cache_timeout: maximum age (in seconds) of cache record to
                be valid
            :param delay: if specified tells the spider to schedule the task
                and execute    it after `delay` seconds
            :param raw: if `raw` is True then the network response is
                forwarding to the corresponding handler without any check of
                HTTP status code of network error, if `raw` is False (by
                default) then failed response is putting back to task queue or
                if tries limit is reached then the processing of this  request
                is finished.
            :param callback: if you pass some function in `callback` option
                then the network response will be passed to this callback and
                the usual 'task_*' handler will be ignored and no error will be
                raised if such 'task_*' handler does not exist.
            :param fallback_name: the name of method that is called when spider
                gives up to do the task (due to multiple network errors)
            :param error_callback: if request was failed then will execute
                'error_callback' function.

            Any non-standard named arguments passed to `Task` constructor will
            be saved as attributes of the object. You can get their values
            later as attributes or with `get` method which allows to use
            default value if attribute does not exist.
        """

        if name == 'generator':
            # The name "generator" is restricted because
            # `task_generator` handler could not be created because
            # this name is already used for special method which
            # generates new tasks
            raise SpiderMisuseError('Task name could not be "generator"')

        self.name = name

        if url is None and grab is None and grab_config is None:
            raise SpiderMisuseError('Either url, grab or grab_config argument '
                                    'of Task constructor should not be None')

        if url is not None and grab is not None:
            raise SpiderMisuseError('Options url and grab could not be used '
                                    'together')

        if url is not None and grab_config is not None:
            raise SpiderMisuseError('Options url and grab_config could not be '
                                    'used together')

        if grab is not None and grab_config is not None:
            raise SpiderMisuseError(
                'Options grab and grab_config could not be used together')

        if raw and error_callback is not None:
            raise SpiderMisuseError('Options raw and error_callback could '
                                    'not be used together')

        if grab:
            self.setup_grab_config(grab.dump_config())
        elif grab_config:
            self.setup_grab_config(grab_config)
        else:
            self.grab_config = None
            self.url = url

        self.process_delay_option(delay)

        self.fallback_name = fallback_name
        self.priority_is_custom = priority_is_custom
        self.priority = priority
        self.network_try_count = network_try_count
        self.task_try_count = task_try_count
        self.disable_cache = disable_cache
        self.refresh_cache = refresh_cache
        self.valid_status = valid_status
        self.use_proxylist = use_proxylist
        self.cache_timeout = cache_timeout
        self.raw = raw
        self.origin_task_generator = None
        self.callback = callback
        self.coroutines_stack = []
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get(self, key, default=None):
        """
        Return value of attribute or None if such attribute
        does not exist.
        """
        return getattr(self, key, default)

    def process_delay_option(self, delay):
        if delay:
            self.schedule_time = datetime.utcnow() + timedelta(seconds=delay)
            self.original_delay = delay
        else:
            self.schedule_time = None
            self.original_delay = None

    def setup_grab_config(self, grab_config):
        self.grab_config = copy_config(grab_config)
        self.url = grab_config['url']

    def clone(self, **kwargs):
        """
        Clone Task instance.

        Reset network_try_count, increase task_try_count.
        """

        # First, create exact copy of the current Task object
        attr_copy = self.__dict__.copy()
        if attr_copy.get('grab_config') is not None:
            del attr_copy['url']
        task = Task(**attr_copy)

        # Reset some task properties if they have not
        # been set explicitly in kwargs
        if 'network_try_count' not in kwargs:
            task.network_try_count = 0
        if 'task_try_count' not in kwargs:
            task.task_try_count = self.task_try_count + 1
        if 'refresh_cache' not in kwargs:
            task.refresh_cache = False
        if 'disable_cache' not in kwargs:
            task.disable_cache = False

        if kwargs.get('url') is not None and kwargs.get('grab') is not None:
            raise SpiderMisuseError('Options url and grab could not be '
                                    'used together')

        if (kwargs.get('url') is not None and
                kwargs.get('grab_config') is not None):
            raise SpiderMisuseError('Options url and grab_config could not '
                                    'be used together')

        if (kwargs.get('grab') is not None and
                kwargs.get('grab_config') is not None):
            raise SpiderMisuseError('Options grab and grab_config could not '
                                    'be used together')

        if kwargs.get('grab'):
            task.setup_grab_config(kwargs['grab'].dump_config())
            del kwargs['grab']
        elif kwargs.get('grab_config'):
            task.setup_grab_config(kwargs['grab_config'])
            del kwargs['grab_config']
        elif kwargs.get('url'):
            task.url = kwargs['url']
            if task.grab_config:
                task.grab_config['url'] = kwargs['url']
            del kwargs['url']

        for key, value in kwargs.items():
            setattr(task, key, value)

        # WTF?
        # The `Task` object can't has `delay` attribute
        # I think in next line the `process_delay_option` method
        # always gets None as input argument
        task.process_delay_option(task.get('delay', None))

        return task

    def __repr__(self):
        return '<Task: %s>' % self.url

    def __lt__(self, other):
        return self.priority < other.priority

    def __eq__(self, other):
        if not self.priority or not other.priority:
            return True
        else:
            return self.priority == other.priority

    def get_fallback_handler(self, spider):
        if self.fallback_name:
            return getattr(spider, self.fallback_name)
        elif self.name:
            fb_name = 'task_%s_fallback' % self.name
            if hasattr(spider, fb_name):
                return getattr(spider, fb_name)
        else:
            return None


def inline_task(f):
    def wrap(self, grab, task):
        origin_task_generator = f(self, grab, task)
        self.handler_for_inline_task(None, origin_task_generator)
    return wrap
