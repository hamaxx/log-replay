import sys
import time
import re
import urllib2
import numpy
import argparse

from Queue import Queue, Empty
from threading import Thread

LOG_LINE_REGEX = r'([0-9\.]+)\s-\s-\s\[.*?\]\s"GET\s(.*?)\sHTTP.*?"\s[0-9]+\s[0-9]+\s".*?"\s"(.*?)"'

class LogParser(object):

	QUEUE_SIZE_MAX = 1000

	def __init__(self, log_queue, log_file, limit):
		self.log_file = log_file
		self.queue = log_queue

		self.log_regex = re.compile(LOG_LINE_REGEX)

		self.limit = limit

		self.queued = 0

	def _get_parsed_line(self, line):
		m = self.log_regex.match(line)
		if not m:
			return None
		return m.groups()

	def _parse_next_batch(self):
		lines = self.log_file.readlines(1000000)

		if not lines:
			return False

		for line in lines:
			if self.limit > 0 and self.queued >= self.limit:
				return False

			while self.queue.qsize() > self.QUEUE_SIZE_MAX:
				time.sleep(0.1)

			parsed_line = self._get_parsed_line(line)
			if parsed_line:
				self.queue.put(parsed_line)
				self.queued += 1
		return True

	def _parser_job(self):
		while self._parse_next_batch(): pass

	def start(self):
		self.parser_job = Thread(target=self._parser_job)
		self.parser_job.start()

		wait_until = max(min(self.limit, self.QUEUE_SIZE_MAX / 2), 1)

		while self.queue.qsize() < wait_until:
			time.sleep(0.1)

	def stop(self):
		self.parser_job.join()


class RequestWorker(object):

	def __init__(self, log_queue, address, timeout, limit, workers):
		self.address = address
		self.timeout = timeout

		self.queue = log_queue
		self.limit = limit
		self.workers = workers

		self.print_on = max(int(limit / 10), 1000)

		self.results = {
			'total': 0,
			'error': 0,
			'ok': 0,
		}
		self.times = []

	def _print_progress(self):
		if self.results['total'] % self.print_on == 0:
			time_total = time.time() - self.t0
			print 'done', self.results['total'], '/', self.limit if self.limit > 0 else '?', '|', int(round(self.results['ok'] / time_total)), 'per sec'

	def _make_request(self):
		try:
			ip, path, user_agent = self.queue.get(False)
		except Empty:
			return False

		url = self.address + path

		try:
			tr0 = time.time()

			request = urllib2.Request(url, headers={"X-RealIP": ip, "User-Agent": user_agent})
			response = urllib2.urlopen(request, timeout=self.timeout)

			if response.getcode() >= 400:
				raise Exception("Response code error %s" % response.getcode())

			response.read()

			self.times.append(time.time() - tr0)

			self.results['ok'] += 1
		except Exception, e:
			print e
			self.results['error'] += 1

		self.results['total'] += 1

		self._print_progress()

		return True

	def _log_consumer_job(self):
		while self._make_request(): pass

	def print_report(self):
		#TODO: rewrite this method
		print

		print 'requests %s' % self.results['total']
		print 'ok       %s' % self.results['ok']
		print 'error    %s' % self.results['error']
		print

		print 'Total time: %s sec' % round(self.time_total, 2)
		print 'Requests per second: %s' % round(self.results['ok'] / self.time_total)
		print

		def get_ms(f):
			return round(f, 4) * 1000

		print 'Response times:'
		print 'mean:\t%sms' % get_ms(numpy.mean(self.times))

		ts = sorted(self.times)
		tlen = len(self.times)
		for p in xrange(10, 100, 10):
			c = float(p) / 100
			print '%d%%\t%sms' % (c * 100, get_ms(ts[int(tlen * c)]))
		print '100%%\t%sms' % get_ms(ts[-1])

	def start(self):
		self.jobs = []
		for i in xrange(self.workers):
			co = Thread(target=self._log_consumer_job)
			self.jobs.append(co)
			co.start()

		self.t0 = time.time()

	def stop(self):
		for co in self.jobs:
			co.join()

		self.time_total = time.time() - self.t0

def parse_args():
	parser = argparse.ArgumentParser(description='Replay HTTP Benchmark.')

	parser.add_argument('-a', '--address', type=str, help='HTTP server address', required=True)
	parser.add_argument('-f', '--file', type=str, help='Log file location', required=True)
	parser.add_argument('-c', '--concurrency', type=int, default=1, help='Number of concurrent requests')
	parser.add_argument('-r', '--requests', type=int, default=-1, help='Number of requests')
	parser.add_argument('-t', '--timeout', type=int, default=1, help='Request timeout in seconds')

	return parser.parse_args(sys.argv[1:])

def run_benchmark(options):
	log_queue = Queue()

	log_file = open(options['file'], 'r')

	log_parser = LogParser(log_queue, log_file, options['requests'])
	request_worker = RequestWorker(log_queue, options['address'], options['timeout'],
			options['requests'], options['concurrency'])

	log_parser.start()

	request_worker.start()
	request_worker.stop()

	log_parser.stop()

	request_worker.print_report()


if __name__ == '__main__':
	options = parse_args()
	run_benchmark(options.__dict__)
