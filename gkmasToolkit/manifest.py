import json
from google.protobuf.json_format import MessageToJson
from pathlib import Path

from .crypt import AESDecryptor
from .utils import GKMAS_OCTOCACHE_KEY, GKMAS_OCTOCACHE_IV
from .octodb_pb2 import Database


class GkmasManifest:

    def __init__(
        self,
        path: str,
        key: str = GKMAS_OCTOCACHE_KEY,
        iv: str = GKMAS_OCTOCACHE_IV,
    ):

        decryptor = AESDecryptor(key, iv)
        ciphertext = Path(path).read_bytes()
        plaintext = decryptor.decrypt(ciphertext)
        self.raw = plaintext[16:]  # trim md5 hash

        protodb = Database()
        protodb.ParseFromString(self.raw)
        self.revision = protodb.revision
        logger.info(f"Manifest revision: {self.revision}")

        self.jdict = json.loads(MessageToJson(protodb))

    def export(self, path: str):
        # dispatcher

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        if path.is_dir():
            self._export_protodb(path / f"manifest_v{self.revision}")
            self._export_json(path / f"manifest_v{self.revision}.json")
            self._export_csv(path / f"manifest_v{self.revision}.csv")

        else:
            if path.suffix == ".json":
                self._export_json(path)
            elif path.suffix == ".csv":
                self._export_csv(path)
            else:
                self._export_protodb(path)

    def _export_protodb(self, path: Path):
        try:
            path.write_bytes(self.raw)
            logger.success(f"ProtoDB has been written into {path}.")
        except:
            logger.error(f"Failed to write ProtoDB into {path}.", fatal=True)

    def _export_json(self, path: Path):
        try:
            path.write_text(json.dumps(self.jdict, sort_keys=True, indent=4))
            logger.success(f"JSON has been written into {path}.")
        except:
            logger.error(f"Failed to write JSON into {path}.", fatal=True)

    def _export_csv(self, path: Path):
        raise NotImplementedError("CSV export is not yet implemented.")
