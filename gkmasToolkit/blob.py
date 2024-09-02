from .utils import Logger, determine_subdir
from .crypt import GkmasDeobfuscator
from .const import (
    GKMAS_OBJECT_SERVER,
    UNITY_SIGNATURE,
)

import requests
from hashlib import md5
from pathlib import Path


logger = Logger()


class GkmasResource:

    def __init__(self, info: dict):

        self.id = info["id"]
        self.name = info["name"]
        self.size = info["size"]
        self.state = info["state"]  # unused
        self.md5 = info["md5"]
        self.objectName = info["objectName"]
        self.__idname = f"[{self.id:04}] '{self.name}'"

    def __repr__(self):
        return f"<GkmasResource {self.__idname}>"

    def download(self, path: str):

        path = self._download_path(path)
        if path.exists():
            logger.warning(f"{self.__idname} already exists")
            return

        plain = self._download_bytes()
        path.write_bytes(plain)
        logger.success(f"{self.__idname} downloaded")

    def _download_path(self, path: str) -> Path:

        # don't expect the client to import pathlib in advance
        path = Path(path)

        if path.suffix == "":  # is directory
            path = path / determine_subdir(self.name) / self.name

        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _download_bytes(self) -> bytes:

        url = f"{GKMAS_OBJECT_SERVER}/{self.objectName}"
        response = requests.get(url)

        # We're being strict here by aborting the download process
        # if any of the sanity checks fail, in order to avoid corrupted output.
        # The client can always retry (just ignore the "file already exists" warnings).

        if response.status_code != 200:
            logger.error(f"{self.__idname} download failed")
            return b""

        if len(response.content) != self.size:
            logger.error(f"{self.__idname} has invalid size")
            return b""

        if md5(response.content).hexdigest() != self.md5:
            logger.error(f"{self.__idname} has invalid MD5 hash")
            return b""

        return response.content


class GkmasAssetBundle(GkmasResource):

    def __init__(self, info: dict):

        super().__init__(info)
        self.name = info["name"] + ".unity3d"
        self.crc = info["crc"]  # unused (for now)
        self.__idname = f"[{self.id:04}] '{self.name}'"

    def __repr__(self):
        return f"<GkmasAssetBundle {self.__idname}>"

    def download(self, path: str):

        path = self._download_path(path)
        if path.exists():
            logger.warning(f"{self.__idname} already exists")
            return

        cipher = self._download_bytes()

        if cipher[: len(UNITY_SIGNATURE)] == UNITY_SIGNATURE:
            path.write_bytes(cipher)
            logger.success(f"{self.__idname} downloaded")
        else:
            deobfuscator = GkmasDeobfuscator(self.name.replace(".unity3d", ""))
            plain = deobfuscator.decrypt(cipher)
            if plain[: len(UNITY_SIGNATURE)] == UNITY_SIGNATURE:
                path.write_bytes(plain)
                logger.success(f"{self.__idname} downloaded and deobfuscated")
            else:
                path.write_bytes(cipher)
                logger.warning(f"{self.__idname} downloaded but LEFT OBFUSCATED")
                # Things can happen...
                # So unlike _download_bytes() in the parent class,
                # here we don't raise an error and abort.
