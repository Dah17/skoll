# import typing as t
# from attrs import define, field
# from asyncio import Queue, Event, create_task, wait

# from skoll.domain import Message
# from skoll.result import Result, fail
# from skoll.application import Subscriber, MissingSubscriber, Mediator, Service, RawMessage

# from .utils import run_callback, is_subscribed

# __all__ = ["BasicMediator"]


# @define(kw_only=True, slots=True)
# class BasicMediator(Mediator):
#     """Basic in-memory mediator implementation."""

#     queue: Queue[Message | RawMessage] = field(factory=Queue)
#     stop_signal: Event = field(factory=Event)
#     subscribers: list[Subscriber] = field(factory=list)
#     handlers: dict[str, Subscriber] = field(factory=dict)

#     @t.override
#     async def publish(self, msg: Message | RawMessage) -> None:
#         self.queue.put_nowait(msg)

#     @t.override
#     async def disconnect(self):
#         self.stop_signal.set()

#     @t.override
#     async def request(self, msg: Message | RawMessage) -> Result[t.Any]:
#         topic = msg.topic if isinstance(msg, Message) else msg["topic"]
#         subscriber = self.handlers.get(topic)
#         if subscriber is not None:
#             return await run_callback(subscriber, msg)
#         return fail(err=MissingSubscriber(debug={"subject": topic}))

#     @t.override
#     def register(self, *services: Service) -> None:
#         for service in services:
#             for subscriber in service.subscribers:
#                 if subscriber.with_reply:
#                     self.handlers[subscriber.topic] = subscriber
#                 else:
#                     self.subscribers.append(subscriber)

#     @t.override
#     async def connect(self):
#         while not self.stop_signal.is_set() or not self.queue.empty():
#             try:
#                 msg = await self.queue.get()
#                 tasks = [
#                     create_task(run_callback(subscriber, msg))
#                     for subscriber in self.subscribers
#                     if is_subscribed(subscriber, msg)
#                 ]
#                 await wait(tasks)
#             except Exception as exc:
#                 print(exc)
