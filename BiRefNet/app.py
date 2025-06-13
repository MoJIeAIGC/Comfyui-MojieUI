import os
import io
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image
import torch
import torchvision.transforms as T

from config import Config
from models.birefnet import BiRefNet

app = FastAPI(title="BiRefNet Segmentation API", version="1.0")

# 固定输出画布尺寸（宽 x 高）
OUTPUT_WIDTH = 1024
OUTPUT_HEIGHT = 1280
# 留白 padding（像素）
PADDING = 50

# 初始化模型
config = Config()
model = BiRefNet(bb_pretrained=False)
model.eval().cuda()
weight_path = os.path.join(os.getcwd(), 'BiRefNet-general-epoch_244.pth')
if not os.path.exists(weight_path):
    raise FileNotFoundError(f"找不到模型权重：{weight_path}")
state = torch.load(weight_path, map_location='cuda')
model.load_state_dict(state)

# 模型输入预处理，仅用于推理
# 不影响后续输出尺寸或比例
preprocess = T.Compose([
    T.Resize((OUTPUT_HEIGHT, OUTPUT_WIDTH)),  # H, W
    T.ToTensor(),
])

@app.post("/segment")
async def segment_image(file: UploadFile = File(...)):
    # 1. 读取上传图像
    try:
        data = await file.read()
        img = Image.open(io.BytesIO(data)).convert('RGB')
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")

    orig_w, orig_h = img.size

    # 2. 推理得到固定大小的 mask
    resized_input = img.resize((OUTPUT_WIDTH, OUTPUT_HEIGHT), Image.Resampling.LANCZOS)
    input_tensor = preprocess(resized_input).unsqueeze(0).half().cuda()

    with torch.no_grad(), torch.cuda.amp.autocast():
        preds = model(input_tensor)
        mask = preds[-1].sigmoid().squeeze().cpu().numpy()

    # 显式释放 GPU 缓存
    torch.cuda.empty_cache()

    # 3. 将 mask 从模型尺寸映射回原始分辨率
    mask_img = Image.fromarray((mask * 255).astype('uint8'), mode='L')
    mask_orig = mask_img.resize((orig_w, orig_h), Image.Resampling.NEAREST)

    # 4. 根据 mask bbox 裁剪前景区域（原图）
    bbox = mask_orig.getbbox()
    if bbox:
        fg = img.crop(bbox)
    else:
        fg = img.copy()

    # 5. 给前景添加 alpha 通道
    fg = fg.convert('RGBA')
    mask_crop = mask_orig.crop(bbox) if bbox else mask_orig
    mask_crop = mask_crop.resize((fg.width, fg.height), Image.Resampling.LANCZOS)
    fg.putalpha(mask_crop)

    # 6. 等比例缩放前景到可用区域
    max_w = OUTPUT_WIDTH - 2 * PADDING
    max_h = OUTPUT_HEIGHT - 2 * PADDING
    fg_w, fg_h = fg.size
    scale = min(max_w / fg_w, max_h / fg_h)
    new_w = int(fg_w * scale)
    new_h = int(fg_h * scale)
    fg_resized = fg.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 7. 在白底画布上居中贴前景
    canvas = Image.new('RGBA', (OUTPUT_WIDTH, OUTPUT_HEIGHT), (255, 255, 255, 255))
    offset_x = (OUTPUT_WIDTH - new_w) // 2
    offset_y = (OUTPUT_HEIGHT - new_h) // 2
    canvas.paste(fg_resized, (offset_x, offset_y), mask=fg_resized)

    # 8. 返回 PNG
    buf = io.BytesIO()
    canvas.save(buf, format='PNG')
    buf.seek(0)
    return StreamingResponse(buf, media_type='image/png')

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, workers=1)