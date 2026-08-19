from typing import TypeAlias
from core import *
from aiohttp import web
from build import Build
from engine.config import ConfigVariables
from engine.task import TaskManager
# from engine.job import JobManager
from engine.lib import MimeType, Json, Ver
from engine.log import Log
from engine.file import FileManager
import hashlib
import hmac
import ipaddress
import os

CATEGORY_NAME = "WEB"

SOUND_FOLDERS   = ConfigVariables.Folders('sound_folders', ["./assets/sounds/"])
IMAGE_FOLDERS   = ConfigVariables.Folders('image_folders')
TEXTURE_FOLDER  = ConfigVariables.Folder('texture_folder')
CACHE_MAX_AGE   = ConfigVariables.Int('cache_max_age', 31536000)
"""How long a browser may keep an asset that never changes once written.

Card art is content addressed: the picture for a card id is the same picture forever, and fetching
it again is the slow thing this cache exists to prevent. Fonts and audio are the same. A year is
right for these.
"""

CACHE_MAX_AGE_CODE = ConfigVariables.Int('cache_max_age_code', 0)
"""How long a browser may keep markup, styles and scripts.

These change every time you edit one, so the year above was actively harmful: a CSS change stayed
invisible until someone thought to hard reload, and the obvious reading of that is that the change
did not work. Cost real time more than once.

0 means the browser revalidates before using its copy, which is what you want while developing.
Raise it for a deployment where the files are not moving.

one hour:   3600
one day:    86400
one week:   604800
one year:   31536000
"""

CODE_EXTENSIONS = ('.html', '.css', '.js', '.ts', '.map', '.json')
"""Keyed off the extension rather than the MIME type on purpose.

`MimeType` calls `.ts` `video/mp2t` and has no entry for `.map`, so a MIME-based split would hand
both of those the year-long asset cache, which is exactly backwards for the two of them.
"""

PASSWORD            = ConfigVariables.Str('password', "")
DETECTED_VERSION    = ConfigVariables.Bool('detected_version', True)

class WebServer:

    HandleAsyncType: TypeAlias = Callable[["web.Request"], Awaitable["web.StreamResponse"]]
    HandleNonAsyncType: TypeAlias = Callable[["web.Request"], "web.StreamResponse"]

    def __init__(self) -> None:
        self.web_app = web.Application()
        self.runner = web.AppRunner(self.web_app)

        if PASSWORD.value:
            self.hash_password = hashlib.md5(PASSWORD.value.encode()).hexdigest()
        else:
            self.hash_password = None

        WebServer.HeaderCache = {'Cache-Control': f'public, max-age={CACHE_MAX_AGE.value}'}
        # `no-cache` does not mean "do not cache". It means the browser may keep the file but has
        # to check with us before using it, which is the behaviour that keeps an edit visible on a
        # plain reload. `max-age=0` is spelled out separately only so a non-zero setting still
        # works the obvious way.
        WebServer.HeaderCacheCode = (
            {'Cache-Control': 'no-cache'} if CACHE_MAX_AGE_CODE.value <= 0
            else {'Cache-Control': f'public, max-age={CACHE_MAX_AGE_CODE.value}'})

    ################################################################################
    #
    @final
    def CacheHeaderFor(self, file_path: str) -> Dict[str, str]:
        """Long cache for things that never change, short for things you are editing."""
        return self.HeaderCacheCode \
            if os.path.splitext(file_path)[1].lower() in CODE_EXTENSIONS \
            else self.HeaderCache

    @final
    def NoStore(self, response: web.Response) -> web.Response:
        """A guard page describes the state of one request, so it must never be cached.

        `ReadFile` stamps `HeaderCache` on every release build. That is right for card art and
        wrong here: a client that cached the version-mismatch page under a card's URL kept
        serving it for a year, long after the mismatch it was reporting had been resolved.
        """
        response.headers['Cache-Control'] = 'no-store'
        return response

    @final
    def LoadHtmlAuthenticate(self):
        return self.NoStore(self.ReadFile('./public/authenticate.html'))

    @final
    def LoadHtmlCleanCache(self):
        return self.NoStore(self.ReadFile('./public/clean_cache.html'))

    ################################################################################
    #
    @final
    def RefuseResource(self, status: int, reason: str) -> web.Response:
        """Refuse a request without pretending to be the thing it asked for.

        The routes behind this guard serve images and `save_local`, never pages. Answering them
        with the guard page meant a 200 whose body was HTML: nothing downstream could tell that
        from success. The browser cached it under the card's URL, and `save_local` reported the
        page text as the path it had saved to.
        """
        return web.Response(text=f"{reason}\n", status=status,
                            headers={'Cache-Control': 'no-store'})

    @final
    def AddNonAwaitGetSecurity(self, path: str, handle: HandleNonAsyncType):
        async def new_handle(request: web.Request) -> web.StreamResponse:
            if not self.IsAuthenticate(request):
                return self.RefuseResource(401, "not authenticated")
            elif not self.IsVersionMatch(request):
                return self.RefuseResource(409, "client version does not match the server")
            else:
                return await TaskManager.ToThread(handle, request)
        self.web_app.router.add_get(path, new_handle)

    @final
    def AddAwaitGetSecurity(self, path: str, handle: HandleAsyncType, need_auth: bool=True, need_check_version: bool=True):
        async def new_handle(request: web.Request) -> web.StreamResponse:
            if need_auth and not self.IsAuthenticate(request):
                return self.LoadHtmlAuthenticate()
            elif need_check_version and not self.IsVersionMatch(request):
                return self.LoadHtmlCleanCache()
            else:
                return await handle(request)
        self.web_app.router.add_get(path, new_handle)

    @final
    def IsAuthenticate(self, request: web.Request) -> bool:
        if not self.hash_password:
            return True
        app_password_cookie = request.cookies.get('session_token')
        if app_password_cookie != self.hash_password:
            return False
        return True

    @final
    def IsPasswordCorrect(self, attempt: object) -> bool:
        """Does this attempt match the configured password?

        With no password configured there is nothing to be wrong about, and `IsAuthenticate`
        already admits everyone, so refusing here would only confuse. Compared in constant time
        because it is a comparison of secrets and doing it properly costs nothing.
        """
        if not self.hash_password:
            return True
        if not isinstance(attempt, str):
            return False
        attempted = hashlib.md5(attempt.encode()).hexdigest()
        return hmac.compare_digest(attempted, self.hash_password)

    @final
    def IsLoopback(self, request: web.Request) -> bool:
        """Did this request come from the machine running the server?

        Fails closed. An absent or unparseable peer address counts as remote, and behind a reverse
        proxy this is the proxy's address, which is also the answer that errs the safe way.
        """
        remote = request.remote
        if not remote:
            return False
        try:
            return ipaddress.ip_address(remote).is_loopback
        except ValueError:
            return False

    @final
    def MayRunArbitraryCommands(self, request: web.Request) -> bool:
        """Gate for endpoints whose input reaches `exec`, which today means `/debug`.

        `IsAuthenticate` is not sufficient on its own: with no password configured it returns True
        for every caller, and the shipped `launch.json` has an empty password. That is fine for the
        default bind of 127.0.0.1, and it is an open door the moment someone adds a LAN address so
        friends can join.

        So: this machine always, anyone else only when a password is actually set and presented.
        """
        if self.IsLoopback(request):
            return True
        return bool(self.hash_password) and self.IsAuthenticate(request)

    @final
    def AddAwaitGetDebugSecurity(self, path: str, handle: HandleAsyncType):
        """Register a route that can execute arbitrary input.

        Refuses with 403 rather than the authenticate page: the caller is a script, not a browser
        following a login flow, and a page of HTML in response to a command is a confusing way to
        say no.
        """
        async def new_handle(request: web.Request) -> web.StreamResponse:
            if not self.MayRunArbitraryCommands(request):
                Log.Warn(CATEGORY_NAME,
                         f"Refused a debug command from {request.remote}: this endpoint runs "
                         f"arbitrary code, so it needs a request from this machine or a password "
                         f"set in the config.")
                return web.Response(status=403, text="debug commands need a local request or a "
                                                     "configured password")
            elif not self.IsVersionMatch(request):
                return self.LoadHtmlCleanCache()
            else:
                return await handle(request)
        self.web_app.router.add_get(path, new_handle)

    @final
    def IsVersionMatch(self, request: web.Request) -> bool:
        if not DETECTED_VERSION.value:
            return True
        app_version_cookie = request.cookies.get('app_version')
        if app_version_cookie and app_version_cookie != Ver.ui_version_str:
            return False
        elif not app_version_cookie:
            return False
        return True

    @final
    def AddHtmlSecurity(self, path: str, html: str):
        async def handle(request: web.Request) -> web.StreamResponse:
            if not self.IsAuthenticate(request):
                return self.LoadHtmlAuthenticate()
            elif not self.IsVersionMatch(request):
                return self.LoadHtmlCleanCache()
            else:
                return self.ReadFile(html)
        self.web_app.router.add_get(path, handle)

    @final
    def AddPost(self, path: str, handle: HandleAsyncType):
        self.web_app.router.add_post(path, handle)

    @final
    def AddPostSecurity(self, path: str, handle: HandleAsyncType):
        async def new_handle(request: web.Request) -> web.StreamResponse:
            if not self.IsAuthenticate(request):
                return web.Response(status=401)
            else:
                return await handle(request)
        self.web_app.router.add_post(path, new_handle)

    @final
    def ReadJsonFile(self, file_path: str|None, *, do_cache: bool=True) -> web.Response:
        if file_path:
            data = Json.Load(file_path)
            compressed_data = Json.DumpGZip(data)
            headers = {'Content-Encoding': 'gzip'}

            if do_cache:
                headers.update(self.HeaderCache)

            return web.Response(body=compressed_data, content_type='application/json', headers=headers)
        else:
            return web.json_response({})

    @final
    def ReadFile(self, file_path: str, find_paths: List[str]=[]) -> web.Response:
        if file_path.startswith("/"):
            file_path = "." + file_path

        def find_path(file_path: str) -> str:
            for path in ["./"] + find_paths:
                check_path = FileManager.JoinPath(path, file_path)
                if FileManager.Exists(check_path):
                    return check_path
            assert False, f"{file_path=}"

        def read_file(path: str, bin: bool):
            try:
                with FileManager.OpenFile(path, read=True, bin=bin) as file:
                    data = file.Read()
                    if not bin:
                        data = data.encode('utf-8')
                return data
            except Exception as exc:
                Log.FailedTrace(CATEGORY_NAME, exc)
                return ""

        try:
            found_path = find_path(file_path)
            data = read_file(found_path, True)
            mime_type = MimeType.GetMimeType(file_path)
            if Build.release:
                header = self.CacheHeaderFor(file_path)
            else:
                header = {}
            # Every file here is written as UTF-8, but text was served with no charset at all, so
            # the browser had to guess and fell back to latin-1. Six of the thirteen pages carry no
            # `<meta charset>` of their own, and on those any non-ASCII character rendered mojibake
            # (a "·" separator arriving as "Â·"). Saying it in the header fixes all of them at once
            # and does not depend on each page remembering to.
            charset = 'utf-8' if mime_type.startswith('text/') else None
            return web.Response(body=data, content_type=mime_type, charset=charset, headers=header)
        except Exception as exc:
            Log.Debug(CATEGORY_NAME, f"{file_path=}")
            Log.FailedTrace(CATEGORY_NAME, exc)
            # A miss is not an asset. Under the old header a mistyped stylesheet path 404'd once
            # and then kept 404ing from the browser's own cache for a year, long after the file
            # was in place. Same shape as J17, one bad moment made permanent by a cache header.
            return web.Response(status=404, headers={'Cache-Control': 'no-store'})

    @final
    def Run(self, ip: str, port: int, name: str="") -> None:
        async def start_server() -> None:
            try:
                await self.runner.setup()
                site = web.TCPSite(self.runner, ip, port)
                await site.start()
                Log.Print(f"{name}:\thttp://{ip}:{port}")
            except Exception as exc:
                Log.Print(f"{name}:\thttp://{ip}:{port} failed")
                Log.FailedTrace(CATEGORY_NAME, exc, no_take_as_error=True)

        self.ip = ip
        self.port = port
        TaskManager.AddTask(start_server, name="WebServer", run_forever=True)

    def Shutdown(self) -> None:
        pass

    ################################################################################
    #
    def AddDefaultGet(self):
        from build import Build

        async def handle_favicon(request: web.Request):
            file_path = './public/favicon.ico'
            return self.ReadFile(file_path)

        async def handle_authenticate(request: web.Request) -> web.Response:
            try:
                data = await request.json()
                password_attempt = data['password']
            except Exception:
                # Anything that is not a JSON body carrying a password. This used to raise on
                # `None.encode()` and answer 500, which reads as a server fault rather than a
                # malformed request.
                return web.Response(status=400, text="expected a JSON body with a password")

            if not self.IsPasswordCorrect(password_attempt):
                # The check used to happen only on the next request, so every attempt was handed a
                # cookie and a 200 and the client could not tell whether it had got in. No cookie
                # is issued here, so a refusal cannot be mistaken for a session.
                return web.Response(status=401, text="wrong password")

            session_token = hashlib.md5(password_attempt.encode()).hexdigest()

            response = web.Response()
            response.set_cookie(
                'session_token',
                session_token,
                max_age=31536000, # 1 year
                path='/',
                httponly=True, # VERY IMPORTANT: Prevents JavaScript access to the cookie
                # secure=True, # IMPORTANT: Use this flag ONLY if serving over HTTPS
                # samesite='Lax' # Recommended: 'Lax' or 'Strict'
            )
            return response

        async def handle_get_version(request: web.Request) -> web.Response:
            # This response exists to issue the `app_version` cookie below, so it must never be
            # cached. It used to be sent as `image/jpeg` under `HeaderCache`, commented "Hack, make
            # browser treat it as images and store in cache", which worked exactly as described and
            # thereby broke the thing it was serving: a stored copy is replayed from the browser's
            # cache without `Set-Cookie`, so a client that lost the cookie could never get another
            # one, and `IsVersionMatch` refused every route from then on. Restarting the server does
            # not help, because the server is not what is wrong. J18.
            #
            # The jpeg content type only existed to buy the caching, so it goes with it, back to
            # the plain-text response on the line that hack replaced.
            response = self.NoStore(web.Response(text=Ver.ui_version_str))
            response.set_cookie(
                'app_version',
                Ver.ui_version_str,
                max_age=365 * 24 * 60 * 60, # 1 year
                path='/',
                httponly=False
            )
            return response

        async def handle_html(request: web.Request):
            return self.ReadFile(request.path, ['./public/'])

        async def handle_css(request: web.Request):
            return self.ReadFile(request.path, ['./public/css', './public/'])

        async def handle_js(request: web.Request):
            return self.ReadFile(request.path, ['./public/js', './public/'])

        async def handle_ts(request: web.Request):
            if Build.release:
                return web.Response(status=404, headers=self.HeaderCache)
            else:
                return self.ReadFile(request.path, ['./public/js', './public/'])

        async def handle_js_map(request: web.Request):
            if Build.release:
                return web.Response(status=404, headers=self.HeaderCache)
            else:
                return self.ReadFile(request.path, ['./public/js', './public/'])

        def handle_mp3(request: web.Request):
            return self.ReadFile(request.path, SOUND_FOLDERS.value)

        def handle_wav(request: web.Request):
            return self.ReadFile(request.path, SOUND_FOLDERS.value)

        async def handle_font(request: web.Request):
            file_path = request.path
            file_path = file_path.split("/")[-1]
            return self.ReadFile(file_path, ['./public/fonts'])

        async def handle_svg(request: web.Request):
            file_path = request.path
            file_path = file_path.split("/")[-1]
            return self.ReadFile(file_path, [TEXTURE_FOLDER.value])

        async def handle_gif(request: web.Request):
            return self.ReadFile('sparkles.gif', IMAGE_FOLDERS.value + [TEXTURE_FOLDER.value])

        self.AddAwaitGetSecurity('/favicon.ico', handle_favicon)

        self.AddPost(r'/authenticate', handle_authenticate)
        self.AddAwaitGetSecurity(r'/get_version', handle_get_version, need_auth=False, need_check_version=False)

        self.AddAwaitGetSecurity(r'/{path:.+\.html}', handle_html)
        self.AddAwaitGetSecurity(r'/{path:.+\.css}', handle_css)
        self.AddAwaitGetSecurity(r'/{path:.+\.js}', handle_js)
        self.AddAwaitGetSecurity(r'/{path:.+\.ts}', handle_ts)
        self.AddAwaitGetSecurity(r'/{path:.+\.js.map}', handle_js_map)

        self.AddNonAwaitGetSecurity(r'/{path:.+\.mp3}', handle_mp3)
        self.AddNonAwaitGetSecurity(r'/{path:.+\.wav}', handle_wav)

        self.AddAwaitGetSecurity(r'/{path:.+\.eot}', handle_font)
        self.AddAwaitGetSecurity(r'/{path:.+\.woff}', handle_font)
        self.AddAwaitGetSecurity(r'/{path:.+\.ttf}', handle_font)

        self.AddAwaitGetSecurity(r'/{path:.+\.svg}', handle_svg)
        self.AddAwaitGetSecurity(r'/{path:.+\.gif}', handle_gif)

