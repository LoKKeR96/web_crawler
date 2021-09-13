# web_crawler
 Python web crawler of internal domain links.
 
 This application crawls a single domain to scrape all of its internal URLs.
 It starts from the domain main page and goes through each sub page or internal
 URL to keep scraping for more links.
 
 When scraping is done it prints the links from each page on the domain to every
 other page on the same domain as a list of links in the format A => B
 
## JavaScript Rendering

 If the domain you want to scrape uses JavaScript to generate dynamic content you
 can enable the processing on JavaScript by changing the global variable in the script.
 
## Parallelism (Concurrency in this case)

 The requests are parallelised by using the following libraries: gevent, requests-future
 and requests_html.
 
 Gevent is used to process each sub page independently. Gevent greenlets are not actually
 running in parallel like multiple threads but they are simply running concurrently by what
 it could be time-sharing or some other form of CPU sharing.
 
 The requests-future library is used to produce asynchronous requests for HTML pages.
 
 The requests_html library is also used for the same purpose but it supports asynchronous
 JavaScript rendering.
 
 There is no reason to keep both libraries, I would personally leave requests_html as it
 offers more than requests-future but I have noticed they behave a bit differently when
 requesting HTML pages. It doesn't hurt at the moment to use them for both use cases where
 JavaScript is used or not used.
 
 I have added a sleep timer every before we make any new request with a random number of seconds
 wait. This is to avoid creating too many reuqests. I think this can be improved to be a bit more
 smart in the future.