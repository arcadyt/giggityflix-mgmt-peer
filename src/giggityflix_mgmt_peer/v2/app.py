# app.py
import asyncio
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response  # Add the imports
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from giggityflix_mgmt_peer.v2.drive_pool.drive_detection.detection import get_all_physical_drives
from giggityflix_mgmt_peer.v2.drive_pool.ui.drive_dashboard import router as drives_router, create_react_artifact

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# Create application directories
def create_app_directories():
    """Create necessary directories for the application."""
    # Create templates directory
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)

    # Create the template file
    template_file = templates_dir / "drive_dashboard.html"
    if not template_file.exists():
        with open(template_file, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Giggityflix Drive Dashboard</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- React -->
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <script src="https://unpkg.com/lucide-react@latest"></script>
</head>
<body>
    <div id="react-root"></div>

    <!-- Our React component -->
    <script src="/drives/dashboard.js"></script>
    <script>
        // Mount the React component
        window.addEventListener('DOMContentLoaded', function() {
            const rootElement = document.getElementById('react-root');
            if (rootElement) {
                const root = ReactDOM.createRoot(rootElement);
                root.render(React.createElement(DriveDashboard));
            }
        });
    </script>
</body>
</html>""")

    # Create static directory
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)


# Create the FastAPI app
app = FastAPI(
    title="Giggityflix Management Peer v2",
    description="Drive pool management with physical drive detection",
    version="2.0.0"
)

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Include the drive dashboard router
app.include_router(drives_router)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    logger.warning("Static files directory not found")


# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to drive dashboard."""
    return templates.TemplateResponse(
        "drive_dashboard.html",
        {"request": request}
    )


# Create React artifact endpoint
@app.get("/drives/dashboard.js")
async def drive_dashboard_js():
    """Return the React drive dashboard component."""
    js_content = create_react_artifact()

    # Wrap the ReactJS code to make it work in the browser
    wrapped_js = """
(function() {
    'use strict';

    // Create global references to React components
    const React = window.React;
    const ReactDOM = window.ReactDOM;
    const lucide = window.lucide;

    // Destructure Lucide icons
    const { ChevronDown, ChevronUp, HardDrive, Database } = lucide;

""" + js_content + """

    // Expose the component globally
    window.DriveDashboard = DriveDashboard;
})();
"""

    return Response(content=wrapped_js, media_type="application/javascript")


# Application startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info("Initializing Giggityflix Management Peer v2")

    # Create necessary directories
    create_app_directories()

    # Pre-load drive information
    try:
        drives = get_all_physical_drives()
        logger.info(f"Detected {len(drives)} physical drives")
        for drive in drives:
            logger.info(f"Drive: {drive.get_drive_id()}, Size: {drive.get_formatted_size()}")
    except Exception as e:
        logger.error(f"Error detecting drives: {e}")


# Run the application
def start_app():
    """Start the application."""
    import uvicorn
    uvicorn.run(
        "app:app",  # Use this path if running from the same directory
        host="0.0.0.0",
        port=8080,
        reload=True
    )


if __name__ == "__main__":
    start_app()