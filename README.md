Benchmark HTTP server by replaying logs
===

Very simple and straightforward script for messuring http server capabilities by replaying log files.

Usage:
---
	usage: replay.py [-h] -a ADDRESS -f FILE -r REQUESTS [-c CONCURRENCY]
					 [-t TIMEOUT]

	arguments:
	  -h, --help            show this help message and exit
	  -a ADDRESS, --address ADDRESS
							HTTP server address
	  -f FILE, --file FILE  Log file location
	  -r REQUESTS, --requests REQUESTS
							Number of requests
	  -c CONCURRENCY, --concurrency CONCURRENCY
							Number of concurrent requests
	  -t TIMEOUT, --timeout TIMEOUT
							Request timeout in seconds

	example:
		python replay.py -a http://localhost:5000 -f access.log -r 10000 -c 4

Report example:
---
	requests 10000
	ok       10000
	error    0

	Total time: 33.95 sec
	Requests per second: 295.0

	Response times:
	mean:	13.5ms
	10%	8.7ms
	20%	9.4ms
	30%	10.0ms
	40%	10.7ms
	50%	11.5ms
	60%	12.5ms
	70%	13.8ms
	80%	15.9ms
	90%	19.3ms
	100%	619.5ms

Log file format:
---
	127.0.0.1 - - [22/Feb/2013:20:15:58 +0000] "GET /path/?parameter=nice HTTP/1.1" 200 26 "http://example.com/referrer" "User Agent String"

Known issues:
---
	Supports only GET requests.
