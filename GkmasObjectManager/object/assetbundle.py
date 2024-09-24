"""
assetbundle.py
GkmasAssetBundle downloading and deobfuscation.
"""

from .resource import GkmasResource
from ._obfus import GkmasDeobfuscator
from ..utils import Logger
from ..const import (
    CHARACTER_ABBREVS,
    DEFAULT_DOWNLOAD_PATH,
    GKMAS_OBJECT_SERVER,
    GKMAS_UNITY_VERSION,
    UNITY_SIGNATURE,
    IMG_RESIZE_ARGTYPE,
)

import re
import requests
import UnityPy
from hashlib import md5
from pathlib import Path
from typing import Union, Tuple
from PIL import Image


logger = Logger()
UnityPy.config.FALLBACK_UNITY_VERSION = GKMAS_UNITY_VERSION


class GkmasAssetBundle(GkmasResource):
    """
    An assetbundle. Class inherits from GkmasResource.

    Attributes:
        All attributes from GkmasResource, plus
        name (str): Human-readable name, appended with '.unity3d'.
        crc (int): CRC checksum, unused for now (since scheme is unknown).

    Methods:
        download(
            path: str = DEFAULT_DOWNLOAD_PATH,
            categorize: bool = True,
            extract_img: bool = True,
            img_format: str = "png",
            img_resize: Union[None, str, Tuple[int, int]] = None,
        ) -> None:
            Downloads and deobfuscates the assetbundle to the specified path.
            Also extracts a single image from each bundle with type 'img'.
    """

    from ._download import _download_path, _download_bytes, _determine_subdir
    from ._export_img import _export_img

    def __init__(self, info: dict):
        """
        Initializes an assetbundle with the given information.
        Usually called from GkmasManifest.

        Args:
            info (dict): An info dictionary, extracted from protobuf.
                Must contain the following keys: id, name, objectName, size, md5, state, crc.
        """

        super().__init__(info)
        self.name = info["name"] + ".unity3d"
        self.crc = info["crc"]  # unused (for now)
        self._idname = f"AB[{self.id:05}] '{self.name}'"

    def __repr__(self):
        return f"<GkmasAssetBundle {self._idname}>"

    def download(
        self,
        path: str = DEFAULT_DOWNLOAD_PATH,
        categorize: bool = True,
        extract_img: bool = True,
        img_format: str = "png",
        img_resize: IMG_RESIZE_ARGTYPE = None,
    ):
        """
        Downloads and deobfuscates the assetbundle to the specified path.

        Args:
            path (str) = DEFAULT_DOWNLOAD_PATH: A directory or a file path.
                If a directory, subdirectories are auto-determined based on the assetbundle name.
            categorize (bool) = True: Whether to put the downloaded object into subdirectories.
                If False, the object is directly downloaded to the specified 'path'.
            extract_img (bool) = True: Whether to extract a single image from assetbundles of type 'img'.
                If False, 'img_.*\\.unity3d' is downloaded as is.
            img_format (str) = 'png': Image format for extraction. Case-insensitive.
                Effective only when 'extract_img' is True.
                Valid options are checked by PIL.Image.save() and are not enumerated.
            img_resize (Union[None, str, Tuple[int, int]]) = None: Image resizing argument.
                If None, image is downloaded as is.
                If str, string must contain exactly one ':' and image is resized to the specified ratio.
                If Tuple[int, int], image is resized to the specified exact dimensions.
        """

        path = self._download_path(path, categorize)
        if path.exists():
            logger.warning(f"{self._idname} already exists")
            return

        cipher = self._download_bytes()

        if cipher[: len(UNITY_SIGNATURE)] == UNITY_SIGNATURE:
            self._export_img(path, cipher, extract_img, img_format, img_resize)
            logger.success(f"{self._idname} downloaded")
        else:
            deobfuscator = GkmasDeobfuscator(self.name.replace(".unity3d", ""))
            plain = deobfuscator.deobfuscate(cipher)
            if plain[: len(UNITY_SIGNATURE)] == UNITY_SIGNATURE:
                self._export_img(path, plain, extract_img, img_format, img_resize)
                logger.success(f"{self._idname} downloaded and deobfuscated")
            else:
                path.write_bytes(cipher)
                logger.warning(f"{self._idname} downloaded but LEFT OBFUSCATED")
                # Unexpected things may happen...
                # So unlike _download_bytes() in the parent class,
                # here we don't raise an error and abort.
