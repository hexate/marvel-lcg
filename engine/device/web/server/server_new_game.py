from core import *
from aiohttp import web
from engine.device.web.server.server_base import GameServerBase

from engine.lib import Json
# from engine.log import Log
from game.puzzle.puzzle_data import PuzzleData
from game.game_run.game_new import NewGameDescriptor

class GameServerNewGame(GameServerBase):

    async def new_debug(self, request: web.Request) -> web.Response:
        self.game.Restart()
        return web.json_response({'result': "New game created"})

    async def new_game(self, request: web.Request) -> web.Response:
        data = request.rel_url.query.get('data', "")
        new_game = Json.LoadsAs(data, NewGameDescriptor)
        self.game.NewGame(new_game)
        return web.json_response({'result': "New game created"})

    async def load_replay(self, request: web.Request) -> web.Response:
        self.game.LoadReplay(request.rel_url.query_string)
        return web.json_response({'result': "New game created"})

    async def load_replay_data(self, request: web.Request) -> web.Response:
        from game.scene.scene import Scene

        data = await request.json()
        replay_data = data.get('data', None)

        try:
            step = int(request.rel_url.query_string)
        except:
            step = None

        if replay_data is None:
            return web.json_response({'error': 'No data provided'}, status=400)

        # Process the replay_data as needed
        # Log.Print("Received replay data:", replay_data)

        scene = Json.LoadsAs(replay_data, Scene)
        if step == 0:
            state = 'Replay'
        else:
            state = 'Load'
        self.game.session.LoadScene(scene, step, state)

        return web.json_response({'result': "New game created"})

    async def save_replay_data(self, request: web.Request) -> web.Response:
        data = Json.SaveString(self.game.scene, ignore_check_sum=False)
        compressed_data = Json.DumpGZip(data)
        self.device_manager.AddSize("Save", len(compressed_data))
        return web.Response(body=compressed_data, content_type='application/json', headers={'Content-Encoding': 'gzip'})

    def save_local(self, request: web.Request) -> web.Response:
        """Write the current scene to the replays folder, for the game over "Save replay" button.

        `delete_old=False` matches the `/save` debug command: this is a save the player asked for,
        so it should not archive whatever file the scene was loaded from. The automatic save at
        game over passes True because it owns that file.

        The client prints the body as the path it saved to, so a failure has to come back as an
        error status. Returning friendly text on failure reads as success (`command.ts`).
        """
        session = self.game.session
        if not session.scene:
            # SaveScene asserts on a missing scene. Reachable before the first game starts.
            return web.Response(text="Save failed, there is no game to save", status=409)

        file_name = session.SaveScene(delete_old=False)
        if not file_name:
            return web.Response(text="Save failed, the scene was not written", status=500)
        return web.Response(text=file_name)

    def play_puzzle(self, puzzle: 'PuzzleData'):
        from game.scene.scene import Scene

        def get_cards_text(cards: List[str]) -> str:
            text = ",".join(f"'{x}'" for x in cards)
            return text

        puzzle_pre_command: List[str] = []

        def append_puzzle_command(command: str, cards: List[str]) -> None:
            text = get_cards_text(cards)
            if text:
                puzzle_pre_command.append(f"{command}({text})")

        append_puzzle_command("Puzzle.CreateEncounterDeck", puzzle.encounter_deck)
        append_puzzle_command("Puzzle.CreateEncounterDiscardPile", puzzle.encounter_discard_pile)
        append_puzzle_command("Puzzle.CreateHandCards", puzzle.players[0].hand_cards)
        append_puzzle_command("Puzzle.CreatePlayerDiscardPile", puzzle.players[0].player_discard_pile)
        append_puzzle_command("Puzzle.CreatePlayerDeck", puzzle.players[0].player_deck)
        append_puzzle_command("Puzzle.CreatePlayerAdditionalDeck", puzzle.players[0].set_aside)

        puzzle_data = {
            "version": puzzle.version,
            "metadata": {
                "seed": puzzle.seed,
                "comment": puzzle.comment,
                "cover": puzzle.cover,
                "is_puzzle": True
            },
            "campaign": {
                "version": puzzle.version,
                "name": "Villain",
                "villain": puzzle.villain,
                "expert": puzzle.expert,
                "schemes": puzzle.schemes,
                "set_aside": puzzle.set_aside,
                "encounters": [],
                "encounter_sets": [],
                "modular_sets": []
            },
            "players": [
                {
                    "version": puzzle.version,
                    "name": f"Player {index}",
                    "hero": puzzle.players[index].identities,
                    "hero_deck": [],
                    "obligations": [],
                    "nemesis_set": [],
                    "set_aside": puzzle.players[index].set_aside,
                    "player_deck": []
                }
                for index in range(len(puzzle.players))
            ],
            "puzzle": puzzle_pre_command + puzzle.puzzle_command,
        }

        scene = Json.LoadsAs(Json.Dumps(puzzle_data), Scene)
        scene.UpdateVersion()

        self.game.session.LoadScene(scene, None, 'Replay')
        self.controller_manager.skip.SetSkipTo(0)

    async def load_puzzle(self, request: web.Request) -> web.Response:
        puzzle = Json.LoadAs(request.rel_url.query_string, PuzzleData, check_sum="Warn")
        self.play_puzzle(puzzle)
        return web.json_response({'result': "New game created"})

    async def new_puzzle_replay(self, request: web.Request) -> web.Response:
        from game.scene.scene import Scene

        scene = Json.LoadsAs(request.rel_url.query_string, Scene)
        scene.UpdateVersion()

        self.game.session.LoadScene(scene, None, 'Replay')
        self.controller_manager.skip.SetSkipTo(0)
        return web.json_response({'result': "New game created"})

    async def new_puzzle(self, request: web.Request) -> web.Response:
        puzzle = Json.LoadsAs(request.rel_url.query_string, PuzzleData)
        self.play_puzzle(puzzle)
        return web.json_response({'result': "New game created"})

    async def new_game_online(self, request: web.Request) -> web.Response:
        ip = request.query.get('ip')
        port = int(request.query.get('port', 2345))
        assert ip
        text = self.device_manager.AddOnlineSite(ip, port)
        return web.Response(text=text)

    async def new_game_lan(self, request: web.Request) -> web.Response:
        port = int(request.query.get('port', 2345))
        text = self.device_manager.AddLocalNetworkSite(port)
        return web.Response(text=text)

    @override
    def __init__(self) -> None:
        super().__init__()
        self.AddAwaitGetSecurity('/new', self.new_game)
        self.AddAwaitGetSecurity('/new_debug', self.new_debug)
        self.AddAwaitGetSecurity('/load_replay', self.load_replay)
        self.AddPostSecurity('/load_replay_data', self.load_replay_data)
        self.AddAwaitGetSecurity('/save_replay_data', self.save_replay_data)
        # Non-await: SaveScene writes the file synchronously, so it runs off the event loop.
        self.AddNonAwaitGetSecurity('/save_local', self.save_local)
        self.AddAwaitGetSecurity('/load_puzzle', self.load_puzzle)
        self.AddAwaitGetSecurity('/new_puzzle_replay', self.new_puzzle_replay)
        self.AddAwaitGetSecurity('/new_puzzle', self.new_puzzle)
        self.AddAwaitGetSecurity('/new_game_online', self.new_game_online)
        self.AddAwaitGetSecurity('/new_game_lan', self.new_game_lan)

