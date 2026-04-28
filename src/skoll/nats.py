import json
import typing as t
import collections.abc as c

from nats.aio.msg import Msg
from attrs import define, field
from nats.js.kv import KeyValue
from nats.js import JetStreamContext
from nats.aio.client import Client as NatsClient
from nats.aio.subscription import Subscription as NSubscription

from .config import SSL
from .result import Result, fail, ok, is_ok, is_fail
from .utils import call_with_dependencies, get_signature
from .exceptions import Error, InternalError, ValidationFailed
from .domain import Message, ID, RawMessage, Subscriber, Service, Mediator, KVStore, KVBucket, Object

__all__ = ["NatsMediator"]


@define(kw_only=True, slots=True)
class NatsMediator(Mediator):

    creds: str
    servers: list[str]
    default_req_timeout: int = 30
    _bucket: KeyValue | None = None
    _js: JetStreamContext | None = None
    nc: NatsClient = field(init=False, factory=lambda: NatsClient())
    subscriptions: dict[str, list[NSubscription]] = field(factory=dict)

    @property
    def js(self) -> JetStreamContext:

        if self._js is None:
            raise InternalError(debug={"message": "JetStream context is not initialized"})
        return self._js

    @property
    def bucket(self) -> KeyValue:
        if self._bucket is None:
            raise InternalError(debug={"message": "KV bucket is not initialized"})
        return self._bucket

    @property
    @t.override
    def kv(self) -> KVStore:
        return NatsKVStore(bucket=self.bucket)

    @t.override
    async def subscribe(self, service: Service) -> ID:
        if not self.nc.is_connected:
            raise InternalError(debug={"message": "Attempt to subscribe before nats client is connected"})
        sub_id = ID()
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
    async def connect(self, kv_buckets: list[KVBucket] | None = None) -> None:
        try:
            if self.nc.is_connected or self.nc.is_reconnecting:
                return None
            await self.nc.connect(tls=SSL, servers=self.servers, max_reconnect_attempts=-1, user_credentials=self.creds)
            self._js = self.nc.jetstream()
            self._bucket = await self._js.create_key_value(bucket="skoll_kv_store", history=1)
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
            response = await self.nc.request(
                subject, json.dumps(payload).encode("utf-8"), timeout=self.default_req_timeout
            )
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


def get_payload(subscriber: Subscriber[t.Any], message: Message) -> Object | None:
    try:
        for param in get_signature(subscriber.callback):
            if param.name == "payload" and issubclass(param.annotation, Object):
                return message.unwrap_payload(param.annotation)
    except Exception:
        return None


async def run_callback(subscriber: Subscriber[t.Any], message: Message | RawMessage) -> Result[t.Any]:
    topic = message.name if isinstance(message, Message) else message.get("name")
    try:
        msg = get_message(subscriber.msg_type, message)
        cxt: dict[str, t.Any] = {
            subscriber.msg_arg: msg,
            "context": msg.context,
            "payload": get_payload(subscriber, msg),
        }
        return await call_with_dependencies(subscriber.callback, cxt)
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


@define(kw_only=True, slots=True)
class NatsKVStore(KVStore):

    bucket: KeyValue

    @t.override
    async def get(self, key: str) -> str | None:
        try:
            entry = await self.bucket.get(key)
            return entry.value.decode("utf-8") if entry.value else None
        except Exception:
            return None

    @t.override
    async def add(self, key: str, value: str, ttl: int | None = None) -> None:
        try:
            await self.bucket.create(key=key, value=value.encode("utf-8"), msg_ttl=ttl)
            return None
        except Exception as e:
            raise InternalError.from_exception(e, extra={"message": f"Failed to add key {key} in KV store"})

    @t.override
    async def update(self, key: str, value: str, ttl: int | None = None) -> None:
        try:
            await self.bucket.update(key=key, value=value.encode("utf-8"), msg_ttl=ttl)
            return None
        except Exception as e:
            raise InternalError.from_exception(e, extra={"message": f"Failed to update key {key} in KV store"})

    @t.override
    async def delete(self, key: str) -> None:
        try:
            await self.bucket.delete(key)
            return None
        except Exception as e:
            raise InternalError.from_exception(e, extra={"message": f"Failed to delete key {key} in KV store"})
