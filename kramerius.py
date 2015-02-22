#!/usr/bin/env python

"""
kramerius.py

Tool to download PDFs from Kramerius servers.

Usage:
    kramerius.py [--from=<page> --to=<page> --url=<url> --limit=<pages>] <id> <output>
    kramerius.py -h | --help
    kramerius.py -v | --version
    
Options:
    -h --help               show this screen.
    -v --version            show version.
    --from=<page>           page to start with.
    --to=<page>             page to end with.  
    --url=<url>             url to kramerius instance 
                            [default: http://kramerius.nkp.cz/kramerius/]
    --limit=<pages>         maximum pages in one downloaded PDF
                            [default: 20]
"""

import os

import re
import tempfile
import requests
from docopt import docopt
import sys
from lib import Unbuffered


__version__ = '0.0.1-alpha'
__author__ = 'Juda Kaleta <juda.kaleta@gmail.com>'
    

class Kramerius(object):
    DETAIL_URL_FORMAT = '{url}MShowMonograph.do?id={id}'
    """
    URL format to detail page of document.

    :type: str
    """

    DETAIL_RE_PAGE = r'value=[\'"]([0-9]+)[\'"][^>]+id=[\'"]{id}[\'"]'
    """
    Regex to parse value from item with given id.
    """

    DETAIL_RE_START = re.compile(
        DETAIL_RE_PAGE.format(id='ext_ontheflypdf_formStartInput')
    )
    """ :type: __Regex """
    DETAIL_RE_END = re.compile(
        DETAIL_RE_PAGE.format(id='ext_ontheflypdf_formEndInput')
    )
    """ :type: __Regex """

    DOWLOAD_URL_FORMAT = \
        '{url}ontheflypdf_MGetPdf?app=9&id={id}&start={start}&end={end}'
    """
    URL format to download page of document.

    :type: str
    """

    CMD_REMOVE_FIRST_PAGE = 'pdftk {input} cat 2-{end} output {output}'
    """
    Command to remove first page from PDF
    """

    PDF_UNITE_FORMAT = 'pdfunite {0}/*.pdf {1}'

    def __init__(self, id, output, start=None, end=None, url='', limit=20):
        """
        Initializes new Kramerius instance with given attributes.

        :param id: ID of document
        :type id: int

        :param output: Path to output file
        :type output: str

        :param start: Page to start with
        :type start: int

        :param end: Page to end with
        :type end: int

        :param url: Base url of Kramerius server
        :type url: str

        :param limit: Maximum count of pages downloaded in one pdf
        :type limit: int
        """
        self.id = id
        self.output = output
        self.start = start
        self.end = end
        self.url = url
        self.limit = limit

        self.directory = tempfile.mkdtemp()
        """
        Temporally directory to save downloaded PDFs

        :type: str
        """

    def run(self):
        """
        Method to run PDF downloading.
        """
        start, end = None, None

        if self.start is None or self.end is None:
            print 'Detecting start and end pages...\t',
            start, end = self.__detect_pages()
            print '[{0}-{1}]'.format(start, end)


        start = int(self.start or start)
        end = int(self.end or end)
        pages = end - start + 1

        print 'Downloading pages in range\t\t[{0}-{1}]'.format(start, end)

        for x in range((pages + limit - 1) // limit):
            tstart, tend = 1 + x * limit,  (x + 1) * limit
            tend = tend if tend < pages else pages
            print 'Downloading pages [{0}-{1}]\t\t'.format(tstart, tend),
            self.__download_pdf(tstart, tend)
            print '\t[DONE]'

        print 'Merging pdfs',
        self.__merge_pdfs()
        print '\t\t\t\t[DONE]'

    def __detect_pages(self):
        """
        Detect start and end pages from document detail page.

        :return: Start and end pages in tuple
        :rtype: tuple[int, int]
        """

        detail_url = self.DETAIL_URL_FORMAT.format(url=self.url, id=self.id)
        """ :type: str """
        content = requests.get(detail_url).content
        """ :type: unicode """

        m_start = self.DETAIL_RE_START.search(content)
        m_end = self.DETAIL_RE_END.search(content)

        return int(m_start.group(1)), int(m_end.group(1))

    def __download_pdf(self, start, end):
        """
        Download PDF in given range and save them into given directory.
        From every PDF document the first page is removed.

        :param start: Page to start with
        :type start: int

        :param end: Page to end with
        :type end: int

        :return: In case of no error function returns `True`.
        :rtype: bool
        """

        file_path = os.path.join(self.directory, str(start))
        download_url = self.DOWLOAD_URL_FORMAT.format(
            url=self.url,
            id=self.id,
            start=start,
            end=end
        )
        response = requests.get(download_url, stream=True)

        with open(file_path, 'w') as file:
            for i, block in enumerate(response.iter_content(2048)):
                if not block:
                    break
                if i % 250 == 0:
                    print '.',
                file.write(block)

        os.system(self.CMD_REMOVE_FIRST_PAGE.format(
            input=file_path,
            output=file_path + '.pdf',
            end=end - start + 2
        ))
        os.remove(file_path)
        return True

    def __merge_pdfs(self):
        """
        Merge all PDFs in directory into one.

        :return: Return code of command
        :rtype: int
        """
        cmd = self.PDF_UNITE_FORMAT.format(self.directory, self.output)
        return os.system(cmd)


if __name__ == '__main__':
    sys.stdout = Unbuffered(sys.stdout)
    arguments = docopt(__doc__, help=True, version=__version__)
    
    id = arguments['<id>']
    output = arguments['<output>']
    start, end = arguments['--from'], arguments['--to']
    url = arguments['--url']
    limit = int(arguments['--limit'])

    kramerius = Kramerius(
        id, output, url=url, start=start, end=end, limit=limit
    )
    kramerius.run()

