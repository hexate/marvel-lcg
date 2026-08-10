# U10: new issue, /debug reaches exec with no effective auth

Status: POSTED 2026-08-10 as [issue #7](https://github.com/irefrixs/marvel-lcg/issues/7). Tracker
items F6/F6a. Single topic, per his #1 request. F6c (the no-password hole on every route) is
deliberately left out and would be its own issue.

Title: `/debug` runs arbitrary Python, and the auth in front of it is inactive by default

---

This one looks like it fits the "urgent bugfix" exception you mentioned in #5, so I am reporting it
rather than sitting on it. Nothing here is exploitable in a stock install, and I will explain why
before the part that worries me.

`/debug` takes its query string and executes it:

```
GET /debug?<python>
  -> handle_debug_command          engine/device/web/server/server_sync.py:20
  -> Unquote(request.rel_url.query_string)
  -> console.SetCommand            engine/console/console.py:49
  -> RunCheat                      game/world/cheat/cheat_cmd_helper.py:411
  -> IsCommandSafe                 engine/security/command_validation.py:60
  -> exec(cmd)                     game/world/cheat/cheat_cmd_helper.py:481
```

`IsCommandSafe` is a blocklist of module names, so it stops `import os` and not much else.
`__import__('os')` reaches the same place without the word `import` appearing as a statement, and
`().__class__.__base__.__subclasses__()` gets to `Popen` without naming a module at all. I would not
treat that file as a boundary.

The route is registered with `AddAwaitGetSecurity` (`server_sync.py:107`), which sounds like it
covers this. It does not, because `IsAuthenticate` returns `True` for every caller when no password
is configured:

```python
def IsAuthenticate(self, request) -> bool:
    if not self.hash_password:
        return True
```

and `launch.json` ships `"password": ""`. So in the default configuration the wrapper is a no-op
and the blocklist is the entire boundary.

**What keeps this safe out of the box:** `server_addresses` defaults to `127.0.0.1:2345`
(`engine/device/manager/web/manager.py:11`). Nothing can reach the port from another machine, so a
normal single-player install is fine.

**What worries me** is the case the game is for. To play with friends you set `ip` so the port is
reachable, and if you have not also set a password, anyone who can reach it has code execution as
your user. That is a fairly ordinary thing for someone to do on a LAN or behind a port forward, and
nothing in the setup tells them a password is load-bearing.

## What I would suggest

Gate the endpoint on the request being local, or a password actually being set and presented. That
keeps the console working for the person running the game, which is who it is for, and closes the
shared-game case without asking anyone to remember a setting:

```python
def MayRunArbitraryCommands(self, request) -> bool:
    if self.IsLoopback(request):
        return True
    return bool(self.hash_password) and self.IsAuthenticate(request)
```

`IsLoopback` fails closed, so a missing peer address, an unparseable one, or a reverse proxy's
address all count as remote. Refusal returns 403 rather than the authenticate page, since the caller
is a script.

Branch, one commit off master, with tests:
<https://github.com/hexate/marvel-lcg/compare/master...pr/gate-debug-endpoint>

One of the tests pins that `IsAuthenticate` passes a LAN client, so the gate cannot later be
rewritten in terms of the thing it exists to compensate for. Another drives the registered route to
confirm a refused request never reaches the handler.

I would leave `command_validation.py` in place as a typo catcher. It is only worth renaming so it
stops implying a protection it cannot provide, and that is cosmetic next to the gate.

Two related things I am keeping out of this issue rather than piling on. The `IsAuthenticate`
behaviour above affects every route that uses it, not just `/debug`, which is a bigger decision
because failing closed would break multiplayer for anyone who never set a password. And
`/authenticate` itself issues a cookie without checking the password, which turns out not to be a
bypass but does mean a client cannot tell a wrong password from a right one. Happy to file either
separately, or leave them, given where the project is.
