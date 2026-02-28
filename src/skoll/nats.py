import json
import typing as t
import collections.abc as c

from nats.aio.msg import Msg
from attrs import define, field
from nats.js import JetStreamContext
from nats.aio.client import Client as NatsClient
from nats.aio.subscription import Subscription as NSubscription

from .config import SSL
from .utils import call_with_dependencies
from .result import Result, fail, ok, is_ok, is_fail
from .exceptions import Error, InternalError, ValidationFailed
from .domain import Message, ID, RawMessage, Subscriber, Service, Mediator

__all__ = ["NatsMediator"]


@define(kw_only=True, slots=True)
class NatsMediator(Mediator):

    creds: str
    servers: list[str]
    _js: JetStreamContext | None = None
    nc: NatsClient = field(init=False, factory=lambda: NatsClient())
    subscriptions: dict[str, list[NSubscription]] = field(factory=dict)

    @property
    def js(self) -> JetStreamContext:
        if self._js is None:
            raise InternalError(debug={"message": "JetStream context is not initialized"})
        return self._js

    @t.override
    async def subscribe(self, service: Service) -> ID:
        if not self.nc.is_connected:
            raise InternalError(debug={"message": "Attempt to subscribe before nats client is connected"})
        sub_id = ID.new()
        subscribtions: list[NSubscription] = []
        for subscriber in service.subscribers:
            if subscriber.js_stream is not None:
                sub = await self.js.subscribe(
                    manual_ack=True,
                    subject=subscriber.topic,
                    stream=subscriber.js_stream,
                    cb=wrap_callback(subscriber),
                    durable=subscriber.service_name,
                    queue=subscriber.service_name if subscriber.queued else None,
                )
            else:
                sub = await self.nc.subscribe(
                    subject=subscriber.topic,
                    cb=wrap_callback(subscriber),
                    queue=subscriber.service_name if subscriber.queued else "",
                )
            subscribtions.append(sub)
        self.subscriptions[sub_id.value] = subscribtions
        return sub_id

    @t.override
    async def unsubscribe(self, id: ID) -> None:
        try:
            subscriptions = self.subscriptions.get(id.value, [])
            for sub in subscriptions:
                await sub.unsubscribe(limit=0)
            del self.subscriptions[id.value]
        except Exception as e:
            raise InternalError.from_exception(e)

    @t.override
    async def connect(self) -> None:
        try:
            if self.nc.is_connected or self.nc.is_reconnecting:
                return None
            await self.nc.connect(tls=SSL, servers=self.servers, max_reconnect_attempts=-1, user_credentials=self.creds)
            self._js = self.nc.jetstream()
            return None
        except Exception as e:
            raise InternalError.from_exception(e)

    @t.override
    async def disconnect(self) -> None:
        if self.nc.is_connected:
            await self.nc.drain()

    @t.override
    async def publish(self, *msg: Message | RawMessage) -> None:
        for m in msg:
            subject, payload = (m.name, m.serialize()) if isinstance(m, Message) else (m["name"], m)
            await self.nc.publish(subject, json.dumps(payload).encode("utf-8"))

    @t.override
    async def request(self, msg: Message | RawMessage) -> Result[t.Any]:
        try:
            subject, payload = (msg.name, msg.serialize()) if isinstance(msg, Message) else (msg["name"], msg)
            response = await self.nc.request(subject, json.dumps(payload).encode("utf-8"), timeout=5)
            raw_msg = json.loads(response.data.decode("utf-8"))
            if raw_msg.get("error") is not None:
                return fail(Error.from_dict(raw_msg["error"]))
            return ok(raw_msg.get("data"))
        except TimeoutError as e:
            return fail(InternalError.from_exception(e, extra={"message": f"Request timed out"}))
        except Exception as e:
            return fail(InternalError.from_exception(e))


def get_message(cls: type[Message], message: Message | RawMessage) -> Message:
    if isinstance(message, Message):
        return message
    res = cls.create(raw=message)
    if is_fail(res):
        raise ValidationFailed(errors=res.err.errors)

    return res.value


async def run_callback(subscriber: Subscriber[t.Any], message: Message | RawMessage) -> Result[t.Any]:
    topic = message.name if isinstance(message, Message) else message.get("name")
    try:
        msg = get_message(subscriber.msg_type, message)
        return await call_with_dependencies(subscriber.callback, {subscriber.msg_arg: msg})
    except Error as err:
        return fail(err=err)
    except Exception as exc:
        return fail(err=InternalError.from_exception(exc, extra={"subject": topic, "message": message}))


def wrap_callback(subscriber: Subscriber[t.Any]) -> t.Callable[[Msg], c.Awaitable[None]]:
    async def callback(msg: Msg):
        try:
            raw_msg: RawMessage = json.loads(msg.data.decode("utf-8"))
            result = await run_callback(subscriber, raw_msg)
            if subscriber.will_reply:
                raw_response = {
                    "data": result.value if is_ok(result) else None,
                    "error": result.err.serialize() if not is_ok(result) else None,
                }
                await msg.respond(json.dumps(raw_response).encode("utf-8"))
            elif subscriber.js_stream is not None:
                if is_ok(result):
                    await msg.ack()
                else:
                    await msg.nak(delay=5)
        except Exception as e:
            print(InternalError.from_exception(e))

    return callback
