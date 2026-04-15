from tap_mapper.config import ApplicationConfig


class TapMapperApplicationRuntime:
    def __init__(self, application_config: ApplicationConfig) -> None:
        self._application_config = application_config

    def run(self) -> int:
        return 0


def main() -> int:
    return TapMapperApplicationRuntime(ApplicationConfig()).run()
