import typing as t
from json import loads
from attrs import define
from re import match as re_match
from aiohttp import ClientSession

from skoll.errors import Forbidden
from skoll.utils import sanitize_dict
from skoll.application import AuthzWriteChange, AuthzPrecondition, AuthzLookupResult, Authz


__all__ = ["SpiceDBAuthz"]


TUPLE_PATTERN = r"(?P<resource>.+?):(?P<resource_id>.*?)#(?P<relation>.*?)@(?P<subject>.*?):(?P<subject_id>.*)"


@define(frozen=True, kw_only=True)
class TupleObject:
    resource: str
    subject: str | None = None
    relation: str | None = None
    subject_id: str | None = None
    resource_id: str | None = None
    subject_relation: str | None = None


@define(kw_only=True, frozen=True, slots=True)
class SpiceDBAuthz(Authz):

    url: str
    token: str

    def make_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    @t.override
    async def write(self, changes: list[AuthzWriteChange], preconditions: list[AuthzPrecondition] | None = None) -> str:
        uri = self.url + "/v1/relationships/write"
        data = {"updates": get_changes(changes), "optionalAuthzPreconditions": get_preconditions(preconditions or [])}
        async with ClientSession() as session:
            async with session.post(uri, json=sanitize_dict(data), ssl=False, headers=self.make_headers()) as response:
                if response.status != 200:
                    print(await response.text())
                    raise ValueError(f"Failed to write changes {changes} with preconditions {preconditions}")
                return (await response.json()).get("writtenAt", {}).get("token", "")

    @t.override
    async def lookup(
        self, filter: str, cxt: dict[str, t.Any] | None = None, limit: int | None = None, cursor: str | None = None
    ) -> AuthzLookupResult:
        tuple_obj = tuple_from(filter)
        if not tuple_obj:
            raise ValueError(f"Invalid tuple: {filter}")

        data: dict[str, t.Any] = {
            "context": cxt,
            "consistency": {"minimizeLatency": True},
            "optionalCursor": {"token": cursor} if cursor else None,
        }
        uri = self.url + "/v1/permissions"
        if tuple_obj.subject_id is not None:  # ResourceLookup
            uri += "/resources"
            data["optionalLimit"] = limit
            data["permission"] = tuple_obj.relation
            data["resourceObjectType"] = tuple_obj.resource
            data["subject"] = {
                "optionalRelation": tuple_obj.subject_relation,
                "object": {"objectType": tuple_obj.subject, "objectId": tuple_obj.subject_id},
            }
        else:  # SubjectLookup
            uri += "/subjects"
            data["optionalConcreteLimit"] = limit
            data["permission"] = tuple_obj.relation
            data["subjectObjectType"] = tuple_obj.subject
            data["optionalSubjectRelation"] = tuple_obj.subject_relation
            data["resource"] = {"objectType": tuple_obj.resource, "objectId": tuple_obj.resource_id}

        async with ClientSession() as session:
            async with session.post(uri, json=sanitize_dict(data), ssl=False, headers=self.make_headers()) as response:
                if response.status != 200:
                    raise Exception(
                        f"Failed to lookup  {filter} with context {cxt} and limit {limit} and cursor {cursor}. status code: {response.status}"
                    )
                lines = [loads(line) for line in (await response.text()).split("\n")[:-1]]
                id_key = "resourceObjectId" if tuple_obj.subject_id is not None else "subjectObjectId"
                return AuthzLookupResult(
                    ids=[line.get("result", {}).get(id_key, "") for line in lines],
                    cursor=lines[-1].get("result", {}).get("afterResultCursor", {}).get("token"),
                )

    @t.override
    async def check(self, tuple: str, cxt: dict[str, t.Any] | None = None) -> None:
        uri = self.url + "/v1/permissions/check"
        tuple_obj = tuple_from(tuple)
        if not tuple_obj:
            raise ValueError(f"Invalid tuple: {tuple}")

        data: dict[str, t.Any] = {
            "context": cxt,
            "permission": tuple_obj.relation,
            "consistency": {"minimizeLatency": True},
            "resource": {"objectType": tuple_obj.resource, "objectId": tuple_obj.resource_id},
            "subject": {
                "optionalRelation": tuple_obj.subject_relation,
                "object": {"objectType": tuple_obj.subject, "objectId": tuple_obj.subject_id},
            },
        }

        async with ClientSession() as session:
            async with session.post(uri, json=sanitize_dict(data), ssl=False, headers=self.make_headers()) as response:
                res = await response.json()
                if res.get("permissionship", "") != "PERMISSIONSHIP_HAS_PERMISSION":
                    raise Forbidden(debug={"tuple": tuple, "context": cxt})
                return None


def tuple_from(tuple_str: str) -> TupleObject | None:
    match = re_match(TUPLE_PATTERN, tuple_str)
    if match:
        data = match.groupdict()
        subject_id = data["subject_id"].split("#")
        data["subject_id"] = subject_id[0]
        data["subject_relation"] = subject_id[1] if len(subject_id) > 1 else None
        return TupleObject(
            resource=data["resource"],
            subject_relation=data["subject_relation"],
            subject=data["subject"] if len(data["subject"]) > 0 else None,
            relation=data["relation"] if len(data["relation"]) > 0 else None,
            subject_id=data["subject_id"] if len(data["subject_id"]) > 0 else None,
            resource_id=data["resource_id"] if len(data["resource_id"]) > 0 else None,
        )
    return None


def get_changes(changes: list[AuthzWriteChange]) -> list[dict[str, t.Any]]:
    updates = []
    for ch in changes:
        tuple_obj = tuple_from(ch[1])
        if not tuple_obj:
            raise ValueError(f"Invalid tuple: {ch[1]}")
        update: dict[str, t.Any] = {
            "operation": "OPERATION_DELETE" if ch[0] == "DELETE" else "OPERATION_TOUCH",
            "relationship": {
                "relation": tuple_obj.relation,
                "resource": {"objectType": tuple_obj.resource, "objectId": tuple_obj.resource_id},
                "subject": {
                    "optionalRelation": tuple_obj.subject_relation,
                    "object": {"objectType": tuple_obj.subject, "objectId": tuple_obj.subject_id},
                },
                "optionalExpiresAt": ch[3].iso_format if ch[3] else None,
                "optionalCaveat": {"caveatName": ch[2][0], "context": ch[2][1]} if ch[2] else None,
            },
        }
        updates.append(update)
    return updates


def get_preconditions(precondition: list[AuthzPrecondition]) -> list[dict[str, t.Any]]:
    return [{"operation": f"OPERATION_{pr[0]}", "filter": relation_filter_from(pr[1])} for pr in precondition]


def relation_filter_from(tuple: str) -> dict[str, t.Any]:
    tuple_obj = tuple_from(tuple)
    if not tuple_obj:
        raise ValueError(f"Invalid tuple: {tuple}")
    return {
        "resourceType": tuple_obj.resource,
        "optionalResourceId": tuple_obj.resource_id,
        "optionalResourceIdPrefix": tuple_obj.resource_id,
        "optionalRelation": tuple_obj.relation,
        "optionalSubjectFilter": {
            "subjectType": tuple_obj.subject,
            "optionalSubjectId": tuple_obj.subject_id,
            "optionalRelation": {"relation": tuple_obj.subject_relation},
        },
    }
