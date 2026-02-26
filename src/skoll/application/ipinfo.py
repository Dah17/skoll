from attrs import define
from skoll.result import is_ok
from aiohttp import ClientSession
from skoll.utils import default_ssl
from skoll.domain import Object, CountryCode, Timezone, Currency

__all__ = ["IPInfo", "get_ip_info"]


@define(kw_only=True, slots=True, frozen=True)
class IPInfo(Object):

    timezone: Timezone
    currency: Currency
    city: str | None = None
    country_code: CountryCode
    region_code: str | None = None


async def get_ip_info(ip: str) -> IPInfo | None:
    try:
        async with ClientSession() as session:
            async with session.get(f"https://ipinfo.io/{ip}/json", ssl=default_ssl) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                raw = {
                    "city": data.get("city"),
                    "country_code": data.get("country"),
                    "region_code": data.get("region_code"),
                    "timezone": data.get("timezone", "UTC"),
                    "currency": data.get("currency", "EUR"),
                }
                res = IPInfo.create(raw)
                if is_ok(res):
                    return res.value
                return None
    except:
        return None
