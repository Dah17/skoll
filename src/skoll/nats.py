import json
import typing as t
import collections.abc as c

from ssl import SSLContext
from nats.aio.msg import Msg
from attrs import define, field
from nats.js.kv import KeyValue
from nats.js import JetStreamContext
from nats.aio.client import Client as NatsClient
from nats.aio.subscription import Subscription as NSubscription

from .result import Result, fail, ok, is_ok, is_fail
from .utils import call_with_dependencies, get_signature
from .exceptions import Error, InternalError, ValidationFailed
from .domain import Message, Ulid, ID, Subscriber, Service, Services, Mediator, KVStore, KVBucket, Object

__all__ = ["NatsMediator"]


@define(kw_only=True, slots=True)
class NatsMediator(Mediator):

    creds: str
    servers: list[str]
    ssl_cxt: SSLContext
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
    async def subscribe(self, services: Services | Service) -> ID:
        if not self.nc.is_connected:
            raise InternalError(debug={"message": "Attempt to subscribe before nats client is connected"})
        sub_id = Ulid()

        subscriptions: list[NSubscription] = []
        for subscriber in get_subscribers(services):
            if subscriber.js_stream is not None:
                sub = await self.js.subscribe(
                    manual_ack=True,
                    subject=subscriber.subject,
                    stream=subscriber.js_stream,
                    cb=wrap_callback(subscriber),
                    durable=subscriber.service_name,
                    queue=subscriber.service_name if subscriber.queued else None,
                )
            else:
                sub = await self.nc.subscribe(
                    subject=subscriber.subject,
                    cb=wrap_callback(subscriber),
                    queue=subscriber.service_name if subscriber.queued else "",
                )
            subscriptions.append(sub)
        self.subscriptions[sub_id.value] = subscriptions
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
            await self.nc.connect(
                tls=self.ssl_cxt, servers=self.servers, max_reconnect_attempts=-1, user_credentials=self.creds
            )
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
    async def publish(self, *msg: Message) -> None:
        for m in msg:
            await self.nc.publish(m.subject, json.dumps(m.serialize()).encode("utf-8"))

    @t.override
    async def request(self, msg: Message) -> Result[t.Any]:
        try:
            response = await self.nc.request(
                msg.subject, json.dumps(msg.serialize()).encode("utf-8"), timeout=self.default_req_timeout
            )
            raw_msg = json.loads(response.data.decode("utf-8"))
            if raw_msg.get("error") is not None:
                return fail(Error.from_dict(raw_msg["error"]))
            return ok(raw_msg.get("data"))
        except TimeoutError as e:
            return fail(InternalError.from_exception(e, extra={"message": f"Request timed out"}))
        except Exception as e:
            return fail(InternalError.from_exception(e))


def get_subscribers(services: Services | Service) -> list[Subscriber]:
    services_list = services.items if isinstance(services, Services) else [services]
    return [subscriber for service in services_list for subscriber in service.subscribers]


def get_payload(subscriber: Subscriber, message: Message) -> Object | None:
    for param in get_signature(subscriber.callback):
        if param.name == "payload" and issubclass(param.annotation, Object):
            res = param.annotation.create(message.payload.value)
            if is_fail(res):
                raise ValidationFailed(errors=res.err.errors)
            return res.value
    return None


async def run_callback(subscriber: Subscriber, message: Message) -> Result[t.Any]:
    try:
        cxt: dict[str, t.Any] = {
            "msg": message,
            "context": message.context,
            "payload": message.payload,
        }
        return await call_with_dependencies(subscriber.callback, cxt)
    except Error as err:
        return fail(err=err)
    except Exception as exc:
        return fail(err=InternalError.from_exception(exc, extra={"subject": message.subject, "message": message}))


def wrap_callback(subscriber: Subscriber) -> t.Callable[[Msg], c.Awaitable[None]]:
    async def callback(msg: Msg):
        try:
            data_res = Message.create(raw=json.loads(msg.data.decode("utf-8")))
            if is_fail(data_res):
                raise ValidationFailed(errors=data_res.err.errors)
            result = await run_callback(subscriber, data_res.value)
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
    async def list_keys(self, filters: list[str]) -> list[str]:
        try:
            return await self.bucket.keys(filters=filters)
        except Exception:
            return []

    @t.override
    async def get[T: Object](self, key: str, cls: type[T]) -> T | None:
        try:
            entry = await self.bucket.get(key)
            str_value = entry.value.decode("utf-8") if entry.value else None
            if str_value is None:
                return None
            res = cls.create(json.loads(str_value))
            if is_fail(res):
                return None
            return res.value
        except Exception:
            return None

    @t.override
    async def add(self, key: str, value: Object, ttl: int | None = None) -> None:
        try:
            str_value = json.dumps(value.serialize()).encode("utf-8")
            await self.bucket.create(key=key, value=str_value, msg_ttl=ttl)
            return None
        except Exception as e:
            raise InternalError.from_exception(e, extra={"message": f"Failed to add key {key} in KV store"})

    @t.override
    async def update(self, key: str, value: Object, ttl: int | None = None) -> None:
        try:
            str_value = json.dumps(value.serialize()).encode("utf-8")
            await self.bucket.update(key=key, value=str_value, msg_ttl=ttl)
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
