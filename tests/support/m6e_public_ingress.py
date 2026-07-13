from ai_drama_web.app import create_app


class PublicClientIngress:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            scope = dict(scope)
            scope["client"] = ("198.51.100.10", scope.get("client", ("", 0))[1])
        await self.app(scope, receive, send)


def create_public_ingress_app():
    return PublicClientIngress(create_app())
