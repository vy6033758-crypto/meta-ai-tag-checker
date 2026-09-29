import io
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from PIL import Image, ExifTags

app = FastAPI(title="Meta & AI Tag Checker")
templates = Jinja2Templates(directory="templates")

# Known AI and Meta markers to detect
AI_INDICATORS = {
    "c2pa": "C2PA Provenance / Content Credentials Manifest (Used by Meta, OpenAI, Adobe)",
    "trainedalgorithmicmedia": "IPTC DigitalSourceType: Trained Algorithmic Media",
    "compositealgorithmicmedia": "IPTC DigitalSourceType: Composite Algorithmic Media",
    "meta ai": "Explicit Meta AI signature found",
    "midjourney": "Midjourney Generation Metadata",
    "dall-e": "OpenAI DALL-E Metadata",
    "stable diffusion": "Stable Diffusion parameters",
    "comfyui": "ComfyUI Workflow Metadata",
    "novelai": "NovelAI generation parameters",
}

def scan_raw_bytes(content: bytes) -> list[str]:
    detected = []
    content_lower = content.lower()
    for marker, description in AI_INDICATORS.items():
        if marker.encode("utf-8") in content_lower:
            detected.append(description)
    return detected

def inspect_image(image_bytes: bytes) -> dict:
    detected_tags = []
    extracted_metadata = {}
    is_ai = False

    # 1. Byte-level scan for C2PA, IPTC, and generator signatures
    byte_matches = scan_raw_bytes(image_bytes)
    if byte_matches:
        detected_tags.extend(byte_matches)
        is_ai = True

    # 2. PIL Image parsing (EXIF + text chunks like PNG tEXt)
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            extracted_metadata["format"] = img.format
            extracted_metadata["dimensions"] = f"{img.width}x{img.height}"

            # Check PNG metadata / text tags
            if hasattr(img, "text") and img.text:
                for k, v in img.text.items():
                    extracted_metadata[f"text:{k}"] = str(v)[:200]
                    v_lower = str(v).lower()
                    if any(t in v_lower for t in ["ai", "prompt", "steps", "cfg", "model", "meta"]):
                        detected_tags.append(f"PNG Text '{k}': contains AI prompt/generation data")
                        is_ai = True

            # Check EXIF
            exif_data = img.getexif()
            if exif_data:
                for tag_id, val in exif_data.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    str_val = str(val)[:200]
                    extracted_metadata[tag_name] = str_val
                    
                    tag_str = (tag_name + " " + str_val).lower()
                    if "meta" in tag_str or "algorithmic" in tag_str or "c2pa" in tag_str:
                        detected_tags.append(f"EXIF '{tag_name}': {str_val}")
                        is_ai = True
    except Exception as e:
        extracted_metadata["parsing_notice"] = f"Standard parser error: {str(e)}"

    return {
        "is_ai": is_ai,
        "signals": list(set(detected_tags)),
        "metadata_sample": dict(list(extracted_metadata.items())[:15]),
    }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"result": None}
    )

@app.post("/scan", response_class=HTMLResponse)
async def scan(request: Request, file: UploadFile = File(...)):
    contents = await file.read()
    result = inspect_image(contents)
    result["filename"] = file.filename
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"result": result}
    )

@app.post("/api/scan")
async def api_scan(file: UploadFile = File(...)):
    contents = await file.read()
    res = inspect_image(contents)
    res["filename"] = file.filename
    return res