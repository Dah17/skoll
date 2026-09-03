import json
import logging
import typing as t
import collections.abc as c

from ssl import SSLContext
from nats.aio.msg import Msg
from attrs import define, field
from nats.js.kv import KeyValue
from nats.js import JetStreamContext
from nats.js.api import ConsumerConfig
from nats.js.errors import NotFoundError
from nats.aio.client import Client as NatsClient
from nats.aio.subscription import Subscription as NSubscription

from .result import Result, fail, ok, is_ok, is_fail
from .exceptions import Error, InternalError, InvalidField, ValidationFailed
from .utils import call_with_dependencies, get_signature, safe_async_call, serialize
from .domain import Message, Ulid, ID, Subscriber, Service, Services, Mediator, KVStore, KVBucket, Object

__all__ = ["NatsMediator"]

logger = logging.getLogger("skoll.nats")

NAK_DELAY = 5
TERMINAL_STATUSES = frozenset({400, 422})


@define(kw_only=True, slots=True)
class NatsMediator(Mediator):

    creds: str
    servers: list[str]
    ssl_cxt: SSLContext
    default_req_timeout: int = 30
    _js: JetStreamContext | None = None
    default_bucket: str = "skoll_kv_store"
    _buckets: dict[str, KeyValue] = field(factory=dict)
    nc: NatsClient = field(init=False, factory=lambda: NatsClient())
    subscriptions: dict[str, list[NSubscription]] = field(factory=dict)

    @property
    def js(self) -> JetStreamContext:

        if self._js is None:
            raise InternalError(debug={"message": "JetStream context is not initialized"})
        return self._js

    def bucket(self, name: str) -> KeyValue:
        bucket = self._buckets.get(name)
        if bucket is None:
            raise InternalError(debug={"message": f"KV bucket '{name}' is not initialized", "bucket": name})
        return bucket

    @property
    @t.override
    def kv(self) -> KVStore:
        return self.store(self.default_bucket)

    @t.override
    def store(self, bucket: str) -> KVStore:
        return NatsKVStore(bucket=self.bucket(bucket))

    @t.override
    async def subscribe(self, services: Services | Service) -> ID:
        if not self.nc.is_connected:
            raise InternalError(debug={"message": "Attempt to subscribe before nats client is connected"})
        sub_id = Ulid()

        subscriptions: list[NSubscription] = []
        for subscriber in get_subscribers(services):
            if subscriber.js_stream is not None:
                await self.sync_consumer(subscriber)
                sub = await self.js.subscribe(
                    manual_ack=True,
                    subject=subscriber.subject,
                    stream=subscriber.js_stream,
                    cb=wrap_callback(subscriber),
                    durable=subscriber.durable,
                    config=consumer_config(subscriber),
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

    async def sync_consumer(self, subscriber: Subscriber) -> None:
        """
        Align an already existing durable consumer with the subscriber configuration.

        `js.subscribe` only applies the consumer config when it has to create the consumer, so without
        this an existing durable would silently keep the settings it was first created with.
        """
        if subscriber.max_deliver is None or subscriber.js_stream is None:
            return None
        try:
            info = await self.js.consumer_info(subscriber.js_stream, subscriber.durable)
        except NotFoundError:
            return None
        if info.config.max_deliver == subscriber.max_deliver:
            return None
        try:
            config = info.config.evolve(max_deliver=subscriber.max_deliver)
            await self.js.add_consumer(subscriber.js_stream, config=config)
        except Exception as e:
            logger.warning(
                "Failed to update max_deliver of consumer %s on stream %s: %s",
                subscriber.service_name,
                subscriber.js_stream,
                e,
            )
        return None

    @t.override
    async def unsubscribe(self, id: ID) -> None:
        try:
            subscriptions = self.subscriptions.get(id.value, [])
            for sub in subscriptions:
                await sub.unsubscribe(limit=0)
            del self.subscriptions[id.value]
        except Exception as e:
            raise InternalError.from_exception(e) from e

    @t.override
    async def connect(self, kv_buckets: list[KVBucket] | None = None) -> None:
        try:
            if self.nc.is_connected or self.nc.is_reconnecting:
                return None
            await self.nc.connect(
                tls=self.ssl_cxt, servers=self.servers, max_reconnect_attempts=-1, user_credentials=self.creds
            )
            self._js = self.nc.jetstream()
            for kb in [KVBucket(key=self.default_bucket), *(kv_buckets or [])]:
                if kb.key in self._buckets:
                    continue
                self._buckets[kb.key] = await self.js.create_key_value(bucket=kb.key, history=kb.history, ttl=kb.ttl)
            return None
        except Exception as e:
            raise InternalError.from_exception(e) from e

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
            return fail(InternalError.from_exception(e, extra={"message": "Request timed out"}))
        except Exception as e:
            return fail(InternalError.from_exception(e))


def get_subscribers(services: Services | Service) -> list[Subscriber]:
    services_list = services.items if isinstance(services, Services) else [services]
    return [
        subscriber.on_subject(subject)
        for service in services_list
        for subscriber in service.subscribers
        for subject in subscriber.every_subject()
    ]


async def run_callback(subscriber: Subscriber, message: Message) -> Result[t.Any]:
    try:
        context: dict[str, t.Any] = {"msg": message}
        for param in get_signature(subscriber.callback):
            payload_key = subscriber.payload_key or "payload"
            if param.name == payload_key and issubclass(param.annotation, Object):
                res = param.annotation.create(message.payload.value)
                if is_fail(res):
                    raise ValidationFailed(errors=res.err.errors)
                context.update({payload_key: res.value})
            if param.name == "cxt" and issubclass(param.annotation, Object):
                res = param.annotation.create(message.cxt.value)
                if is_fail(res):
                    errs = [e.serialize() for e in res.err.errors]
                    raise InternalError(debug={"message": "Failed to create context object", "errors": errs})
                context.update({"cxt": res.value})
        return await call_with_dependencies(subscriber.callback, context)
    except Error as err:
        logger.error("Error while processing message on subject %s: %s", message.subject, err)
        return fail(err=err)
    except Exception as exc:
        return fail(err=InternalError.from_exception(exc, extra={"subject": message.subject, "message": message}))


def parse_message(msg: Msg) -> Result[Message]:
    try:
        res = Message.create(raw=json.loads(msg.data.decode("utf-8")))
        if is_fail(res):
            return fail(ValidationFailed(errors=res.err.errors or [res.err]))
        return ok(res.value)
    except Exception as e:
        return fail(ValidationFailed(errors=[InvalidField(field="data", hints={"error": str(e)})]))


def is_terminal(err: Error) -> bool:
    """
    Whether an error makes a message poisonous, meaning no redelivery will ever succeed.
    """
    return isinstance(err, ValidationFailed) or err.status in TERMINAL_STATUSES


async def settle(msg: Msg, result: Result[t.Any]) -> None:
    if is_ok(result):
        await msg.ack()
    elif is_terminal(result.err):
        logger.error("Terminating message on subject %s: %s", msg.subject, result.err.serialize())
        await msg.term()
    else:
        await msg.nak(delay=NAK_DELAY)


def wrap_callback(subscriber: Subscriber) -> t.Callable[[Msg], c.Awaitable[None]]:
    async def callback(msg: Msg):
        try:
            data_res = parse_message(msg)
            result = data_res if is_fail(data_res) else await run_callback(subscriber, data_res.value)
            if subscriber.will_reply:
                raw_res: dict[str, t.Any] = {"data": None, "error": None}
                if is_ok(result):
                    raw_res["data"] = serialize(result.value)
                else:
                    raw_res["error"] = result.err.serialize()
                await msg.respond(json.dumps(raw_res).encode("utf-8"))
            elif subscriber.js_stream is not None:
                await settle(msg, result)
            elif is_fail(result):
                logger.error("Failed to process message on subject %s: %s", msg.subject, result.err.serialize())
        except Exception as e:
            logger.exception("Unhandled error in NATS message callback: %s", e)

    return callback


def consumer_config(subscriber: Subscriber) -> ConsumerConfig | None:
    if subscriber.max_deliver is None:
        return None
    return ConsumerConfig(max_deliver=subscriber.max_deliver)


@define(kw_only=True, slots=True)
class NatsKVStore(KVStore):

    bucket: KeyValue

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
    async def list[T: Object](self, filters: list[str], cls: type[T]) -> list[T]:
        keys = await safe_async_call(lambda: self.bucket.keys(filters=filters), default=[])
        items: list[T] = []
        for key in keys:
            item = await self.get(key, cls)
            if item is not None:
                items.append(item)
        return items

    @t.override
    async def put(self, key: str, value: Object, ttl: int | None = None) -> None:
        try:
            data = json.dumps(value.serialize()).encode("utf-8")
            if ttl is None:
                await self.bucket.put(key=key, value=data)
            else:
                await safe_async_call(self.bucket.delete, key=key)
                await self.bucket.create(key=key, value=data, msg_ttl=ttl)
        except Exception as e:
            logger.error("Failed to put key %s in KV store: %s", key, e)
            raise InternalError.from_exception(e, extra={"message": f"Failed to put key {key} in KV store"}) from e

    @t.override
    async def delete(self, key: str) -> None:
        try:
            await self.bucket.delete(key)
        except Exception as e:
            raise InternalError.from_exception(e, extra={"message": f"Failed to delete key {key} in KV store"}) from e
