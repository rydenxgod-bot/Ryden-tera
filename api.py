from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, HTMLResponse
from playwright.async_api import async_playwright
import uvicorn
import re

app = FastAPI()

@app.get("/api")
async def get_terabox_data(url: str = Query(...)):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)

        # Wait for video element
        await page.wait_for_selector("video", timeout=10000)

        # Extract video link
        content = await page.content()
        video_match = re.search(r'src="(https://.*?\.terabox\.com.*?)"', content)
        thumb_match = re.search(r'poster="(https://[^"]+)"', content)
        name_match = re.search(r'fileName\s*=\s*"([^"]+)"', content)

        if not video_match:
            await browser.close()
            return JSONResponse({"status": "error", "message": "Video not found"})

        video_url = video_match.group(1)
        thumbnail = thumb_match.group(1) if thumb_match else ""
        file_name = name_match.group(1) if name_match else "Unknown.mp4"

        # Estimate size (not accurate without header check)
        file_size = "Unknown"
        file_type = "video/mp4"

        stream_url = f"https://{Request.scope['server'][0]}/stream?url={video_url}"

        await browser.close()
        return {
            "status": "success",
            "file_name": file_name,
            "file_size": file_size,
            "file_type": file_type,
            "thumbnail": thumbnail,
            "direct_download": video_url,
            "watch_url": stream_url
        }

@app.get("/stream")
async def stream_video(url: str):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Terabox Stream</title>
        <link href="https://vjs.zencdn.net/7.21.1/video-js.css" rel="stylesheet" />
        <style>
            body {{
                background-color: #121212;
                margin: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                color: white;
                font-family: Arial, sans-serif;
            }}
            .loading {{
                position: absolute;
                font-size: 22px;
                animation: pulse 1.5s infinite;
            }}
            @keyframes pulse {{
                0% {{ opacity: 0.3 }}
                50% {{ opacity: 1 }}
                100% {{ opacity: 0.3 }}
            }}
        </style>
    </head>
    <body>
        <div class="loading" id="loading">🔄 Retrieving video stream...</div>
        <video id="my-video" class="video-js" controls autoplay preload="auto" width="720" height="400" style="display:none">
            <source src="{url}" type="video/mp4" />
            Your browser does not support the video tag.
        </video>
        <script src="https://vjs.zencdn.net/7.21.1/video.min.js"></script>
        <script>
            const video = document.getElementById('my-video');
            video.addEventListener('loadeddata', () => {{
                document.getElementById('loading').style.display = 'none';
                video.style.display = 'block';
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
