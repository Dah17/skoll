# import nats
# import typing as t
# from skoll.domain import Message
# from skoll.result import Result, ok
# from skoll.config import NATSConfig
# from skoll.application.types import RawMessage
# from skoll.application import Mediator, Subscriber, Service


# __all__ = ["NATSMediator"]


# class NATSMediator(Mediator):
#     """NATS mediator implementation."""

#     seed: str
#     urls: list[str]
#     subscribers: list[Subscriber]
#     handlers: dict[str, Subscriber]

#     def __init__(self, config: NATSConfig) -> None:
#         if config.urls is None or config.seed is None:
#             raise ValueError("NATS URLs and seed are required")
#         self.urls = config.urls.split(",")
#         self.seed = config.seed
#         self.handlers = {}
#         self.subscribers = []

#     @t.override
#     def register(self, *services: Service) -> None:
#         for service in services:
#             for subscriber in service.subscribers:
#                 if subscriber.with_reply:
#                     self.handlers[subscriber.topic] = subscriber
#                 else:
#                     self.subscribers.append(subscriber)

#     @t.override
#     async def start(self) -> None:
#         pass

#     @t.override
#     async def stop(self) -> None:
#         pass

#     @t.override
#     async def publish(self, msg: Message | RawMessage) -> None:
#         pass

#     @t.override
#     async def request(self, msg: Message | RawMessage) -> Result[t.Any]:
#         return ok(None)
