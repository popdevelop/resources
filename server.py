import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.forms.models import model_to_dict
from models import Station
from models import Line
import database
import logging
import os.path
import tornado.escape
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import util
import xml.etree.ElementTree as ET

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/neareststations", NearestStationsHandler),
            (r"/querystation", QueryStationHandler),
            (r"/stationresults", StationResultsHandler)
        ]
        settings = dict(
            cookie_secret="61oETzKXnQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        user_json = self.get_secure_cookie("user")
        if not user_json: return None
        return tornado.escape.json_decode(user_json)


class MainHandler(BaseHandler):
    def get(self):
        self.render("index.html")


class APIHandler(BaseHandler):
    @tornado.web.asynchronous
    def get(self):
        self.args = dict(zip(self.request.arguments.keys(),
                             map(lambda a: a[0],
                                 self.request.arguments.values())))
        client = tornado.httpclient.AsyncHTTPClient()
        command = self.build_command(self.args)
        if not command: raise tornado.web.HTTPError(204)
        print command
        client.fetch(command, callback=self.async_callback(self.on_response))

    def on_response(self, response):
        if response.error: raise tornado.web.HTTPError(500)

        try:
            tree = ET.XML(response.body)
        except Exception as e:
            raise tornado.web.HTTPError(500)

        json = tornado.escape.json_encode(self.handle_result(tree))
        if "callback" in self.args:
            json = "%s(%s)" % (self.args["callback"], json)
        self.set_header("Content-Length", len(json))
        self.set_header("Content-Type", "application/json")
        self.write(json)
        self.finish()

    def build_command(self, args):
        return None

    def handle_result(self, tree):
        return []


class NearestStationsHandler(APIHandler):
    def build_command(self, args):
        (x, y) = util.WGS84_to_RT90(float(args["lat"]),
                                    float(args["lon"]))
        return "http://www.labs.skanetrafiken.se/v2.2/" \
            "neareststation.asp?x=%s&y=%s&R=1000" % (x, y)

    def handle_result(self, tree):
        stations = []
        ns = "http://www.etis.fskab.se/v1.0/ETISws"
        for station in tree.find('.//{%s}NearestStopAreas' % ns):
            s = Station()
            s.name = station.find('.//{%s}Name' % ns).text
            s.key = station.find('.//{%s}Id' % ns).text
            X = int(station.find('.//{%s}X' % ns).text)
            Y = int(station.find('.//{%s}Y' % ns).text)
            (s.lat, s.lon) = util.RT90_to_WGS84(X, Y)
            stations.append(s)
        return [model_to_dict(s) for s in stations]


class QueryStationHandler(APIHandler):
    def build_command(self, args):
        return "http://www.labs.skanetrafiken.se/v2.2/" \
            "querystation.asp?inpPointfr=%s" % args["q"]

    def handle_result(self, tree):
        stations = []
        ns = "http://www.etis.fskab.se/v1.0/ETISws"
        for station in tree.findall('.//{%s}StartPoints//{%s}Point' % (ns, ns)):
            s = Station()
            s.name = station.find('.//{%s}Name' % ns).text
            s.key = station.find('.//{%s}Id' % ns).text
            X = int(station.find('.//{%s}X' % ns).text)
            Y = int(station.find('.//{%s}Y' % ns).text)
            (s.lat, s.lon) = util.RT90_to_WGS84(X, Y)
            stations.append(s)

        return [model_to_dict(s) for s in stations]


class StationResultsHandler(APIHandler):
    def build_command(self, args):
        return "http://www.labs.skanetrafiken.se/v2.2/" \
            "stationresults.asp?selPointFrKey=%s" % args["s"]

    def handle_result(self, tree):
        lines = []
        ns = "http://www.etis.fskab.se/v1.0/ETISws"
        for line in tree.findall('.//{%s}Lines//{%s}Line' % (ns, ns)):
            l = Line()
            l.name = line.find('.//{%s}Name' % ns).text
            l.time = line.find('.//{%s}JourneyDateTime' % ns).text
            l.type = line.find('.//{%s}LineTypeName' % ns).text
            l.towards = line.find('.//{%s}Towards' % ns).text
            lines.append(l)

        return [model_to_dict(l) for l in lines]


def main():
    database.Database()
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
