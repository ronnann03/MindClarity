"""Gestor de perfiles de usuario con persistencia JSON.

Guarda y carga perfiles con preferencias personalizadas:
nombre, voz, idioma, pantalla preferida, etc.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


@dataclass
class UserProfile:
    """Perfil de usuario con preferencias personalizadas."""
    name: str
    voice_id: str = "EXAVITQu4vr4xnSDxMaL"
    language: str = "auto"
    preferred_screen: int = 0
    assistant_name: str = "YU"
    temperature: float = 0.7
    custom_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convierte el perfil a diccionario."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> UserProfile:
        """Crea un perfil desde un diccionario."""
        return cls(**data)


class ProfileManager:
    """Gestor de perfiles persistidos en archivo JSON."""

    PROFILES_FILE = BASE_DIR / ".profiles.json"

    @classmethod
    def load_profiles(cls) -> dict[str, UserProfile]:
        """Carga todos los perfiles desde el archivo."""
        if not cls.PROFILES_FILE.exists():
            return {}

        try:
            with open(cls.PROFILES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {name: UserProfile.from_dict(profile) for name, profile in data.items()}
        except (json.JSONDecodeError, IOError):
            return {}

    @classmethod
    def save_profiles(cls, profiles: dict[str, UserProfile]) -> None:
        """Guarda todos los perfiles en el archivo."""
        data = {name: profile.to_dict() for name, profile in profiles.items()}
        with open(cls.PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def create_profile(cls, name: str, **kwargs) -> UserProfile:
        """Crea un nuevo perfil."""
        profiles = cls.load_profiles()
        if name in profiles:
            raise ValueError(f"El perfil '{name}' ya existe.")

        profile = UserProfile(name=name, **kwargs)
        profiles[name] = profile
        cls.save_profiles(profiles)
        return profile

    @classmethod
    def get_profile(cls, name: str) -> UserProfile | None:
        """Obtiene un perfil por nombre."""
        profiles = cls.load_profiles()
        return profiles.get(name)

    @classmethod
    def update_profile(cls, name: str, **kwargs) -> UserProfile | None:
        """Actualiza un perfil existente."""
        profiles = cls.load_profiles()
        if name not in profiles:
            return None

        profile = profiles[name]
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profiles[name] = profile
        cls.save_profiles(profiles)
        return profile

    @classmethod
    def delete_profile(cls, name: str) -> bool:
        """Elimina un perfil."""
        profiles = cls.load_profiles()
        if name not in profiles:
            return False

        del profiles[name]
        cls.save_profiles(profiles)
        return True

    @classmethod
    def list_profiles(cls) -> list[str]:
        """Lista los nombres de todos los perfiles."""
        profiles = cls.load_profiles()
        return list(profiles.keys())

    @classmethod
    def ensure_default_profile(cls) -> UserProfile:
        """Asegura que existe un perfil por defecto."""
        profiles = cls.load_profiles()
        if "Defecto" in profiles:
            return profiles["Defecto"]

        return cls.create_profile(
            "Defecto",
            voice_id="EXAVITQu4vr4xnSDxMaL",
            language="auto",
            preferred_screen=0,
            assistant_name="YU"
        )
