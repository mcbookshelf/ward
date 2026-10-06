from platformdirs import user_cache_path

ADOPTIUM_API = "https://api.adoptium.net/v3"
FABRIC_API = "https://meta.fabricmc.net/v2"
MODRINTH_API = "https://api.modrinth.com/v2"
PACK_FORMATS = (
    "https://raw.githubusercontent.com/misode/mcmeta/refs/heads/summary/versions/data.json"
)
USER_AGENT = "mcbookshelf/ward (github.com/mcbookshelf/ward)"
FABRIC_INSTALLER = "1.1.1"
JAVA_VERSION = 25

CACHE_DIR = user_cache_path("mcward", appauthor=False)
JAVA_DIR = CACHE_DIR / "java" / str(JAVA_VERSION)

PROTOCOL_VERSION = 1

WARD_HOST = "127.0.0.1"
PID_FILE = "ward.pid"
PORT_FILE = "ward.port"
OUTPUT_FILE = "ward.log"

STARTUP_TIMEOUT = 120
SHUTDOWN_TIMEOUT = 15
STATUS_TIMEOUT = 10
SOCKET_CONNECT_TIMEOUT = 2
DOWNLOAD_TIMEOUT = 120
