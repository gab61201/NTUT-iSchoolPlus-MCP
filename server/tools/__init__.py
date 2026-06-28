from mcp.server.fastmcp import FastMCP

from nportal.session import SessionManager

mcp = FastMCP("ntut-ischoolplus-mcp")
session = SessionManager()

# Tool modules register themselves via @mcp.tool() on import
from . import auth
from . import semester
from . import timetable
from . import syllabus
from . import files
from . import videos
from . import bulletin
from . import notes
from . import homework
from . import calendar
from . import graduation

__all__ = ["mcp"]
