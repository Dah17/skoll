import typing as t

from skoll.domain import Message
from skoll.result import Result, fail, is_fail
from skoll.utils import call_with_dependencies
from skoll.application import Subscriber, RawMessage
from skoll.errors import Error, InternalError, ValidationFailed

__all__ = ["run_callback"]


async def run_callback(subscriber: Subscriber, message: Message | RawMessage) -> Result[t.Any]:
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


# def is_subscribed(subscriber: Subscriber, message: Message | RawMessage) -> bool:
#     topic = message.topic if isinstance(message, Message) else message.get("topic")
#     s = topic.split(".") if topic else []
#     p = subscriber.topic.split(".") if subscriber.topic else []

#     i = j = 0
#     while i < len(s) and j < len(p):
#         if j + 1 < len(p) and p[j + 1] == ">":
#             # Next token is '>', so this token must match exactly
#             if p[j] != "*" and p[j] != s[i]:
#                 return False
#             j += 2
#             i += 1
#             continue

#         if p[j] == ">":
#             return True

#         if p[j] == "*":
#             i += 1
#             j += 1
#             continue

#         if p[j] != s[i]:
#             return False

#         i += 1
#         j += 1

#     if i == len(s):
#         # Check remaining pattern tokens
#         while j < len(p):
#             if p[j] == ">":
#                 return True
#             if p[j] != "*":
#                 return False
#             j += 1
#         return True

#     # Subject has leftover tokens
#     return j < len(p) and p[j] == ">"
