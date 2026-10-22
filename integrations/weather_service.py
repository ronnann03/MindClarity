"""Servicio de clima usando wttr.in (sin API key) o OpenWeatherMap."""
from __future__ import annotations

import httpx
from pydantic import BaseModel

from config.settings import settings
from core.logger import log


class WeatherInfo(BaseModel):
    """Información estructurada del clima."""

    city: str
    temperature: float
    description: str
    humidity: int = 0
    wind_speed: float = 0.0

    def __str__(self) -> str:
        return (
            f"En {self.city} hay {self.description}, {self.temperature:.0f}°C, "
            f"humedad {self.humidity}% y viento a {self.wind_speed:.0f} km/h."
        )


class WeatherService:
    """Obtiene el clima de una ciudad."""

    async def get_weather(self, city: str = "", **_: object) -> str:
        """Devuelve un resumen legible del clima de `city`."""
        city = city or "tu ubicación"
        info = await self._fetch(city)
        return str(info) if info else f"No pude obtener el clima de {city}."

    async def _fetch(self, city: str) -> WeatherInfo | None:
        # Preferir OpenWeatherMap si hay API key; si no, wttr.in.
        if settings.openweather_api_key:
            info = await self._openweather(city)
            if info:
                return info
        return await self._wttr(city)

    async def _wttr(self, city: str) -> WeatherInfo | None:
        import urllib.parse
        try:
            location = urllib.parse.quote(city)
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://wttr.in/{location}",
                    params={"format": "j1"},
                    headers={"User-Agent": "curl/8"},
                )
                resp.raise_for_status()
                data = resp.json()
            current = data["current_condition"][0]
            return WeatherInfo(
                city=city,
                temperature=float(current["temp_C"]),
                description=current["lang_es"][0]["value"] if "lang_es" in current
                else current["weatherDesc"][0]["value"],
                humidity=int(current["humidity"]),
                wind_speed=float(current["windspeedKmph"]),
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Error consultando wttr.in: {}", exc)
            return None

    async def _openweather(self, city: str) -> WeatherInfo | None:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "q": city,
                        "appid": settings.openweather_api_key,
                        "units": "metric",
                        "lang": "es",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            return WeatherInfo(
                city=data.get("name", city),
                temperature=data["main"]["temp"],
                description=data["weather"][0]["description"],
                humidity=data["main"]["humidity"],
                wind_speed=data["wind"]["speed"] * 3.6,
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Error consultando OpenWeatherMap: {}", exc)
            return None


weather_service = WeatherService()
