from grab.spider import Spider, Task
import logging

#from test.util import BaseGrabTestCase
from util import BaseGrabTestCase
from tools.error import InvalidUrlError

# That URLs breaks Grab's URL normalization process
# with error "label empty or too long"
INVALID_URL = 'http://13354&altProductId=6423589&productId=6423589'\
              '&altProductStoreId=13713&catalogId=10001'\
              '&categoryId=28678&productStoreId=13713'\
              'http://www.textbooksnow.com/webapp/wcs/stores'\
              '/servlet/ProductDisplay?langId=-1&storeId='


class SpiderErrorTestCase(BaseGrabTestCase):
    def setUp(self):
        self.server.reset()
    """
    def test_generator_with_invalid_url(self):

        class SomeSpider(Spider):
            def task_generator(self):
                yield Task('page', url=INVALID_URL)

        from grab.spider.base import logger_verbose
        logger_verbose.setLevel(logging.DEBUG)
        bot = SomeSpider()
        bot.run()

    def test_redirect_with_invalid_url(self):

        server = self.server

        class SomeSpider(Spider):
            def task_generator(self):
                self.done_counter = 0
                yield Task('page', url=server.get_url())

            def task_page(self, grab, task):
                pass

        # from grab.spider.base import logger_verbose
        # logger_verbose.setLevel(logging.DEBUG)
        self.server.response_once['code'] = 301
        self.server.response_once['headers'] = [
            ('Location', INVALID_URL),
        ]
        bot = SomeSpider(network_try_limit=1)
        bot.run()
    """

    def test_call_fallback_method_exist(self):
        class GrabInvalidUrl(Exception): pass
        class SomeSpider(Spider):
            def prepare(self):
                self.fallback_called = False
                self.exception = None

            def error_callback(spider, task, ex):
                print('==========')
                print(type(ex))
                spider.fallback_called = True
                spider.exception = ex

            def task_generator(self):
                #yield Task('page', url=INVALID_URL, error_callback=SomeSpider.error_callback)
                yield Task('page', url=INVALID_URL)

            #def process_new_task(self, task):
            #    raise GrabInvalidUrl("SomeException")

            def fallback_method(self, task, exception):
                self.fallback_called = True
                self.exception = exception


        from grab.spider.base import logger_verbose
        logger_verbose.setLevel(logging.DEBUG)
        bot = SomeSpider()
        bot.run()
        self.assertEqual(bot.fallback_called, True)
        self.assertTrue(isinstance(bot.exception, InvalidUrlError))


import unittest
if __name__ == '__main__':
    unittest.main()