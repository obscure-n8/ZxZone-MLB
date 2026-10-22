from aiohttp import web
from asyncio import create_subprocess_exec

from bot import config_dict, LOGGER, PORT
from bot.helper.ext_utils.ping import ping_server


async def ping_base_route(repeat=False):
    if token := config_dict["ARGO_TOKEN"]:
        try:
            code = await (
                await create_subprocess_exec(
                    *["cloudflared", "service", "install", token]
                )
            ).wait()
            if code != 0:
                ping_server(repeat)
                return
        except Exception as e:
            LOGGER.error(e)
            ping_server(repeat)
            return
        if config_dict["PING_URL"]:
            ping_route = web.RouteTableDef()

            @ping_route.get("/", allow_head=True)
            async def root_route_handler(_):
                return web.Response(status=200, text="Server pingging...")

            web_app = web.Application(client_max_size=30000000)
            web_app.add_routes(ping_route)
            server = web.AppRunner(web_app)
            await server.setup()
            await web.TCPSite(server, "0.0.0.0", PORT).start()
            LOGGER.info("Ping server running on PORT: %s", PORT)
    ping_server(repeat)


async def kill_route():
    if config_dict["ARGO_TOKEN"]:
        try:
            await (
                await create_subprocess_exec(*["cloudflared", "service", "uninstall"])
            ).wait()
        except Exception as e:
            LOGGER.error(e)
