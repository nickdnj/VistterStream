import os
import sys
from types import SimpleNamespace

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from backend.services import ptz_service


class _FakeMediaService:
    def __init__(self, tokens):
        self._tokens = tokens

    def GetProfiles(self):
        return [SimpleNamespace(token=token) for token in self._tokens]


class _FakePTZService:
    def __init__(self, goto_log, set_log):
        self._goto_log = goto_log
        self._set_log = set_log

    def create_type(self, name):
        return SimpleNamespace()

    def GotoPreset(self, request):
        self._goto_log.append(
            {
                "profile_token": getattr(request, "ProfileToken", None),
                "preset_token": getattr(request, "PresetToken", None),
            }
        )

    def SetPreset(self, request):
        self._set_log.append(
            {
                "profile_token": getattr(request, "ProfileToken", None),
                "preset_token": getattr(request, "PresetToken", None),
            }
        )
        return SimpleNamespace(PresetToken=None)


class _FakeCamera:
    def __init__(self, host, port, user, passwd):
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.xaddrs = {}
        self._goto_calls = []
        self._set_calls = []
        self._media_tokens = ["MEDIA_TOKEN_1"]

    def update_xaddrs(self):
        # Simulate device reporting PTZ endpoint
        self.xaddrs = {
            "http://www.onvif.org/ver20/ptz/wsdl": "http://device.local/onvif/ptz",
        }

    def create_ptz_service(self):
        return _FakePTZService(self._goto_calls, self._set_calls)

    def create_media_service(self):
        return _FakeMediaService(self._media_tokens)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio("asyncio")
async def test_move_to_preset_with_explicit_onvif_url(monkeypatch):
    # Ensure clean environment for the module under test
    monkeypatch.setenv("ONVIF_DEVICE_URL", "http://192.168.12.59:8899/onvif/device_service")
    monkeypatch.setenv("ONVIF_PTZ_URL", "http://192.168.12.59:8899/onvif/ptz")
    monkeypatch.setenv("PTZ_DEBUG", "1")

    fake_onvif_module = SimpleNamespace(
        client=SimpleNamespace(SERVICES={"ptz": {"ns": "http://www.onvif.org/ver20/ptz/wsdl"}})
    )
    monkeypatch.setitem(sys.modules, "onvif", fake_onvif_module)

    init_calls = []

    def _fake_camera_ctor(host, port, user, passwd):
        init_calls.append({"host": host, "port": port, "user": user, "passwd": passwd})
        return _FakeCamera(host, port, user, passwd)

    monkeypatch.setattr(ptz_service, "ONVIFCamera", _fake_camera_ctor)
    monkeypatch.setattr(ptz_service, "ONVIFError", Exception)

    service = ptz_service.PTZService()
    assert service._onvif_available is True

    moved = await service.move_to_preset(
        address="sunba.local",
        port=80,
        username="admin",
        password="very-secret",
        preset_token="PRESET_TOKEN_5",
    )

    assert moved is True

    # The explicit override should be used instead of the original host/port
    assert init_calls == [
        {"host": "192.168.12.59", "port": 8899, "user": "admin", "passwd": "very-secret"}
    ]

    fake_camera = service._camera_connections["192.168.12.59:8899"]
    assert fake_camera.xaddrs["http://www.onvif.org/ver20/ptz/wsdl"] == "http://192.168.12.59:8899/onvif/ptz"

    assert fake_camera._goto_calls == [
        {"profile_token": "MEDIA_TOKEN_1", "preset_token": "PRESET_TOKEN_5"}
    ]


@pytest.mark.anyio("asyncio")
async def test_set_preset_uses_provided_token(monkeypatch):
    monkeypatch.setenv("ONVIF_DEVICE_URL", "http://192.168.12.59:8899/onvif/device_service")
    monkeypatch.setenv("ONVIF_PTZ_URL", "http://192.168.12.59:8899/onvif/ptz")
    monkeypatch.setenv("PTZ_DEBUG", "1")

    fake_onvif_module = SimpleNamespace(
        client=SimpleNamespace(SERVICES={"ptz": {"ns": "http://www.onvif.org/ver20/ptz/wsdl"}})
    )
    monkeypatch.setitem(sys.modules, "onvif", fake_onvif_module)

    init_calls = []

    def _fake_camera_ctor(host, port, user, passwd):
        init_calls.append({"host": host, "port": port, "user": user, "passwd": passwd})
        return _FakeCamera(host, port, user, passwd)

    monkeypatch.setattr(ptz_service, "ONVIFCamera", _fake_camera_ctor)
    monkeypatch.setattr(ptz_service, "ONVIFError", Exception)

    service = ptz_service.PTZService()
    fake_camera = await service.get_onvif_camera("sunba.local", 80, "admin", "very-secret")

    token = await service.set_preset(
        address="sunba.local",
        port=80,
        username="admin",
        password="very-secret",
        preset_name="Preset1",
        preset_token="2",
    )

    assert token == "2"
    assert fake_camera._set_calls == [
        {"profile_token": "MEDIA_TOKEN_1", "preset_token": "2"}
    ]
