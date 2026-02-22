import typing as t

from skoll.application import Subscriber
from skoll.domain import Message, RawMessage
from skoll.result import Result, fail, is_fail
from skoll.utils import call_with_dependencies
from skoll.errors import Error, InternalError, ValidationFailed

__all__ = ["run_callback"]


async def run_callback(subscriber: Subscriber[t.Any], message: Message | RawMessage) -> Result[t.Any]:
    topic = message.name if isinstance(message, Message) else message.get("name")
    try:
        msg = get_message(subscriber.msg_type, message)
        return await call_with_dependencies(subscriber.callback, {subscriber.msg_arg: msg})
    except Error as err:
        return fail(err=err)
    except Exception as exc:
        return fail(err=InternalError.from_exception(exc, extra={"subject": topic, "message": message}))


def get_message(cls: type[Message], message: Message | RawMessage) -> Message:
    if isinstance(message, Message):
        return message
    res = cls.create(raw=message)
    if is_fail(res):
        raise ValidationFailed(errors=res.err.errors)

    return res.value
