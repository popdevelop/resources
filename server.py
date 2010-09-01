#!/usr/bin/env python

from django.forms.models import model_to_dict
from models import Station
import database
import logging
import os.path
import tornado.auth
import tornado.escape
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import util
import uuid
import xml.etree.ElementTree as ET

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/logout", AuthLogoutHandler),
            (r"/a/message/new", MessageNewHandler),
            (r"/a/message/updates", MessageUpdatesHandler),
            (r"/neareststations", NearestStationsHandler),
            (r"/querystation", QueryStationHandler),
        ]
        settings = dict(
            cookie_secret="61oETzKXnQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            twitter_consumer_key = "39DOr5gcrYUI6Hga71sgIg",
            twitter_consumer_secret = "sOEV2NW00y6RX5aKzVfFslLjavKRZfLaUS6as1OwvE",
            login_url="/auth/login",
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
    @tornado.web.authenticated
    def get(self):
        self.render("index.html", messages=MessageMixin.cache)


class NearestStationsHandler(BaseHandler):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def get(self):
        self.args = dict(zip(self.request.arguments.keys(),
                             map(lambda a: a[0], self.request.arguments.values())))
        client = tornado.httpclient.AsyncHTTPClient()
        (x, y) = util.WGS84_to_RT90(float(self.args["lat"]), float(self.args["lon"]))
        client.fetch("http://www.labs.skanetrafiken.se/v2.2/"
                     "neareststation.asp?x=%s&y=%s&R=1000" % (x, y),
                     callback=self.async_callback(self.on_response))

    def on_response(self, response):
        if response.error: raise tornado.web.HTTPError(500)

        try:
            e = ET.XML(response.body)
        except Exception as e:
            raise tornado.web.HTTPError(500)

        stations = []
        ns = "http://www.etis.fskab.se/v1.0/ETISws"
        for station in e.find('.//{%s}NearestStopAreas' % ns):
            s = Station()
            s.name = station.find('.//{%s}Name' % ns).text
            s.key = station.find('.//{%s}Id' % ns).text
            X = int(station.find('.//{%s}X' % ns).text)
            Y = int(station.find('.//{%s}Y' % ns).text)
            (s.lat, s.lon) = util.RT90_to_WGS84(X, Y)
            stations.append(s)

        stops = [model_to_dict(s) for s in stations]
        json = tornado.escape.json_encode(stops)
        if "callback" in self.args:
            json = "%s(%s)" % (self.args["callback"], json)
        self.set_header("Content-Length", len(json))
        self.set_header("Content-Type", "application/json")
        self.write(json)
        self.finish()


class QueryStationHandler(BaseHandler):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def get(self):
        self.args = dict(zip(self.request.arguments.keys(),
                             map(lambda a: a[0], self.request.arguments.values())))
        client = tornado.httpclient.AsyncHTTPClient()
        client.fetch("http://www.labs.skanetrafiken.se/v2.2/querystation.asp?inpPointfr=%s" % self.args["q"],
                     callback=self.async_callback(self.on_response))

    def on_response(self, response):
        if response.error: raise tornado.web.HTTPError(500)

        try:
            e = ET.XML(response.body)
        except Exception as e:
            raise tornado.web.HTTPError(500)

        stations = []
        ns = "http://www.etis.fskab.se/v1.0/ETISws"
        for station in e.findall('.//{%s}Point' % ns):
            s = Station()
            s.name = station.find('.//{%s}Name' % ns).text
            s.key = station.find('.//{%s}Id' % ns).text
            X = int(station.find('.//{%s}X' % ns).text)
            Y = int(station.find('.//{%s}Y' % ns).text)
            (s.lat, s.lon) = util.RT90_to_WGS84(X, Y)
            stations.append(s)

        stops = [model_to_dict(s) for s in stations]
        json = tornado.escape.json_encode(stops)
        if "callback" in self.args:
            json = "%s(%s)" % (self.args["callback"], json)
        self.set_header("Content-Length", len(json))
        self.set_header("Content-Type", "application/json")
        self.write(json)
        self.finish()


class MessageMixin(object):
    waiters = []
    cache = []
    cache_size = 200

    def wait_for_messages(self, callback, cursor=None):
        cls = MessageMixin
        if cursor:
            index = 0
            for i in xrange(len(cls.cache)):
                index = len(cls.cache) - i - 1
                if cls.cache[index]["id"] == cursor: break
            recent = cls.cache[index + 1:]
            if recent:
                callback(recent)
                return
        cls.waiters.append(callback)

    def new_messages(self, messages):
        cls = MessageMixin
        logging.info("Sending new message to %r listeners", len(cls.waiters))
        for callback in cls.waiters:
            try:
                callback(messages)
            except:
                logging.error("Error in waiter callback", exc_info=True)
        cls.waiters = []
        cls.cache.extend(messages)
        if len(cls.cache) > self.cache_size:
            cls.cache = cls.cache[-self.cache_size:]


class MessageNewHandler(BaseHandler, MessageMixin):
    @tornado.web.authenticated
    def post(self):
        message = {
            "id": str(uuid.uuid4()),
            "from": self.current_user["first_name"],
            "body": self.get_argument("body"),
        }
        message["html"] = self.render_string("message.html", message=message)
        if self.get_argument("next", None):
            self.redirect(self.get_argument("next"))
        else:
            self.write(message)
        self.new_messages([message])


class MessageUpdatesHandler(BaseHandler, MessageMixin):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self):
        cursor = self.get_argument("cursor", None)
        self.wait_for_messages(self.async_callback(self.on_new_messages),
                               cursor=cursor)

    def on_new_messages(self, messages):
        # Closed client connection
        if self.request.connection.stream.closed():
            return
        self.finish(dict(messages=messages))


class AuthLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect(ax_attrs=["name"])

    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Google auth failed")
        self.set_secure_cookie("user", tornado.escape.json_encode(user))
        self.redirect("/")


class AuthLogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.write("You are now logged out")


def main():
    database.Database()
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
