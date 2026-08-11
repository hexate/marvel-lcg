from core import *

from engine.file import Cache
from engine.device.web import *

from aiohttp import web
from engine.device.web.server.server_base import GameServerBase

CATEGORY_NAME = "WEB"

class GameServerFiles(GameServerBase):

    async def handle_marvel(self, request: web.Request) -> web.StreamResponse:
        if request.query_string == '':
            return self.ReadFile('./public/main.html')
        else:
            return self.ReadFile('./public/marvel.html')

    async def handle_players_404(self, request: web.Request) -> web.StreamResponse:
        player = request.match_info.get('player')
        return web.Response(text=f"Please visiting /?p={player}", status=404)

    def handle_sets_image(self, request: web.Request) -> web.StreamResponse:
        file_path = request.path

        image_bytes = Cache.LoadImage(file_path)

        return web.Response(body=image_bytes, content_type='image/jpeg', headers=self.HeaderCache)

    def handle_image_request(self, request: web.Request) -> web.StreamResponse:
        # file_path = request.match_info['path']
        file_path = request.path
        file_path = file_path.split("/")[-1]

        # This is the last route registered, so it sees every path nothing else claimed. Serving a
        # placeholder for all of them means a missing or misspelled route answers 200 with a grey
        # card instead of failing: that is how `save_local` went unnoticed, the client read the
        # JPEG bytes as its save path and reported success. Cards we have no art for still get the
        # placeholder, because the game registered their names.
        if not Cache.CanLoadImage(file_path):
            return web.Response(text=f"No image named {file_path}", status=404)

        image_bytes = Cache.LoadImage(file_path)
        image_size = len(image_bytes)

        self.device_manager.AddSize("Image", image_size)

        return web.Response(body=image_bytes, content_type='image/jpeg', headers=self.HeaderCache)

    @override
    def __init__(self) -> None:
        super().__init__()

        self.AddDefaultGet()

        self.AddAwaitGetSecurity('/', self.handle_marvel)
        self.AddAwaitGetSecurity(r'/p={player:\d+}', self.handle_players_404)
        self.AddAwaitGetSecurity('/watch', self.handle_marvel)

        self.AddNonAwaitGetSecurity(r'/sets/{path:.+}', self.handle_sets_image)
        self.AddNonAwaitGetSecurity(r'/{path:.+}', self.handle_image_request)

