# test_codecs.py from CPython 2.7, modified for Jython
from test import support
import unittest
import codecs
import locale
import sys, io
if not support.is_jython:
    import _testcapi

class Queue(object):
    """
    queue: write bytes at one end, read bytes from the other end
    """
    def __init__(self):
        self._buffer = ""

    def write(self, chars):
        self._buffer += chars

    def read(self, size=-1):
        if size<0:
            s = self._buffer
            self._buffer = ""
            return s
        else:
            s = self._buffer[:size]
            self._buffer = self._buffer[size:]
            return s

class ReadTest(unittest.TestCase):
    def check_partial(self, input, partialresults):
        # get a StreamReader for the encoding and feed the bytestring version
        # of input to the reader byte by byte. Read everything available from
        # the StreamReader and check that the results equal the appropriate
        # entries from partialresults.
        q = Queue()
        r = codecs.getreader(self.encoding)(q)
        result = ""
        for (c, partialresult) in zip(input.encode(self.encoding), partialresults):
            q.write(c)
            result += r.read()
            self.assertEqual(result, partialresult)
        # check that there's nothing left in the buffers
        self.assertEqual(r.read(), "")
        self.assertEqual(r.bytebuffer, "")
        self.assertEqual(r.charbuffer, "")

        # do the check again, this time using a incremental decoder
        d = codecs.getincrementaldecoder(self.encoding)()
        result = ""
        for (c, partialresult) in zip(input.encode(self.encoding), partialresults):
            result += d.decode(c)
            self.assertEqual(result, partialresult)
        # check that there's nothing left in the buffers
        self.assertEqual(d.decode("", True), "")
        self.assertEqual(d.buffer, "")

        # Check whether the reset method works properly
        d.reset()
        result = ""
        for (c, partialresult) in zip(input.encode(self.encoding), partialresults):
            result += d.decode(c)
            self.assertEqual(result, partialresult)
        # check that there's nothing left in the buffers
        self.assertEqual(d.decode("", True), "")
        self.assertEqual(d.buffer, "")

        # check iterdecode()
        encoded = input.encode(self.encoding)
        self.assertEqual(
            input,
            "".join(codecs.iterdecode(encoded, self.encoding))
        )

    def test_readline(self):
        def getreader(input):
            stream = io.StringIO(input.encode(self.encoding))
            return codecs.getreader(self.encoding)(stream)

        def readalllines(input, keepends=True, size=None):
            reader = getreader(input)
            lines = []
            while True:
                line = reader.readline(size=size, keepends=keepends)
                if not line:
                    break
                lines.append(line)
            return "|".join(lines)

        s = "foo\nbar\r\nbaz\rspam\u2028eggs"
        sexpected = "foo\n|bar\r\n|baz\r|spam\u2028|eggs"
        sexpectednoends = "foo|bar|baz|spam|eggs"
        self.assertEqual(readalllines(s, True), sexpected)
        self.assertEqual(readalllines(s, False), sexpectednoends)
        self.assertEqual(readalllines(s, True, 10), sexpected)
        self.assertEqual(readalllines(s, False, 10), sexpectednoends)

        # Test long lines (multiple calls to read() in readline())
        vw = []
        vwo = []
        for (i, lineend) in enumerate("\n \r\n \r \u2028".split()):
            vw.append((i*200)*"\3042" + lineend)
            vwo.append((i*200)*"\3042")
        self.assertEqual(readalllines("".join(vw), True), "".join(vw))
        self.assertEqual(readalllines("".join(vw), False), "".join(vwo))

        # Test lines where the first read might end with \r, so the
        # reader has to look ahead whether this is a lone \r or a \r\n
        for size in range(80):
            for lineend in "\n \r\n \r \u2028".split():
                s = 10*(size*"a" + lineend + "xxx\n")
                reader = getreader(s)
                for i in range(10):
                    self.assertEqual(
                        reader.readline(keepends=True),
                        size*"a" + lineend,
                    )
                reader = getreader(s)
                for i in range(10):
                    self.assertEqual(
                        reader.readline(keepends=False),
                        size*"a",
                    )

    def test_bug1175396(self):
        s = [
            '<%!--===================================================\r\n',
            '    BLOG index page: show recent articles,\r\n',
            '    today\'s articles, or articles of a specific date.\r\n',
            '========================================================--%>\r\n',
            '<%@inputencoding="ISO-8859-1"%>\r\n',
            '<%@pagetemplate=TEMPLATE.y%>\r\n',
            '<%@import=import frog.util, frog%>\r\n',
            '<%@import=import frog.objects%>\r\n',
            '<%@import=from frog.storageerrors import StorageError%>\r\n',
            '<%\r\n',
            '\r\n',
            'import logging\r\n',
            'log=logging.getLogger("Snakelets.logger")\r\n',
            '\r\n',
            '\r\n',
            'user=self.SessionCtx.user\r\n',
            'storageEngine=self.SessionCtx.storageEngine\r\n',
            '\r\n',
            '\r\n',
            'def readArticlesFromDate(date, count=None):\r\n',
            '    entryids=storageEngine.listBlogEntries(date)\r\n',
            '    entryids.reverse() # descending\r\n',
            '    if count:\r\n',
            '        entryids=entryids[:count]\r\n',
            '    try:\r\n',
            '        return [ frog.objects.BlogEntry.load(storageEngine, date, Id) for Id in entryids ]\r\n',
            '    except StorageError,x:\r\n',
            '        log.error("Error loading articles: "+str(x))\r\n',
            '        self.abort("cannot load articles")\r\n',
            '\r\n',
            'showdate=None\r\n',
            '\r\n',
            'arg=self.Request.getArg()\r\n',
            'if arg=="today":\r\n',
            '    #-------------------- TODAY\'S ARTICLES\r\n',
            '    self.write("<h2>Today\'s articles</h2>")\r\n',
            '    showdate = frog.util.isodatestr() \r\n',
            '    entries = readArticlesFromDate(showdate)\r\n',
            'elif arg=="active":\r\n',
            '    #-------------------- ACTIVE ARTICLES redirect\r\n',
            '    self.Yredirect("active.y")\r\n',
            'elif arg=="login":\r\n',
            '    #-------------------- LOGIN PAGE redirect\r\n',
            '    self.Yredirect("login.y")\r\n',
            'elif arg=="date":\r\n',
            '    #-------------------- ARTICLES OF A SPECIFIC DATE\r\n',
            '    showdate = self.Request.getParameter("date")\r\n',
            '    self.write("<h2>Articles written on %s</h2>"% frog.util.mediumdatestr(showdate))\r\n',
            '    entries = readArticlesFromDate(showdate)\r\n',
            'else:\r\n',
            '    #-------------------- RECENT ARTICLES\r\n',
            '    self.write("<h2>Recent articles</h2>")\r\n',
            '    dates=storageEngine.listBlogEntryDates()\r\n',
            '    if dates:\r\n',
            '        entries=[]\r\n',
            '        SHOWAMOUNT=10\r\n',
            '        for showdate in dates:\r\n',
            '            entries.extend( readArticlesFromDate(showdate, SHOWAMOUNT-len(entries)) )\r\n',
            '            if len(entries)>=SHOWAMOUNT:\r\n',
            '                break\r\n',
            '                \r\n',
        ]
        stream = io.StringIO("".join(s).encode(self.encoding))
        reader = codecs.getreader(self.encoding)(stream)
        for (i, line) in enumerate(reader):
            self.assertEqual(line, s[i])

    def test_readlinequeue(self):
        q = Queue()
        writer = codecs.getwriter(self.encoding)(q)
        reader = codecs.getreader(self.encoding)(q)

        # No lineends
        writer.write("foo\r")
        self.assertEqual(reader.readline(keepends=False), "foo")
        writer.write("\nbar\r")
        self.assertEqual(reader.readline(keepends=False), "")
        self.assertEqual(reader.readline(keepends=False), "bar")
        writer.write("baz")
        self.assertEqual(reader.readline(keepends=False), "baz")
        self.assertEqual(reader.readline(keepends=False), "")

        # Lineends
        writer.write("foo\r")
        self.assertEqual(reader.readline(keepends=True), "foo\r")
        writer.write("\nbar\r")
        self.assertEqual(reader.readline(keepends=True), "\n")
        self.assertEqual(reader.readline(keepends=True), "bar\r")
        writer.write("baz")
        self.assertEqual(reader.readline(keepends=True), "baz")
        self.assertEqual(reader.readline(keepends=True), "")
        writer.write("foo\r\n")
        self.assertEqual(reader.readline(keepends=True), "foo\r\n")

    def test_bug1098990_a(self):
        s1 = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy\r\n"
        s2 = "offending line: ladfj askldfj klasdj fskla dfzaskdj fasklfj laskd fjasklfzzzzaa%whereisthis!!!\r\n"
        s3 = "next line.\r\n"

        s = (s1+s2+s3).encode(self.encoding)
        stream = io.StringIO(s)
        reader = codecs.getreader(self.encoding)(stream)
        self.assertEqual(reader.readline(), s1)
        self.assertEqual(reader.readline(), s2)
        self.assertEqual(reader.readline(), s3)
        self.assertEqual(reader.readline(), "")

    def test_bug1098990_b(self):
        s1 = "aaaaaaaaaaaaaaaaaaaaaaaa\r\n"
        s2 = "bbbbbbbbbbbbbbbbbbbbbbbb\r\n"
        s3 = "stillokay:bbbbxx\r\n"
        s4 = "broken!!!!badbad\r\n"
        s5 = "againokay.\r\n"

        s = (s1+s2+s3+s4+s5).encode(self.encoding)
        stream = io.StringIO(s)
        reader = codecs.getreader(self.encoding)(stream)
        self.assertEqual(reader.readline(), s1)
        self.assertEqual(reader.readline(), s2)
        self.assertEqual(reader.readline(), s3)
        self.assertEqual(reader.readline(), s4)
        self.assertEqual(reader.readline(), s5)
        self.assertEqual(reader.readline(), "")

class UTF32Test(ReadTest):
    encoding = "utf-32"

    spamle = ('\xff\xfe\x00\x00'
              's\x00\x00\x00p\x00\x00\x00a\x00\x00\x00m\x00\x00\x00'
              's\x00\x00\x00p\x00\x00\x00a\x00\x00\x00m\x00\x00\x00')
    spambe = ('\x00\x00\xfe\xff'
              '\x00\x00\x00s\x00\x00\x00p\x00\x00\x00a\x00\x00\x00m'
              '\x00\x00\x00s\x00\x00\x00p\x00\x00\x00a\x00\x00\x00m')

    def test_only_one_bom(self):
        _, _, reader, writer = codecs.lookup(self.encoding)
        # encode some stream
        s = io.StringIO()
        f = writer(s)
        f.write("spam")
        f.write("spam")
        d = s.getvalue()
        # check whether there is exactly one BOM in it
        self.assertTrue(d == self.spamle or d == self.spambe)
        # try to read it back
        s = io.StringIO(d)
        f = reader(s)
        self.assertEqual(f.read(), "spamspam")

    def test_badbom(self):
        s = io.StringIO(4*"\xff")
        f = codecs.getreader(self.encoding)(s)
        self.assertRaises(UnicodeError, f.read)

        s = io.StringIO(8*"\xff")
        f = codecs.getreader(self.encoding)(s)
        self.assertRaises(UnicodeError, f.read)

    def test_partial(self):
        self.check_partial(
            "\x00\xff\u0100\uffff",
            [
                "", # first byte of BOM read
                "", # second byte of BOM read
                "", # third byte of BOM read
                "", # fourth byte of BOM read => byteorder known
                "",
                "",
                "",
                "\x00",
                "\x00",
                "\x00",
                "\x00",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff\u0100",
                "\x00\xff\u0100",
                "\x00\xff\u0100",
                "\x00\xff\u0100",
                "\x00\xff\u0100\uffff",
            ]
        )

    def test_handlers(self):
        self.assertEqual(('\ufffd', 1),
                         codecs.utf_32_decode('\x01', 'replace', True))
        self.assertEqual(('', 1),
                         codecs.utf_32_decode('\x01', 'ignore', True))

    def test_errors(self):
        self.assertRaises(UnicodeDecodeError, codecs.utf_32_decode,
                          "\xff", "strict", True)

    def test_issue8941(self):
        # Issue #8941: insufficient result allocation when decoding into
        # surrogate pairs on UCS-2 builds.
        encoded_le = '\xff\xfe\x00\x00' + '\x00\x00\x01\x00' * 1024
        self.assertEqual('\U00010000' * 1024,
                         codecs.utf_32_decode(encoded_le)[0])
        encoded_be = '\x00\x00\xfe\xff' + '\x00\x01\x00\x00' * 1024
        self.assertEqual('\U00010000' * 1024,
                         codecs.utf_32_decode(encoded_be)[0])

class UTF32LETest(ReadTest):
    encoding = "utf-32-le"

    def test_partial(self):
        self.check_partial(
            "\x00\xff\u0100\uffff",
            [
                "",
                "",
                "",
                "\x00",
                "\x00",
                "\x00",
                "\x00",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff\u0100",
                "\x00\xff\u0100",
                "\x00\xff\u0100",
                "\x00\xff\u0100",
                "\x00\xff\u0100\uffff",
            ]
        )

    def test_simple(self):
        self.assertEqual("\U00010203".encode(self.encoding), "\x03\x02\x01\x00")

    def test_errors(self):
        self.assertRaises(UnicodeDecodeError, codecs.utf_32_le_decode,
                          "\xff", "strict", True)

    def test_issue8941(self):
        # Issue #8941: insufficient result allocation when decoding into
        # surrogate pairs on UCS-2 builds.
        encoded = '\x00\x00\x01\x00' * 1024
        self.assertEqual('\U00010000' * 1024,
                         codecs.utf_32_le_decode(encoded)[0])

class UTF32BETest(ReadTest):
    encoding = "utf-32-be"

    def test_partial(self):
        self.check_partial(
            "\x00\xff\u0100\uffff",
            [
                "",
                "",
                "",
                "\x00",
                "\x00",
                "\x00",
                "\x00",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff\u0100",
                "\x00\xff\u0100",
                "\x00\xff\u0100",
                "\x00\xff\u0100",
                "\x00\xff\u0100\uffff",
            ]
        )

    def test_simple(self):
        self.assertEqual("\U00010203".encode(self.encoding), "\x00\x01\x02\x03")

    def test_errors(self):
        self.assertRaises(UnicodeDecodeError, codecs.utf_32_be_decode,
                          "\xff", "strict", True)

    def test_issue8941(self):
        # Issue #8941: insufficient result allocation when decoding into
        # surrogate pairs on UCS-2 builds.
        encoded = '\x00\x01\x00\x00' * 1024
        self.assertEqual('\U00010000' * 1024,
                         codecs.utf_32_be_decode(encoded)[0])


class UTF16Test(ReadTest):
    encoding = "utf-16"

    spamle = '\xff\xfes\x00p\x00a\x00m\x00s\x00p\x00a\x00m\x00'
    spambe = '\xfe\xff\x00s\x00p\x00a\x00m\x00s\x00p\x00a\x00m'

    def test_only_one_bom(self):
        _, _, reader, writer = codecs.lookup(self.encoding)
        # encode some stream
        s = io.StringIO()
        f = writer(s)
        f.write("spam")
        f.write("spam")
        d = s.getvalue()
        # check whether there is exactly one BOM in it
        self.assertTrue(d == self.spamle or d == self.spambe)
        # try to read it back
        s = io.StringIO(d)
        f = reader(s)
        self.assertEqual(f.read(), "spamspam")

    def test_badbom(self):
        s = io.StringIO("\xff\xff")
        f = codecs.getreader(self.encoding)(s)
        self.assertRaises(UnicodeError, f.read)

        s = io.StringIO("\xff\xff\xff\xff")
        f = codecs.getreader(self.encoding)(s)
        self.assertRaises(UnicodeError, f.read)

    def test_partial(self):
        self.check_partial(
            "\x00\xff\u0100\uffff",
            [
                "", # first byte of BOM read
                "", # second byte of BOM read => byteorder known
                "",
                "\x00",
                "\x00",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff\u0100",
                "\x00\xff\u0100",
                "\x00\xff\u0100\uffff",
            ]
        )

    def test_handlers(self):
        self.assertEqual(('\ufffd', 1),
                         codecs.utf_16_decode('\x01', 'replace', True))
        self.assertEqual(('', 1),
                         codecs.utf_16_decode('\x01', 'ignore', True))

    def test_errors(self):
        self.assertRaises(UnicodeDecodeError, codecs.utf_16_decode, "\xff", "strict", True)

    def test_bug691291(self):
        # Files are always opened in binary mode, even if no binary mode was
        # specified.  This means that no automatic conversion of '\n' is done
        # on reading and writing.
        s1 = 'Hello\r\nworld\r\n'

        s = s1.encode(self.encoding)
        self.addCleanup(support.unlink, support.TESTFN)
        with open(support.TESTFN, 'wb') as fp:
            fp.write(s)
        with codecs.open(support.TESTFN, 'U', encoding=self.encoding) as reader:
            self.assertEqual(reader.read(), s1)

class UTF16LETest(ReadTest):
    encoding = "utf-16-le"

    def test_partial(self):
        self.check_partial(
            "\x00\xff\u0100\uffff",
            [
                "",
                "\x00",
                "\x00",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff\u0100",
                "\x00\xff\u0100",
                "\x00\xff\u0100\uffff",
            ]
        )

    def test_errors(self):
        self.assertRaises(UnicodeDecodeError, codecs.utf_16_le_decode, "\xff", "strict", True)

class UTF16BETest(ReadTest):
    encoding = "utf-16-be"

    def test_partial(self):
        self.check_partial(
            "\x00\xff\u0100\uffff",
            [
                "",
                "\x00",
                "\x00",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff\u0100",
                "\x00\xff\u0100",
                "\x00\xff\u0100\uffff",
            ]
        )

    def test_errors(self):
        self.assertRaises(UnicodeDecodeError, codecs.utf_16_be_decode, "\xff", "strict", True)

class UTF8Test(ReadTest):
    encoding = "utf-8"

    def test_partial(self):
        self.check_partial(
            "\x00\xff\u07ff\u0800\uffff",
            [
                "\x00",
                "\x00",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff\u07ff",
                "\x00\xff\u07ff",
                "\x00\xff\u07ff",
                "\x00\xff\u07ff\u0800",
                "\x00\xff\u07ff\u0800",
                "\x00\xff\u07ff\u0800",
                "\x00\xff\u07ff\u0800\uffff",
            ]
        )

class UTF7Test(ReadTest):
    encoding = "utf-7"

    def test_partial(self):
        self.check_partial(
            "a+-b",
            [
                "a",
                "a",
                "a+",
                "a+-",
                "a+-b",
            ]
        )

    # Jython extra (test supplementary characters)
    @unittest.skipIf(not support.is_jython, "Jython supports surrogate pairs")
    def test_partial_supp(self):
        # Check the encoding is what we think it is
        ustr = "x\U00023456.\u0177\U00023456\u017az"
        bstr = b'x+2E3cVg.+AXfYTdxWAXo-z'
        self.assertEqual(ustr.encode(self.encoding), bstr)

        self.check_partial(
            ustr,
            [
                "x",
                "x",   # '+' added: begins Base64
                "x",
                "x",
                "x",
                "x",
                "x",
                "x",
                "x\U00023456.",    # '.' added: ends Base64
                "x\U00023456.",    # '+' added: begins Base64
                "x\U00023456.",
                "x\U00023456.",
                "x\U00023456.",
                "x\U00023456.",
                "x\U00023456.",
                "x\U00023456.",
                "x\U00023456.",
                "x\U00023456.",
                "x\U00023456.",
                "x\U00023456.",
                "x\U00023456.",
                "x\U00023456.\u0177\U00023456\u017a",  # '-' added: ends Base64
                "x\U00023456.\u0177\U00023456\u017az",
            ]
        )

class UTF16ExTest(unittest.TestCase):

    def test_errors(self):
        self.assertRaises(UnicodeDecodeError, codecs.utf_16_ex_decode, "\xff", "strict", 0, True)

    def test_bad_args(self):
        self.assertRaises(TypeError, codecs.utf_16_ex_decode)

@unittest.skipIf(support.is_jython, "Jython has no _codecs.readbuffer_encode method")
class ReadBufferTest(unittest.TestCase):

    def test_array(self):
        import array
        self.assertEqual(
            codecs.readbuffer_encode(array.array("c", "spam")),
            ("spam", 4)
        )

    def test_empty(self):
        self.assertEqual(codecs.readbuffer_encode(""), ("", 0))

    def test_bad_args(self):
        self.assertRaises(TypeError, codecs.readbuffer_encode)
        self.assertRaises(TypeError, codecs.readbuffer_encode, 42)

@unittest.skipIf(support.is_jython, "Jython has no _codecs.charbuffer_encode method")
class CharBufferTest(unittest.TestCase):

    def test_string(self):
        self.assertEqual(codecs.charbuffer_encode("spam"), ("spam", 4))

    def test_empty(self):
        self.assertEqual(codecs.charbuffer_encode(""), ("", 0))

    def test_bad_args(self):
        self.assertRaises(TypeError, codecs.charbuffer_encode)
        self.assertRaises(TypeError, codecs.charbuffer_encode, 42)

class UTF8SigTest(ReadTest):
    encoding = "utf-8-sig"

    def test_partial(self):
        self.check_partial(
            "\ufeff\x00\xff\u07ff\u0800\uffff",
            [
                "",
                "",
                "", # First BOM has been read and skipped
                "",
                "",
                "\ufeff", # Second BOM has been read and emitted
                "\ufeff\x00", # "\x00" read and emitted
                "\ufeff\x00", # First byte of encoded u"\xff" read
                "\ufeff\x00\xff", # Second byte of encoded u"\xff" read
                "\ufeff\x00\xff", # First byte of encoded u"\u07ff" read
                "\ufeff\x00\xff\u07ff", # Second byte of encoded u"\u07ff" read
                "\ufeff\x00\xff\u07ff",
                "\ufeff\x00\xff\u07ff",
                "\ufeff\x00\xff\u07ff\u0800",
                "\ufeff\x00\xff\u07ff\u0800",
                "\ufeff\x00\xff\u07ff\u0800",
                "\ufeff\x00\xff\u07ff\u0800\uffff",
            ]
        )

    def test_bug1601501(self):
        # SF bug #1601501: check that the codec works with a buffer
        str("\xef\xbb\xbf", "utf-8-sig")

    def test_bom(self):
        d = codecs.getincrementaldecoder("utf-8-sig")()
        s = "spam"
        self.assertEqual(d.decode(s.encode("utf-8-sig")), s)

    def test_stream_bom(self):
        unistring = "ABC\u00A1\u2200XYZ"
        bytestring = codecs.BOM_UTF8 + "ABC\xC2\xA1\xE2\x88\x80XYZ"

        reader = codecs.getreader("utf-8-sig")
        for sizehint in [None] + list(range(1, 11)) + \
                        [64, 128, 256, 512, 1024]:
            istream = reader(io.StringIO(bytestring))
            ostream = io.StringIO()
            while True:
                if sizehint is not None:
                    data = istream.read(sizehint)
                else:
                    data = istream.read()

                if not data:
                    break
                ostream.write(data)

            got = ostream.getvalue()
            self.assertEqual(got, unistring)

    def test_stream_bare(self):
        unistring = "ABC\u00A1\u2200XYZ"
        bytestring = "ABC\xC2\xA1\xE2\x88\x80XYZ"

        reader = codecs.getreader("utf-8-sig")
        for sizehint in [None] + list(range(1, 11)) + \
                        [64, 128, 256, 512, 1024]:
            istream = reader(io.StringIO(bytestring))
            ostream = io.StringIO()
            while True:
                if sizehint is not None:
                    data = istream.read(sizehint)
                else:
                    data = istream.read()

                if not data:
                    break
                ostream.write(data)

            got = ostream.getvalue()
            self.assertEqual(got, unistring)

class EscapeDecodeTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(codecs.escape_decode(""), ("", 0))

class RecodingTest(unittest.TestCase):
    def test_recoding(self):
        f = io.StringIO()
        f2 = codecs.EncodedFile(f, "unicode_internal", "utf-8")
        # f2.write(u"a")
        # Must be bytes in Jython (and probably should have been in CPython)
        f2.write(b"\x00\x00\x00\x61")
        f2.close()
        # Python used to crash on this at exit because of a refcount
        # bug in _codecsmodule.c

# From RFC 3492
punycode_testcases = [
    # A Arabic (Egyptian):
    ("\u0644\u064A\u0647\u0645\u0627\u0628\u062A\u0643\u0644"
     "\u0645\u0648\u0634\u0639\u0631\u0628\u064A\u061F",
     "egbpdaj6bu4bxfgehfvwxn"),
    # B Chinese (simplified):
    ("\u4ED6\u4EEC\u4E3A\u4EC0\u4E48\u4E0D\u8BF4\u4E2D\u6587",
     "ihqwcrb4cv8a8dqg056pqjye"),
    # C Chinese (traditional):
    ("\u4ED6\u5011\u7232\u4EC0\u9EBD\u4E0D\u8AAA\u4E2D\u6587",
     "ihqwctvzc91f659drss3x8bo0yb"),
    # D Czech: Pro<ccaron>prost<ecaron>nemluv<iacute><ccaron>esky
    ("\u0050\u0072\u006F\u010D\u0070\u0072\u006F\u0073\u0074"
     "\u011B\u006E\u0065\u006D\u006C\u0075\u0076\u00ED\u010D"
     "\u0065\u0073\u006B\u0079",
     "Proprostnemluvesky-uyb24dma41a"),
    # E Hebrew:
    ("\u05DC\u05DE\u05D4\u05D4\u05DD\u05E4\u05E9\u05D5\u05D8"
     "\u05DC\u05D0\u05DE\u05D3\u05D1\u05E8\u05D9\u05DD\u05E2"
     "\u05D1\u05E8\u05D9\u05EA",
     "4dbcagdahymbxekheh6e0a7fei0b"),
    # F Hindi (Devanagari):
    ("\u092F\u0939\u0932\u094B\u0917\u0939\u093F\u0928\u094D"
    "\u0926\u0940\u0915\u094D\u092F\u094B\u0902\u0928\u0939"
    "\u0940\u0902\u092C\u094B\u0932\u0938\u0915\u0924\u0947"
    "\u0939\u0948\u0902",
    "i1baa7eci9glrd9b2ae1bj0hfcgg6iyaf8o0a1dig0cd"),

    #(G) Japanese (kanji and hiragana):
    ("\u306A\u305C\u307F\u3093\u306A\u65E5\u672C\u8A9E\u3092"
    "\u8A71\u3057\u3066\u304F\u308C\u306A\u3044\u306E\u304B",
     "n8jok5ay5dzabd5bym9f0cm5685rrjetr6pdxa"),

    # (H) Korean (Hangul syllables):
    ("\uC138\uACC4\uC758\uBAA8\uB4E0\uC0AC\uB78C\uB4E4\uC774"
     "\uD55C\uAD6D\uC5B4\uB97C\uC774\uD574\uD55C\uB2E4\uBA74"
     "\uC5BC\uB9C8\uB098\uC88B\uC744\uAE4C",
     "989aomsvi5e83db1d2a355cv1e0vak1dwrv93d5xbh15a0dt30a5j"
     "psd879ccm6fea98c"),

    # (I) Russian (Cyrillic):
    ("\u043F\u043E\u0447\u0435\u043C\u0443\u0436\u0435\u043E"
     "\u043D\u0438\u043D\u0435\u0433\u043E\u0432\u043E\u0440"
     "\u044F\u0442\u043F\u043E\u0440\u0443\u0441\u0441\u043A"
     "\u0438",
     "b1abfaaepdrnnbgefbaDotcwatmq2g4l"),

    # (J) Spanish: Porqu<eacute>nopuedensimplementehablarenEspa<ntilde>ol
    ("\u0050\u006F\u0072\u0071\u0075\u00E9\u006E\u006F\u0070"
     "\u0075\u0065\u0064\u0065\u006E\u0073\u0069\u006D\u0070"
     "\u006C\u0065\u006D\u0065\u006E\u0074\u0065\u0068\u0061"
     "\u0062\u006C\u0061\u0072\u0065\u006E\u0045\u0073\u0070"
     "\u0061\u00F1\u006F\u006C",
     "PorqunopuedensimplementehablarenEspaol-fmd56a"),

    # (K) Vietnamese:
    #  T<adotbelow>isaoh<odotbelow>kh<ocirc>ngth<ecirchookabove>ch\
    #   <ihookabove>n<oacute>iti<ecircacute>ngVi<ecircdotbelow>t
    ("\u0054\u1EA1\u0069\u0073\u0061\u006F\u0068\u1ECD\u006B"
     "\u0068\u00F4\u006E\u0067\u0074\u0068\u1EC3\u0063\u0068"
     "\u1EC9\u006E\u00F3\u0069\u0074\u0069\u1EBF\u006E\u0067"
     "\u0056\u0069\u1EC7\u0074",
     "TisaohkhngthchnitingVit-kjcr8268qyxafd2f1b9g"),

    #(L) 3<nen>B<gumi><kinpachi><sensei>
    ("\u0033\u5E74\u0042\u7D44\u91D1\u516B\u5148\u751F",
     "3B-ww4c5e180e575a65lsy2b"),

    # (M) <amuro><namie>-with-SUPER-MONKEYS
    ("\u5B89\u5BA4\u5948\u7F8E\u6075\u002D\u0077\u0069\u0074"
     "\u0068\u002D\u0053\u0055\u0050\u0045\u0052\u002D\u004D"
     "\u004F\u004E\u004B\u0045\u0059\u0053",
     "-with-SUPER-MONKEYS-pc58ag80a8qai00g7n9n"),

    # (N) Hello-Another-Way-<sorezore><no><basho>
    ("\u0048\u0065\u006C\u006C\u006F\u002D\u0041\u006E\u006F"
     "\u0074\u0068\u0065\u0072\u002D\u0057\u0061\u0079\u002D"
     "\u305D\u308C\u305E\u308C\u306E\u5834\u6240",
     "Hello-Another-Way--fc4qua05auwb3674vfr0b"),

    # (O) <hitotsu><yane><no><shita>2
    ("\u3072\u3068\u3064\u5C4B\u6839\u306E\u4E0B\u0032",
     "2-u9tlzr9756bt3uc0v"),

    # (P) Maji<de>Koi<suru>5<byou><mae>
    ("\u004D\u0061\u006A\u0069\u3067\u004B\u006F\u0069\u3059"
     "\u308B\u0035\u79D2\u524D",
     "MajiKoi5-783gue6qz075azm5e"),

     # (Q) <pafii>de<runba>
    ("\u30D1\u30D5\u30A3\u30FC\u0064\u0065\u30EB\u30F3\u30D0",
     "de-jg4avhby1noc0d"),

    # (R) <sono><supiido><de>
    ("\u305D\u306E\u30B9\u30D4\u30FC\u30C9\u3067",
     "d9juau41awczczp"),

    # (S) -> $1.00 <-
    ("\u002D\u003E\u0020\u0024\u0031\u002E\u0030\u0030\u0020"
     "\u003C\u002D",
     "-> $1.00 <--")
    ]

for i in punycode_testcases:
    if len(i)!=2:
        print(repr(i))

class PunycodeTest(unittest.TestCase):
    def test_encode(self):
        for uni, puny in punycode_testcases:
            # Need to convert both strings to lower case, since
            # some of the extended encodings use upper case, but our
            # code produces only lower case. Converting just puny to
            # lower is also insufficient, since some of the input characters
            # are upper case.
            self.assertEqual(uni.encode("punycode").lower(), puny.lower())

    def test_decode(self):
        for uni, puny in punycode_testcases:
            self.assertEqual(uni, puny.decode("punycode"))

class UnicodeInternalTest(unittest.TestCase):
    def test_bug1251300(self):
        # Decoding with unicode_internal used to not correctly handle "code
        # points" above 0x10ffff on UCS-4 builds.
        if sys.maxunicode > 0xffff:
            ok = [
                ("\x00\x10\xff\xff", "\U0010ffff"),
                ("\x00\x00\x01\x01", "\U00000101"),
                ("", ""),
            ]
            not_ok = [
                "\x7f\xff\xff\xff",
                "\x80\x00\x00\x00",
                "\x81\x00\x00\x00",
                "\x00",
                "\x00\x00\x00\x00\x00",
            ]
            for internal, uni in ok:
                if sys.byteorder == "little":
                    internal = "".join(reversed(internal))
                self.assertEqual(uni, internal.decode("unicode_internal"))
            for internal in not_ok:
                if sys.byteorder == "little":
                    internal = "".join(reversed(internal))
                self.assertRaises(UnicodeDecodeError, internal.decode,
                    "unicode_internal")

    def test_decode_error_attributes(self):
        if sys.maxunicode > 0xffff:
            try:
                "\x00\x00\x00\x00\x00\x11\x11\x00".decode("unicode_internal")
            except UnicodeDecodeError as ex:
                if support.is_jython:
                    # Jython delegates internally to utf-32be and it shows here
                    self.assertEqual("utf-32", ex.encoding)
                else:
                    self.assertEqual("unicode_internal", ex.encoding)
                self.assertEqual("\x00\x00\x00\x00\x00\x11\x11\x00", ex.object)
                self.assertEqual(4, ex.start)
                self.assertEqual(8, ex.end)
            else:
                self.fail("UnicodeDecodeError not raised")

    def test_decode_callback(self):
        if sys.maxunicode > 0xffff:
            codecs.register_error("UnicodeInternalTest", codecs.ignore_errors)
            decoder = codecs.getdecoder("unicode_internal")
            ab = "ab".encode("unicode_internal")
            ignored = decoder("%s\x22\x22\x22\x22%s" % (ab[:4], ab[4:]),
                "UnicodeInternalTest")
            self.assertEqual(("ab", 12), ignored)

    def test_encode_length(self):
        # Issue 3739
        encoder = codecs.getencoder("unicode_internal")
        self.assertEqual(encoder("a")[1], 1)
        self.assertEqual(encoder("\xe9\u0142")[1], 2)

        encoder = codecs.getencoder("string-escape")
        self.assertEqual(encoder(r'\x00')[1], 4)

# From http://www.gnu.org/software/libidn/draft-josefsson-idn-test-vectors.html
nameprep_tests = [
    # 3.1 Map to nothing.
    ('foo\xc2\xad\xcd\x8f\xe1\xa0\x86\xe1\xa0\x8bbar'
     '\xe2\x80\x8b\xe2\x81\xa0baz\xef\xb8\x80\xef\xb8\x88\xef'
     '\xb8\x8f\xef\xbb\xbf',
     'foobarbaz'),
    # 3.2 Case folding ASCII U+0043 U+0041 U+0046 U+0045.
    ('CAFE',
     'cafe'),
    # 3.3 Case folding 8bit U+00DF (german sharp s).
    # The original test case is bogus; it says \xc3\xdf
    ('\xc3\x9f',
     'ss'),
    # 3.4 Case folding U+0130 (turkish capital I with dot).
    ('\xc4\xb0',
     'i\xcc\x87'),
    # 3.5 Case folding multibyte U+0143 U+037A.
    ('\xc5\x83\xcd\xba',
     '\xc5\x84 \xce\xb9'),
    # 3.6 Case folding U+2121 U+33C6 U+1D7BB.
    # XXX: skip this as it fails in UCS-2 mode
    #('\xe2\x84\xa1\xe3\x8f\x86\xf0\x9d\x9e\xbb',
    # 'telc\xe2\x88\x95kg\xcf\x83'),
    (None, None),
    # 3.7 Normalization of U+006a U+030c U+00A0 U+00AA.
    ('j\xcc\x8c\xc2\xa0\xc2\xaa',
     '\xc7\xb0 a'),
    # 3.8 Case folding U+1FB7 and normalization.
    ('\xe1\xbe\xb7',
     '\xe1\xbe\xb6\xce\xb9'),
    # 3.9 Self-reverting case folding U+01F0 and normalization.
    # The original test case is bogus, it says `\xc7\xf0'
    ('\xc7\xb0',
     '\xc7\xb0'),
    # 3.10 Self-reverting case folding U+0390 and normalization.
    ('\xce\x90',
     '\xce\x90'),
    # 3.11 Self-reverting case folding U+03B0 and normalization.
    ('\xce\xb0',
     '\xce\xb0'),
    # 3.12 Self-reverting case folding U+1E96 and normalization.
    ('\xe1\xba\x96',
     '\xe1\xba\x96'),
    # 3.13 Self-reverting case folding U+1F56 and normalization.
    ('\xe1\xbd\x96',
     '\xe1\xbd\x96'),
    # 3.14 ASCII space character U+0020.
    (' ',
     ' '),
    # 3.15 Non-ASCII 8bit space character U+00A0.
    ('\xc2\xa0',
     ' '),
    # 3.16 Non-ASCII multibyte space character U+1680.
    ('\xe1\x9a\x80',
     None),
    # 3.17 Non-ASCII multibyte space character U+2000.
    ('\xe2\x80\x80',
     ' '),
    # 3.18 Zero Width Space U+200b.
    ('\xe2\x80\x8b',
     ''),
    # 3.19 Non-ASCII multibyte space character U+3000.
    ('\xe3\x80\x80',
     ' '),
    # 3.20 ASCII control characters U+0010 U+007F.
    ('\x10\x7f',
     '\x10\x7f'),
    # 3.21 Non-ASCII 8bit control character U+0085.
    ('\xc2\x85',
     None),
    # 3.22 Non-ASCII multibyte control character U+180E.
    ('\xe1\xa0\x8e',
     None),
    # 3.23 Zero Width No-Break Space U+FEFF.
    ('\xef\xbb\xbf',
     ''),
    # 3.24 Non-ASCII control character U+1D175.
    ('\xf0\x9d\x85\xb5',
     None),
    # 3.25 Plane 0 private use character U+F123.
    ('\xef\x84\xa3',
     None),
    # 3.26 Plane 15 private use character U+F1234.
    ('\xf3\xb1\x88\xb4',
     None),
    # 3.27 Plane 16 private use character U+10F234.
    ('\xf4\x8f\x88\xb4',
     None),
    # 3.28 Non-character code point U+8FFFE.
    ('\xf2\x8f\xbf\xbe',
     None),
    # 3.29 Non-character code point U+10FFFF.
    ('\xf4\x8f\xbf\xbf',
     None),
    # 3.30 Surrogate code U+DF42.
    # THIS IS NOT LEGAL IN JYTHON so omitting
    # ('\xed\xbd\x82',
    #  None),
    # 3.31 Non-plain text character U+FFFD.
    ('\xef\xbf\xbd',
     None),
    # 3.32 Ideographic description character U+2FF5.
    ('\xe2\xbf\xb5',
     None),
    # 3.33 Display property character U+0341.
    ('\xcd\x81',
     '\xcc\x81'),
    # 3.34 Left-to-right mark U+200E.
    ('\xe2\x80\x8e',
     None),
    # 3.35 Deprecated U+202A.
    ('\xe2\x80\xaa',
     None),
    # 3.36 Language tagging character U+E0001.
    ('\xf3\xa0\x80\x81',
     None),
    # 3.37 Language tagging character U+E0042.
    ('\xf3\xa0\x81\x82',
     None),
    # 3.38 Bidi: RandALCat character U+05BE and LCat characters.
    ('foo\xd6\xbebar',
     None),
    # 3.39 Bidi: RandALCat character U+FD50 and LCat characters.
    ('foo\xef\xb5\x90bar',
     None),
    # 3.40 Bidi: RandALCat character U+FB38 and LCat characters.
    ('foo\xef\xb9\xb6bar',
     'foo \xd9\x8ebar'),
    # 3.41 Bidi: RandALCat without trailing RandALCat U+0627 U+0031.
    ('\xd8\xa71',
     None),
    # 3.42 Bidi: RandALCat character U+0627 U+0031 U+0628.
    ('\xd8\xa71\xd8\xa8',
     '\xd8\xa71\xd8\xa8'),
    # 3.43 Unassigned code point U+E0002.
    # Skip this test as we allow unassigned
    #('\xf3\xa0\x80\x82',
    # None),
    (None, None),
    # 3.44 Larger test (shrinking).
    # Original test case reads \xc3\xdf
    ('X\xc2\xad\xc3\x9f\xc4\xb0\xe2\x84\xa1j\xcc\x8c\xc2\xa0\xc2'
     '\xaa\xce\xb0\xe2\x80\x80',
     'xssi\xcc\x87tel\xc7\xb0 a\xce\xb0 '),
    # 3.45 Larger test (expanding).
    # Original test case reads \xc3\x9f
    ('X\xc3\x9f\xe3\x8c\x96\xc4\xb0\xe2\x84\xa1\xe2\x92\x9f\xe3\x8c'
     '\x80',
     'xss\xe3\x82\xad\xe3\x83\xad\xe3\x83\xa1\xe3\x83\xbc\xe3'
     '\x83\x88\xe3\x83\xabi\xcc\x87tel\x28d\x29\xe3\x82'
     '\xa2\xe3\x83\x91\xe3\x83\xbc\xe3\x83\x88')
    ]


class NameprepTest(unittest.TestCase):
    def test_nameprep(self):
        from encodings.idna import nameprep
        for pos, (orig, prepped) in enumerate(nameprep_tests):
            if orig is None:
                # Skipped
                continue
            # The Unicode strings are given in UTF-8
            orig = str(orig, "utf-8")
            if prepped is None:
                # Input contains prohibited characters
                self.assertRaises(UnicodeError, nameprep, orig)
            else:
                prepped = str(prepped, "utf-8")
                try:
                    self.assertEqual(nameprep(orig), prepped)
                except Exception as e:
                    raise support.TestFailed("Test 3.%d: %s" % (pos+1, str(e)))

# @unittest.skipIf(support.is_jython, "FIXME: Jython issue 1153 missing support for IDNA")
class IDNACodecTest(unittest.TestCase):
    def test_builtin_decode(self):
        self.assertEqual(str("python.org", "idna"), "python.org")
        self.assertEqual(str("python.org.", "idna"), "python.org.")
        self.assertEqual(str("xn--pythn-mua.org", "idna"), "pyth\xf6n.org")
        self.assertEqual(str("xn--pythn-mua.org.", "idna"), "pyth\xf6n.org.")

    def test_builtin_encode(self):
        self.assertEqual("python.org".encode("idna"), "python.org")
        self.assertEqual("python.org.".encode("idna"), "python.org.")
        self.assertEqual("pyth\xf6n.org".encode("idna"), "xn--pythn-mua.org")
        self.assertEqual("pyth\xf6n.org.".encode("idna"), "xn--pythn-mua.org.")

    def test_stream(self):
        import io
        r = codecs.getreader("idna")(io.StringIO("abc"))
        r.read(3)
        self.assertEqual(r.read(), "")

    def test_incremental_decode(self):
        self.assertEqual(
            "".join(codecs.iterdecode("python.org", "idna")),
            "python.org"
        )
        self.assertEqual(
            "".join(codecs.iterdecode("python.org.", "idna")),
            "python.org."
        )
        self.assertEqual(
            "".join(codecs.iterdecode("xn--pythn-mua.org.", "idna")),
            "pyth\xf6n.org."
        )
        self.assertEqual(
            "".join(codecs.iterdecode("xn--pythn-mua.org.", "idna")),
            "pyth\xf6n.org."
        )

        decoder = codecs.getincrementaldecoder("idna")()
        self.assertEqual(decoder.decode("xn--xam", ), "")
        self.assertEqual(decoder.decode("ple-9ta.o", ), "\xe4xample.")
        self.assertEqual(decoder.decode("rg"), "")
        self.assertEqual(decoder.decode("", True), "org")

        decoder.reset()
        self.assertEqual(decoder.decode("xn--xam", ), "")
        self.assertEqual(decoder.decode("ple-9ta.o", ), "\xe4xample.")
        self.assertEqual(decoder.decode("rg."), "org.")
        self.assertEqual(decoder.decode("", True), "")

    def test_incremental_encode(self):
        self.assertEqual(
            "".join(codecs.iterencode("python.org", "idna")),
            "python.org"
        )
        self.assertEqual(
            "".join(codecs.iterencode("python.org.", "idna")),
            "python.org."
        )
        self.assertEqual(
            "".join(codecs.iterencode("pyth\xf6n.org.", "idna")),
            "xn--pythn-mua.org."
        )
        self.assertEqual(
            "".join(codecs.iterencode("pyth\xf6n.org.", "idna")),
            "xn--pythn-mua.org."
        )

        encoder = codecs.getincrementalencoder("idna")()
        self.assertEqual(encoder.encode("\xe4x"), "")
        self.assertEqual(encoder.encode("ample.org"), "xn--xample-9ta.")
        self.assertEqual(encoder.encode("", True), "org")

        encoder.reset()
        self.assertEqual(encoder.encode("\xe4x"), "")
        self.assertEqual(encoder.encode("ample.org."), "xn--xample-9ta.org.")
        self.assertEqual(encoder.encode("", True), "")

class CodecsModuleTest(unittest.TestCase):

    def test_decode(self):
        self.assertEqual(codecs.decode('\xe4\xf6\xfc', 'latin-1'),
                          '\xe4\xf6\xfc')
        self.assertRaises(TypeError, codecs.decode)
        self.assertEqual(codecs.decode('abc'), 'abc')
        self.assertRaises(UnicodeDecodeError, codecs.decode, '\xff', 'ascii')

    def test_encode(self):
        self.assertEqual(codecs.encode('\xe4\xf6\xfc', 'latin-1'),
                          '\xe4\xf6\xfc')
        self.assertRaises(TypeError, codecs.encode)
        self.assertRaises(LookupError, codecs.encode, "foo", "__spam__")
        self.assertEqual(codecs.encode('abc'), 'abc')
        self.assertRaises(UnicodeEncodeError, codecs.encode, '\xffff', 'ascii')

    def test_register(self):
        self.assertRaises(TypeError, codecs.register)
        self.assertRaises(TypeError, codecs.register, 42)

    def test_lookup(self):
        self.assertRaises(TypeError, codecs.lookup)
        self.assertRaises(LookupError, codecs.lookup, "__spam__")
        self.assertRaises(LookupError, codecs.lookup, " ")

    def test_getencoder(self):
        self.assertRaises(TypeError, codecs.getencoder)
        self.assertRaises(LookupError, codecs.getencoder, "__spam__")

    def test_getdecoder(self):
        self.assertRaises(TypeError, codecs.getdecoder)
        self.assertRaises(LookupError, codecs.getdecoder, "__spam__")

    def test_getreader(self):
        self.assertRaises(TypeError, codecs.getreader)
        self.assertRaises(LookupError, codecs.getreader, "__spam__")

    def test_getwriter(self):
        self.assertRaises(TypeError, codecs.getwriter)
        self.assertRaises(LookupError, codecs.getwriter, "__spam__")

    def test_lookup_issue1813(self):
        # Issue #1813: under Turkish locales, lookup of some codecs failed
        # because 'I' is lowercased as a dotless "i"
        oldlocale = locale.getlocale(locale.LC_CTYPE)
        self.addCleanup(locale.setlocale, locale.LC_CTYPE, oldlocale)
        try:
            locale.setlocale(locale.LC_CTYPE, 'tr_TR')
        except locale.Error:
            # Unsupported locale on this system
            self.skipTest('test needs Turkish locale')
        c = codecs.lookup('ASCII')
        self.assertEqual(c.name, 'ascii')

class StreamReaderTest(unittest.TestCase):

    def setUp(self):
        self.reader = codecs.getreader('utf-8')
        self.stream = io.StringIO('\xed\x95\x9c\n\xea\xb8\x80')

    def test_readlines(self):
        f = self.reader(self.stream)
        self.assertEqual(f.readlines(), ['\ud55c\n', '\uae00'])

class EncodedFileTest(unittest.TestCase):

    def test_basic(self):
        f = io.StringIO('\xed\x95\x9c\n\xea\xb8\x80')
        ef = codecs.EncodedFile(f, 'utf-16-le', 'utf-8')
        self.assertEqual(ef.read(), '\\\xd5\n\x00\x00\xae')

        f = io.StringIO()
        ef = codecs.EncodedFile(f, 'utf-8', 'latin1')
        ef.write('\xc3\xbc')
        self.assertEqual(f.getvalue(), '\xfc')

class Str2StrTest(unittest.TestCase):

    def test_read(self):
        sin = "\x80".encode("base64_codec")
        reader = codecs.getreader("base64_codec")(io.StringIO(sin))
        sout = reader.read()
        self.assertEqual(sout, "\x80")
        self.assertIsInstance(sout, str)

    def test_readline(self):
        sin = "\x80".encode("base64_codec")
        reader = codecs.getreader("base64_codec")(io.StringIO(sin))
        sout = reader.readline()
        self.assertEqual(sout, "\x80")
        self.assertIsInstance(sout, str)

all_unicode_encodings = [
    "ascii",
    "base64_codec",
    "big5",
    "big5hkscs",
    "charmap",
    "cp037",
    "cp1006",
    "cp1026",
    "cp1140",
    "cp1250",
    "cp1251",
    "cp1252",
    "cp1253",
    "cp1254",
    "cp1255",
    "cp1256",
    "cp1257",
    "cp1258",
    "cp424",
    "cp437",
    "cp500",
    "cp720",
    "cp737",
    "cp775",
    "cp850",
    "cp852",
    "cp855",
    "cp856",
    "cp857",
    "cp858",
    "cp860",
    "cp861",
    "cp862",
    "cp863",
    "cp864",
    "cp865",
    "cp866",
    "cp869",
    "cp874",
    "cp875",
    "cp932",
    "cp949",
    "cp950",
    # "euc_jis_2004",  # Not available on Java
    # 'euc_jisx0213',  # Not available on Java
    'euc_jp',
    'euc_kr',
    'gb18030',
    'gb2312',
    'gbk',
    "hex_codec",
    "hp_roman8",
    # 'hz', # Not available on Java
    "idna",
    'iso2022_jp',
    # 'iso2022_jp_1', # Not available on Java
    'iso2022_jp_2',
    # 'iso2022_jp_2004', # Not available on Java
    # 'iso2022_jp_3', # Not available on Java
    # 'iso2022_jp_ext', # Not available on Java
    'iso2022_kr',
    "iso8859_1",
    "iso8859_10",
    "iso8859_11",
    "iso8859_13",
    "iso8859_14",
    "iso8859_15",
    "iso8859_16",
    "iso8859_2",
    "iso8859_3",
    "iso8859_4",
    "iso8859_5",
    "iso8859_6",
    "iso8859_7",
    "iso8859_8",
    "iso8859_9",
    'johab',
    "koi8_r",
    "koi8_u",
    "latin_1",
    "mac_cyrillic",
    "mac_greek",
    "mac_iceland",
    "mac_latin2",
    "mac_roman",
    "mac_turkish",
    "palmos",
    "ptcp154",
    "punycode",
    "raw_unicode_escape",
    "rot_13",
    "shift_jis",
    #'shift_jis_2004', # Not available on Java
    'shift_jisx0213',
    "tis_620",
    "unicode_escape",
    "unicode_internal",
    "utf_16",
    "utf_16_be",
    "utf_16_le",
    "utf_7",
    "utf_8",
]

if hasattr(codecs, "mbcs_encode"):
    all_unicode_encodings.append("mbcs")

# The following encodings work only with str, not unicode
all_string_encodings = [
    "quopri_codec",
    "string_escape",
    "uu_codec",
]

# The following encoding is not tested, because it's not supposed
# to work:
#    "undefined"

# The following encodings don't work in stateful mode
broken_unicode_with_streams = [
    "base64_codec",
    "hex_codec",
    "punycode",
    "unicode_internal"
]
broken_incremental_coders = broken_unicode_with_streams[:]

# The following encodings only support "strict" mode
only_strict_mode = [
    "idna",
    "zlib_codec",
    "bz2_codec",
]

try:
    import bz2
except ImportError:
    pass
else:
    all_unicode_encodings.append("bz2_codec")
    broken_unicode_with_streams.append("bz2_codec")

try:
    import zlib
except ImportError:
    pass
else:
    all_unicode_encodings.append("zlib_codec")
    broken_unicode_with_streams.append("zlib_codec")

class BasicUnicodeTest(unittest.TestCase):

    @unittest.skipIf(support.is_jython, "_testcapi module not present in Jython")
    def test_basics(self):
        s = "abc123" # all codecs should be able to encode these
        for encoding in all_unicode_encodings:
            name = codecs.lookup(encoding).name
            if encoding.endswith("_codec"):
                name += "_codec"
            elif encoding == "latin_1":
                name = "latin_1"
            self.assertEqual(encoding.replace("_", "-"), name.replace("_", "-"))
            (bytes, size) = codecs.getencoder(encoding)(s)
            self.assertEqual(size, len(s), "%r != %r (encoding=%r)" % (size, len(s), encoding))
            (chars, size) = codecs.getdecoder(encoding)(bytes)
            self.assertEqual(chars, s, "%r != %r (encoding=%r)" % (chars, s, encoding))

            if encoding not in broken_unicode_with_streams:
                # check stream reader/writer
                q = Queue()
                writer = codecs.getwriter(encoding)(q)
                encodedresult = ""
                for c in s:
                    writer.write(c)
                    encodedresult += q.read()
                q = Queue()
                reader = codecs.getreader(encoding)(q)
                decodedresult = ""
                for c in encodedresult:
                    q.write(c)
                    decodedresult += reader.read()
                self.assertEqual(decodedresult, s, "%r != %r (encoding=%r)" % (decodedresult, s, encoding))

            if encoding not in broken_incremental_coders:
                # check incremental decoder/encoder (fetched via the Python
                # and C API) and iterencode()/iterdecode()
                try:
                    encoder = codecs.getincrementalencoder(encoding)()
                    cencoder = _testcapi.codec_incrementalencoder(encoding)
                except LookupError: # no IncrementalEncoder
                    pass
                else:
                    # check incremental decoder/encoder
                    encodedresult = ""
                    for c in s:
                        encodedresult += encoder.encode(c)
                    encodedresult += encoder.encode("", True)
                    decoder = codecs.getincrementaldecoder(encoding)()
                    decodedresult = ""
                    for c in encodedresult:
                        decodedresult += decoder.decode(c)
                    decodedresult += decoder.decode("", True)
                    self.assertEqual(decodedresult, s, "%r != %r (encoding=%r)" % (decodedresult, s, encoding))

                    # check C API
                    encodedresult = ""
                    for c in s:
                        encodedresult += cencoder.encode(c)
                    encodedresult += cencoder.encode("", True)
                    cdecoder = _testcapi.codec_incrementaldecoder(encoding)
                    decodedresult = ""
                    for c in encodedresult:
                        decodedresult += cdecoder.decode(c)
                    decodedresult += cdecoder.decode("", True)
                    self.assertEqual(decodedresult, s, "%r != %r (encoding=%r)" % (decodedresult, s, encoding))

                    # check iterencode()/iterdecode()
                    result = "".join(codecs.iterdecode(codecs.iterencode(s, encoding), encoding))
                    self.assertEqual(result, s, "%r != %r (encoding=%r)" % (result, s, encoding))

                    # check iterencode()/iterdecode() with empty string
                    result = "".join(codecs.iterdecode(codecs.iterencode("", encoding), encoding))
                    self.assertEqual(result, "")

                if encoding not in only_strict_mode:
                    # check incremental decoder/encoder with errors argument
                    try:
                        encoder = codecs.getincrementalencoder(encoding)("ignore")
                        cencoder = _testcapi.codec_incrementalencoder(encoding, "ignore")
                    except LookupError: # no IncrementalEncoder
                        pass
                    else:
                        encodedresult = "".join(encoder.encode(c) for c in s)
                        decoder = codecs.getincrementaldecoder(encoding)("ignore")
                        decodedresult = "".join(decoder.decode(c) for c in encodedresult)
                        self.assertEqual(decodedresult, s, "%r != %r (encoding=%r)" % (decodedresult, s, encoding))

                        encodedresult = "".join(cencoder.encode(c) for c in s)
                        cdecoder = _testcapi.codec_incrementaldecoder(encoding, "ignore")
                        decodedresult = "".join(cdecoder.decode(c) for c in encodedresult)
                        self.assertEqual(decodedresult, s, "%r != %r (encoding=%r)" % (decodedresult, s, encoding))

    def test_seek(self):
        # all codecs - except idna on Java - should be able to encode these
        s1 = "%s\n%s\n" % (100*"abc123", 100*"def456")
        for encoding in all_unicode_encodings:
            s = s1
            if encoding in broken_unicode_with_streams:
                continue
            if encoding == "idna":
                s =  "%s\n%s\n" % (5*"abc123", 5*"def456") # idna encoder rejects as being too long
            reader = codecs.getreader(encoding)(io.StringIO(s.encode(encoding)))
            for t in range(5):
                # Test that calling seek resets the internal codec state and buffers
                reader.seek(0, 0)
                line = reader.readline()
                self.assertEqual(s[:len(line)], line)

    def test_bad_decode_args(self):
        for encoding in all_unicode_encodings:
            decoder = codecs.getdecoder(encoding)
            self.assertRaises(TypeError, decoder)
            if encoding not in ("idna", "punycode"):
                self.assertRaises(TypeError, decoder, 42)

    def test_bad_encode_args(self):
        for encoding in all_unicode_encodings:
            encoder = codecs.getencoder(encoding)
            self.assertRaises(TypeError, encoder)

    def test_encoding_map_type_initialized(self):
        from encodings import cp1140
        # This used to crash, we are only verifying there's no crash.
        table_type = type(cp1140.encoding_table)
        self.assertEqual(table_type, table_type)

class BasicStrTest(unittest.TestCase):
    def test_basics(self):
        s = "abc123"
        for encoding in all_string_encodings:
            (bytes, size) = codecs.getencoder(encoding)(s)
            self.assertEqual(size, len(s))
            (chars, size) = codecs.getdecoder(encoding)(bytes)
            self.assertEqual(chars, s, "%r != %r (encoding=%r)" % (chars, s, encoding))

class CharmapTest(unittest.TestCase):
    def test_decode_with_string_map(self):
        self.assertEqual(
            codecs.charmap_decode("\x00\x01\x02", "strict", "abc"),
            ("abc", 3)
        )

        self.assertEqual(
            codecs.charmap_decode("\x00\x01\x02", "replace", "ab"),
            ("ab\ufffd", 3)
        )

        self.assertEqual(
            codecs.charmap_decode("\x00\x01\x02", "replace", "ab\ufffe"),
            ("ab\ufffd", 3)
        )

        self.assertEqual(
            codecs.charmap_decode("\x00\x01\x02", "ignore", "ab"),
            ("ab", 3)
        )

        self.assertEqual(
            codecs.charmap_decode("\x00\x01\x02", "ignore", "ab\ufffe"),
            ("ab", 3)
        )

        allbytes = "".join(chr(i) for i in range(256))
        self.assertEqual(
            codecs.charmap_decode(allbytes, "ignore", ""),
            ("", len(allbytes))
        )

class WithStmtTest(unittest.TestCase):
    def test_encodedfile(self):
        f = io.StringIO("\xc3\xbc")
        with codecs.EncodedFile(f, "latin-1", "utf-8") as ef:
            self.assertEqual(ef.read(), "\xfc")

    def test_streamreaderwriter(self):
        f = io.StringIO("\xc3\xbc")
        info = codecs.lookup("utf-8")
        with codecs.StreamReaderWriter(f, info.streamreader,
                                       info.streamwriter, 'strict') as srw:
            self.assertEqual(srw.read(), "\xfc")


class BomTest(unittest.TestCase):
    def test_seek0(self):
        data = "1234567890"
        tests = ("utf-16",
                 "utf-16-le",
                 "utf-16-be",
                 "utf-32",
                 "utf-32-le",
                 "utf-32-be",
                 )
        self.addCleanup(support.unlink, support.TESTFN)
        for encoding in tests:
            # Check if the BOM is written only once
            with codecs.open(support.TESTFN, 'w+', encoding=encoding) as f:
                f.write(data)
                f.write(data)
                f.seek(0)
                self.assertEqual(f.read(), data * 2)
                f.seek(0)
                self.assertEqual(f.read(), data * 2)

            # Check that the BOM is written after a seek(0)
            with codecs.open(support.TESTFN, 'w+', encoding=encoding) as f:
                f.write(data[0])
                self.assertNotEqual(f.tell(), 0)
                f.seek(0)
                f.write(data)
                f.seek(0)
                self.assertEqual(f.read(), data)

            # (StreamWriter) Check that the BOM is written after a seek(0)
            with codecs.open(support.TESTFN, 'w+', encoding=encoding) as f:
                f.writer.write(data[0])
                self.assertNotEqual(f.writer.tell(), 0)
                f.writer.seek(0)
                f.writer.write(data)
                f.seek(0)
                self.assertEqual(f.read(), data)

            # Check that the BOM is not written after a seek() at a position
            # different than the start
            with codecs.open(support.TESTFN, 'w+', encoding=encoding) as f:
                f.write(data)
                f.seek(f.tell())
                f.write(data)
                f.seek(0)
                self.assertEqual(f.read(), data * 2)

            # (StreamWriter) Check that the BOM is not written after a seek()
            # at a position different than the start
            with codecs.open(support.TESTFN, 'w+', encoding=encoding) as f:
                f.writer.write(data)
                f.writer.seek(f.writer.tell())
                f.writer.write(data)
                f.seek(0)
                self.assertEqual(f.read(), data * 2)


def test_main():
    support.run_unittest(
        UTF32Test,
        UTF32LETest,
        UTF32BETest,
        UTF16Test,
        UTF16LETest,
        UTF16BETest,
        UTF8Test,
        UTF8SigTest,
        UTF7Test,
        UTF16ExTest,
        ReadBufferTest,
        CharBufferTest,
        EscapeDecodeTest,
        RecodingTest,
        PunycodeTest,
        UnicodeInternalTest,
        NameprepTest,
        IDNACodecTest,
        CodecsModuleTest,
        StreamReaderTest,
        EncodedFileTest,
        Str2StrTest,
        BasicUnicodeTest,
        BasicStrTest,
        CharmapTest,
        WithStmtTest,
        BomTest,
    )


if __name__ == "__main__":
    test_main()
