from ic_python_db import Entity, OneToMany, OneToOne, String, TimestampedMixin
from ic_python_logging import get_logger

logger = get_logger("entity.codex")


class Codex(Entity, TimestampedMixin):
    name = String()
    url = String()  # Optional URL for downloadable code
    checksum = String()  # Optional SHA-256 checksum for verification
    calls = OneToMany("Call", "codex")
    courts = OneToMany("Court", "codex")
    federation = OneToOne("Realm", "federation_codex")
    __alias__ = "name"

    @property
    def code(self):
        """Read codex content from the persistent filesystem."""
        # Return pending code if name hasn't been set yet
        pending = getattr(self, '_pending_code', None)
        if pending is not None:
            return pending
        if self.name:
            try:
                with open(f"/{self.name}", "r") as f:
                    return f.read()
            except (FileNotFoundError, OSError):
                pass
        return None

    @code.setter
    def code(self, value):
        """Write codex content to the persistent filesystem."""
        if value is not None:
            if self.name:
                try:
                    with open(f"/{self.name}", "w") as f:
                        f.write(str(value))
                except OSError as e:
                    logger.error(f"Failed to write codex '{self.name}' to filesystem: {e}")
                # Clear any pending code
                if hasattr(self, '_pending_code'):
                    del self._pending_code
            else:
                # Name not set yet — store temporarily until _save() flushes it
                self._pending_code = value

    def _save(self):
        """Override to flush pending code to filesystem after all properties are set."""
        pending = getattr(self, '_pending_code', None)
        if pending is not None and self.name:
            try:
                with open(f"/{self.name}", "w") as f:
                    f.write(str(pending))
            except OSError as e:
                logger.error(f"Failed to write codex '{self.name}' to filesystem: {e}")
            del self._pending_code
        return super()._save()
