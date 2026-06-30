#!/usr/bin/env python3
"""
filling_in.py — 水印嵌入
从 filling_in/covers/ 和 filling_in/watermarks/ 读取图片，
输出含水印图到 output/filling_in/
"""
import cv2, numpy as np, os, sys, json, io, datetime
import logging
from logging.handlers import RotatingFileHandler

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# --- 全局系统日志配置 (专业软件标准) ---
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'system.log')
logger = logging.getLogger('Onetry_System')
logger.setLevel(logging.INFO)
if not logger.handlers:
    # 滚动日志：最大 1MB，保留 3 个备份，防止日志文件无限变大
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1*1024*1024, backupCount=3, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s] - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# 捕获导致程序崩溃的未处理异常
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("程序崩溃 (Uncaught exception):", exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception
# ---------------------------------------

COVER_DIR = os.path.join("input", "filling_in", "covers")
WM_DIR = os.path.join("input", "filling_in", "watermarks")
OUT_DIR = os.path.join("output", "filling_in")
WM_SIZE, COVER_SIZE, BLOCK_SIZE, P = 64, 512, 8, 20

def get_unique_filepath(directory, base_name, ext=".png"):
    """生成唯一的文件路径，如果存在则追加 (1), (2) 等"""
    filename = f"{base_name}{ext}"
    filepath = os.path.join(directory, filename)
    counter = 1
    while os.path.exists(filepath):
        filename = f"{base_name}({counter}){ext}"
        filepath = os.path.join(directory, filename)
        counter += 1
    return filepath


def check_already_watermarked(cover_bgr):
    """
    检测图片是否已经包含水印。
    原理：自然图像的 DCT 中频系数 D(3,2) 和 D(2,3) 差异通常较小。
    而打过水印的图像，由于强制加上了 P=20，这两个系数的绝对差值会显著增大。
    如果差值 > 18 的块占比超过 48%，则极大概率已经打过水印。
    """
    ycrcb = cv2.cvtColor(cover_bgr, cv2.COLOR_BGR2YCrCb)
    Y = ycrcb[:, :, 0].astype(np.float32)
    suspicious_blocks = 0
    total_blocks = 0
    for i in range(0, COVER_SIZE, BLOCK_SIZE):
        for j in range(0, COVER_SIZE, BLOCK_SIZE):
            yi, wi = i // BLOCK_SIZE, j // BLOCK_SIZE
            if yi >= WM_SIZE or wi >= WM_SIZE:
                break
            dct_block = cv2.dct(Y[i:i+BLOCK_SIZE, j:j+BLOCK_SIZE])
            if abs(dct_block[3, 2] - dct_block[2, 3]) > 18:
                suspicious_blocks += 1
            total_blocks += 1
    
    ratio = suspicious_blocks / total_blocks if total_blocks > 0 else 0
    return ratio > 0.48, ratio


def embed(cover_bgr, wm_bin):
    ycrcb = cv2.cvtColor(cover_bgr, cv2.COLOR_BGR2YCrCb)
    Y = ycrcb[:, :, 0].astype(np.float32)
    Cr, Cb = ycrcb[:, :, 1], ycrcb[:, :, 2]
    for i in range(0, COVER_SIZE, BLOCK_SIZE):
        for j in range(0, COVER_SIZE, BLOCK_SIZE):
            yi, wi = i // BLOCK_SIZE, j // BLOCK_SIZE
            if yi >= WM_SIZE or wi >= WM_SIZE:
                break
            block = Y[i:i+BLOCK_SIZE, j:j+BLOCK_SIZE].copy()
            dct_block = cv2.dct(block)
            bit = wm_bin[yi, wi]
            A, B = dct_block[3, 2], dct_block[2, 3]
            if bit == 1:
                if A <= B:
                    dct_block[3, 2] = B + P
            else:
                if B <= A:
                    dct_block[2, 3] = A + P
            Y[i:i+BLOCK_SIZE, j:j+BLOCK_SIZE] = cv2.idct(dct_block)
    Y = np.clip(Y, 0, 255).astype(np.uint8)
    return cv2.cvtColor(cv2.merge([Y, Cr, Cb]), cv2.COLOR_YCrCb2BGR)


def extract(image_bgr):
    ycrcb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2YCrCb)
    Y = ycrcb[:, :, 0].astype(np.float32)
    ext = np.zeros((WM_SIZE, WM_SIZE), dtype=np.uint8)
    for i in range(0, COVER_SIZE, BLOCK_SIZE):
        for j in range(0, COVER_SIZE, BLOCK_SIZE):
            yi, wi = i // BLOCK_SIZE, j // BLOCK_SIZE
            if yi >= WM_SIZE or wi >= WM_SIZE:
                break
            dct_block = cv2.dct(Y[i:i+BLOCK_SIZE, j:j+BLOCK_SIZE])
            ext[yi, wi] = 1 if dct_block[3, 2] > dct_block[2, 3] else 0
    return ext * 255


def calc_nc(a, b):
    a = a.astype(np.float32)
    b = b.astype(np.float32)
    a_mean = np.mean(a)
    b_mean = np.mean(b)
    num = np.sum((a - a_mean) * (b - b_mean))
    den = np.sqrt(np.sum((a - a_mean)**2) * np.sum((b - b_mean)**2))
    return float(num / den) if den != 0 else 0.0


def scan(folder):
    exts = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp'}
    if not os.path.isdir(folder):
        return []
    return sorted([os.path.join(folder, f) for f in os.listdir(folder)
                   if os.path.splitext(f)[1].lower() in exts])


def cv_imread(file_path, flags=cv2.IMREAD_COLOR):
    if not os.path.exists(file_path):
        print(f"[警告] 文件不存在: {file_path}")
        logger.warning(f"文件不存在: {file_path}")
        return None
    try:
        img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), flags)
        return img
    except Exception as e:
        print(f"[警告] 读取文件失败 {file_path}: {e}")
        logger.error(f"读取文件失败 {file_path}: {e}", exc_info=True)
        return None

def cv_imwrite(file_path, img):
    try:
        ext = os.path.splitext(file_path)[1]
        cv2.imencode(ext, img)[1].tofile(file_path)
        return True
    except Exception as e:
        print(f"[警告] 写入文件失败 {file_path}: {e}")
        logger.error(f"写入文件失败 {file_path}: {e}", exc_info=True)
        return False

def main():
    logger.info("=== 开始运行 filling_in.py (水印嵌入) ===")
    os.makedirs(OUT_DIR, exist_ok=True)
    covers = scan(COVER_DIR)
    wms = scan(WM_DIR)
    if not covers:
        print(f"[错误] {COVER_DIR}/ 里没有图片"); sys.exit(1)
    if not wms:
        print(f"[错误] {WM_DIR}/ 里没有图片"); sys.exit(1)

    print(f"找到 {len(covers)} 张原图 × {len(wms)} 个水印 → {len(covers)*len(wms)} 组\n")
    pairs_log = []
    txt_log = [f"--- 水印嵌入任务日志 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---"]

    for cp in covers:
        for wp in wms:
            cname = os.path.splitext(os.path.basename(cp))[0]
            wname = os.path.splitext(os.path.basename(wp))[0]
            key = f"{cname}__{wname}"

            tmp_cover = cv_imread(cp)
            if tmp_cover is None:
                msg = f"[跳过] 无法读取原图: {cp}"
                print(msg)
                txt_log.append(msg)
                logger.warning(msg)
                continue
            cover = cv2.resize(tmp_cover, (COVER_SIZE, COVER_SIZE))
            
            # 检查是否已经打过水印，防止二次覆盖
            is_watermarked, ratio = check_already_watermarked(cover)
            if is_watermarked:
                msg = f"[拒绝] 图片 {cp} 疑似已包含水印 (特征占比: {ratio:.1%})。为防止版权篡改，拒绝二次打入水印！"
                print(msg)
                txt_log.append(msg)
                logger.warning(msg)
                continue
            
            wm_raw = cv_imread(wp, cv2.IMREAD_GRAYSCALE)
            if wm_raw is None:
                msg = f"[跳过] 无法读取水印图: {wp}"
                print(msg)
                txt_log.append(msg)
                logger.warning(msg)
                continue
            wm_raw = cv2.resize(wm_raw, (WM_SIZE, WM_SIZE))
            _, wm_bin = cv2.threshold(wm_raw, 127, 1, cv2.THRESH_BINARY)

            watermarked = embed(cover, wm_bin)
            wm_out = get_unique_filepath(OUT_DIR, key)
            cv_imwrite(wm_out, watermarked)

            wm_ext = extract(watermarked)
            psnr = 20 * np.log10(255.0 / np.sqrt(np.mean(
                (cv2.cvtColor(cover, cv2.COLOR_BGR2YCrCb)[:, :, 0].astype(np.float32) -
                 cv2.cvtColor(watermarked, cv2.COLOR_BGR2YCrCb)[:, :, 0].astype(np.float32))**2
            )))
            nc = calc_nc(wm_bin * 255, wm_ext)

            print(f"[{key}]")
            print(f"  含水印图 → {wm_out}")
            print(f"  PSNR(Y) = {psnr:.2f} dB | NC = {nc:.4f}")
            success_msg = f"[成功] {key} -> 成功打入水印 (PSNR: {psnr:.2f}dB, NC: {nc:.4f})"
            txt_log.append(success_msg)
            logger.info(success_msg)

            pairs_log.append({
                "pair": key, "cover": cp, "watermark": wp,
                "watermarked": wm_out,
                "psnr_y": round(float(psnr), 2), "nc": round(float(nc), 4)
            })

    with open(os.path.join(OUT_DIR, "pairs.json"), "w", encoding="utf-8") as f:
        json.dump(pairs_log, f, ensure_ascii=False, indent=2)
        
    with open(os.path.join(OUT_DIR, "process_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(txt_log) + "\n")
        
    print(f"\n===== 完成 =====")
    print(f"含水印图在: {OUT_DIR}/")
    print(f"→ 请把输出图复制到 comparative_proof/watermarked/ 或 verify/images/")
    logger.info("=== filling_in.py 运行结束 ===")


if __name__ == "__main__":
    main()
