
from django.http import FileResponse


async def get_tdf(request, tdf_name):
    """
    Handle GET requests for the TDF page.
    """
    
    return FileResponse(open(f"tdfs/{tdf_name}", "rb"), content_type="application/octet-stream")