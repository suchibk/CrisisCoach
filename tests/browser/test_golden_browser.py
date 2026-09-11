"""Opt-in real-browser checks: CRISIS_COACH_BROWSER_TESTS=1 pytest tests/browser."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
import pytest

pytestmark = pytest.mark.skipif(os.getenv("CRISIS_COACH_BROWSER_TESTS") != "1", reason="opt-in browser suite")
ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture
def browser_app(tmp_path):
    playwright=pytest.importorskip("playwright.sync_api")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1",0))
        port=listener.getsockname()[1]
    env={k:v for k,v in os.environ.items() if not k.startswith(("CRISIS_COACH_","ELEVENLABS_","LANGCHAIN_","LANGSMITH_"))}
    env["CRISIS_COACH_DATA_DIR"]=str(tmp_path / "live")
    env["PYTHONDONTWRITEBYTECODE"]="1"
    log=(tmp_path / "server.log").open("w")
    process=subprocess.Popen([sys.executable,"-B","-m","streamlit","run",str(ROOT / "src/crisis_coach/interfaces/streamlit_app.py"),"--server.headless=true","--server.address=127.0.0.1",f"--server.port={port}","--browser.gatherUsageStats=false"],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    try:
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if process.poll() is not None: raise RuntimeError("Streamlit exited; inspect server.log")
            try:
                with urlopen(f"http://127.0.0.1:{port}/_stcore/health",timeout=1) as response:
                    if response.status==200: break
            except OSError: time.sleep(.2)
        else: raise RuntimeError("Streamlit did not become ready")
        with playwright.sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(viewport={"width":1440,"height":1100},accept_downloads=True)
            page.set_default_timeout(15000)
            external=[]
            def route(request):
                if request.request.url.startswith((f"http://127.0.0.1:{port}/","data:","blob:")): request.continue_()
                else:
                    external.append(request.request.url)
                    request.abort()
            page.route("**/*",route)
            page.goto(f"http://127.0.0.1:{port}")
            page.get_by_test_id("stSidebar").get_by_text("Practice",exact=True).click()
            playwright.expect(page.get_by_text("PRACTICE · Synthetic scenario",exact=False)).to_be_visible()
            yield page,external,tmp_path,playwright.expect
            browser.close()
    finally:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill();process.wait(timeout=5)
        log.close()


def clear_gates(page,expect):
    page.get_by_role("button",name="No, I'm fine — shaken, but fine",exact=True).click()
    page.get_by_role("button",name="No, he's out of his car and looks okay",exact=True).click()
    page.get_by_role("button",name="Yes, I'm on the kerb",exact=True).click()
    expect(page.get_by_role("button",name="Simulate usable photo",exact=True)).to_be_visible()


def test_golden_browser_flow(browser_app):
    page,external,tmp_path,expect=browser_app
    screenshots=Path(os.getenv("CRISIS_COACH_SCREENSHOTS",str(tmp_path / "screenshots")))
    screenshots.mkdir(parents=True,exist_ok=True)
    expect(page.get_by_role("heading",name="Are you hurt anywhere?",exact=True)).to_be_visible()
    clear_gates(page,expect)
    page.get_by_role("button",name="He's getting back in his car",exact=True).click()
    page.get_by_role("button",name="Simulate rejected photo",exact=True).click()
    expect(page.get_by_role("heading",name="The image is too dark. Retake it only from a safe position.")).to_be_visible()
    page.get_by_role("button",name="Simulate usable photo",exact=True).click()
    expect(page.get_by_role("heading",name="Ask for the other driver insurance details. Record them only if they agree.")).to_be_visible()
    page.get_by_test_id("stMain").evaluate("e => e.scrollTop = 0")
    page.screenshot(path=str(screenshots / "practice-desktop-dark.png"),full_page=True)
    page.get_by_role("textbox",name="Record the details in your own words",exact=True).fill("Synthetic insurer, policy DEMO-123")
    page.get_by_role("button",name="Save text",exact=True).click()
    # A real upload traverses Streamlit's uploader and the local capture tool.
    page.locator('input[type="file"]').set_input_files(str(ROOT / "src/crisis_coach/practice/fixtures/usable.png"))
    page.get_by_role("button",name="Save photo",exact=True).click()
    page.get_by_test_id("stSidebar").get_by_text("Light",exact=True).click()
    expect(page.locator('.stApp')).to_have_css("background-color","rgb(242, 245, 244)")
    page.get_by_test_id("stMain").evaluate("e => e.scrollTop = 0")
    page.screenshot(path=str(screenshots / "practice-desktop-light.png"),full_page=True)
    caption=page.get_by_test_id("stCaptionContainer").filter(has_text="Suggested inputs")
    expect(caption).to_have_css("opacity","1")
    expect(caption).to_have_css("color","rgb(69, 95, 107)")
    repeat=page.get_by_role("button",name="Repeat",exact=True)
    repeat.focus()
    page.keyboard.press("Tab")
    expect(page.get_by_role("button",name="Slow down",exact=True)).to_be_focused()
    page.get_by_test_id("stSidebarCollapseButton").click()
    page.set_viewport_size({"width":390,"height":844})
    expect(page.get_by_test_id("stSidebar")).not_to_be_visible()
    page.get_by_test_id("stMain").evaluate("e => e.scrollTop = 0")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    page.screenshot(path=str(screenshots / "practice-mobile-light.png"),full_page=True)
    page.set_viewport_size({"width":1440,"height":1100})
    page.get_by_test_id("stExpandSidebarButton").click()
    # Choose an applicable three-item path and build a real document.
    page.get_by_role("combobox",name="Practice scenario",exact=True).click()
    page.get_by_role("option",name="Priya · minor scuff",exact=True).click()
    page.get_by_role("button",name="Start / reset practice",exact=True).click()
    clear_gates(page,expect)
    page.get_by_role("button",name="Simulate usable photo",exact=True).click()
    page.get_by_role("button",name="Simulate usable photo",exact=True).click()
    page.get_by_role("textbox",name="Record the details in your own words",exact=True).fill("I reversed into a bollard.")
    page.get_by_role("button",name="Save text",exact=True).click()
    page.get_by_test_id("stSidebar").get_by_text("Evidence pack",exact=True).click()
    page.get_by_role("button",name="Build evidence pack",exact=True).click()
    with page.expect_download() as downloaded:
        page.get_by_role("button",name="Download evidence pack",exact=True).click()
    target=tmp_path / "download.docx"
    downloaded.value.save_as(target)
    from docx import Document
    exported="\n".join(p.text for p in Document(target).paragraphs)
    assert "I reversed into a bollard." in exported
    assert "PRACTICE: synthetic data" in exported
    page.get_by_test_id("stSidebar").get_by_text("Incident",exact=True).click()
    page.get_by_role("button",name="He's shouting at me",exact=True).click()
    expect(page.get_by_text("Collection stopped",exact=True)).to_be_visible()
    expect(page.get_by_role("button",name="Pause",exact=True)).to_be_disabled()
    assert page.locator('input[type="file"]').count()==0
    page.screenshot(path=str(screenshots / "hostility-stand-down.png"),full_page=True)
    assert not external, external
