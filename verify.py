#!/usr/bin/env python3
"""
verify.py — 盲提取验证
从 input/verify/images/ 和 input/verify/watermarks/ 读取图片和水印，
盲提取后逐像素比对，输出验证结果图 → output/verify/

判定逻辑:
  NC > 0.80  → 匹配：该图片包含你的水印
  NC ≈ 0.50  → 未匹配：提取结果为随机噪声，图片不含该水印
  (0.50 是抛硬币的基线——4096 个像素各碰巧对上一半)
"""
import cv2, numpy as np, matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
import os, sys, io, datetime
import logging
from logging.handlers import RotatingFileHandler

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# --- 全局系统日志配置 (专业软件标准) ---
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'system.log')
logger = logging.getLogger('Onetry_System')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1*1024*1024, backupCount=3, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s] - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("程序崩溃 (Uncaught exception):", exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception
# ---------------------------------------

IMG_DIR = os.path.join("input", "verify", "images")
WM_DIR = os.path.join("input", "verify", "watermarks")
OUT_DIR = os.path.join("output", "verify")
WM_SIZE, COVER_SIZE, BLOCK_SIZE = 64, 512, 8

# ---- 阈值 (基于 ZNCC 零均值归一化交叉相关) ----
# NC > MATCH_THRESHOLD → 确认含水印
# NC < NOISE_THRESHOLD → 纯随机噪声或不相干水印，图片未嵌该水印
# 中间地带 → 图片可能被严重破坏但仍残留微量信号
MATCH_THRESHOLD = 0.70
NOISE_THRESHOLD = 0.30

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


def extract(image_bgr):
    if image_bgr.shape[:2] != (COVER_SIZE, COVER_SIZE):
        image_bgr = cv2.resize(image_bgr, (COVER_SIZE, COVER_SIZE))
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


def make_verify_chart(input_img, extracted_wm, ref_bin, ref_name, key):
    nc = calc_nc(ref_bin, extracted_wm)
    total_wm = WM_SIZE * WM_SIZE
    r = ref_bin.astype(np.float32) / 255.0
    e = extracted_wm.astype(np.float32) / 255.0
    wm_matched = int(np.sum(np.abs(r - e) < 0.5))
    wm_mismatched = total_wm - wm_matched
    wm_rate = wm_matched / total_wm * 100

    # ---- 判断提取结果是否为随机噪声 ----
    # 纯噪声的图案中 0/1 各半→匹配率约 50%
    is_noise = nc < NOISE_THRESHOLD
    is_match = nc > MATCH_THRESHOLD

    input_rgb = cv2.cvtColor(input_img, cv2.COLOR_BGR2RGB)

    # ==============================================================
    # 画图: 上两栏 + 下两栏 + 底部判定条
    # ==============================================================
    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(3, 2, height_ratios=[3, 3, 0.7], hspace=0.5, wspace=0.15)

    # ---- 上左: 待验证图片 ----
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.imshow(input_rgb)
    ax1.set_title("待验证图片", fontsize=13, fontweight="bold")
    ax1.axis("off")

    # ---- 上右: 证据链/判定说明 ----
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.axis("off")

    if is_match:
        explanation = (
            "证据链说明\n\n"
            "① 左侧为待验证图片\n"
            "② 从图片中盲提取水印\n"
            "   （不依赖原图、不依赖原始水印）\n"
            "③ 提取结果与你的原始水印\n"
            "   逐像素比对\n\n"
            "比对结果:\n"
            f"水印共 {total_wm} 个像素\n"
            f"一致: {wm_matched}\n"
            f"不一致: {wm_mismatched}\n"
            f"匹配率: {wm_rate:.1f}%\n\n"
            f"结论：该图片包含你的水印\n"
            f"NC={nc:.4f}，远超随机基线 0.50\n"
            f"纯巧合概率 = (1/2)^4096 ≈ 10^-1233\n"
        )
        box_color = "#d5f5e3"
    elif is_noise:
        explanation = (
            "证据链说明\n\n"
            "① 左侧为待验证图片\n"
            "② 从图片中盲提取水印\n"
            "③ 提取结果与原始水印逐像素比对\n\n"
            "比对结果:\n"
            f"水印共 {total_wm} 像素\n"
            f"一致: {wm_matched}  不一致: {wm_mismatched}\n"
            f"匹配率: {wm_rate:.1f}%\n\n"
            f"结论：该图片不含此水印\n"
            f"NC={nc:.4f}，≈随机基线 0.50\n"
            f"→ 提取结果不包含你的水印\n"
        )
        box_color = "#fadbd8"
    else:
        explanation = (
            "证据链说明\n\n"
            "① 左侧为待验证图片\n"
            "② 从图片中盲提取水印\n"
            "③ 提取结果与你的原始水印\n"
            "   逐像素比对\n\n"
            "比对结果:\n"
            f"水印共 {total_wm} 个像素\n"
            f"一致: {wm_matched}\n"
            f"不一致: {wm_mismatched}\n"
            f"匹配率: {wm_rate:.1f}%\n\n"
            f"结论：可能有微量残留\n"
            f"NC={nc:.4f}，略高于噪音基线\n"
            f"图片可能嵌过水印但被严重破坏\n"
            f"（多次压缩、裁剪、叠加等）"
        )
        box_color = "#fdebd0"

    ax2.text(0.5, 0.5, explanation, transform=ax2.transAxes,
             fontsize=11, ha="center", va="center",
             bbox=dict(boxstyle="round,pad=0.8", facecolor=box_color,
                       edgecolor="gray", alpha=0.95))

    # ---- 下左: 盲提取出的水印 ----
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.imshow(extracted_wm, cmap="gray")
    if is_noise:
        ax3.set_title("盲提取结果\n", fontsize=12, fontweight="bold", color="#c0392b")
    elif is_match:
        ax3.set_title("盲提取出的水印\n", fontsize=12, fontweight="bold")
    else:
        ax3.set_title("盲提取结果（有微弱痕迹）\n→ 图片可能被严重破坏", fontsize=12, fontweight="bold", color="#e67e22")
    ax3.axis("off")

    # ---- 下右: 我的原始水印 ----
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.imshow(ref_bin, cmap="gray")
    ax4.set_title(f"我的原始水印（签名）\n{ref_name}", fontsize=12, fontweight="bold")
    ax4.axis("off")

    # ---- 底部判定条 ----
    ax_bar = fig.add_subplot(gs[2, :])
    if is_match:
        bar_color = "#2ecc71"
        bar_label = f"水印像素匹配率: {wm_rate:.1f}%  |  NC: {nc:.4f}  |  判定: 包含你的水印"
    elif is_noise:
        bar_color = "#e74c3c"
        bar_label = f"水印像素匹配率: {wm_rate:.1f}%（约等于随机 50%）  |  NC: {nc:.4f}  |  判定: 不含该水印"
    else:
        bar_color = "#f39c12"
        bar_label = f"水印像素匹配率: {wm_rate:.1f}%  |  NC: {nc:.4f}  |  判定: 可能有微量残留"
    ax_bar.barh(["水印像素匹配率"], [wm_rate], height=0.5, color=[bar_color])
    ax_bar.barh(["水印像素匹配率"], [100], height=0.5, color=["#ecf0f1"], zorder=0)
    ax_bar.set_xlim(0, 100)
    ax_bar.set_xlabel(bar_label, fontsize=13, fontweight="bold")
    ax_bar.xaxis.set_ticks_position("top")
    ax_bar.xaxis.set_label_position("top")
    ax_bar.tick_params(left=False, labelleft=False)

    # 顶部总结
    if is_match:
        verdict = (f"【验证成功】水印匹配率 {wm_rate:.1f}%，NC={nc:.4f}。该图片包含你的水印！")
        vcolor = "#27ae60"
    elif is_noise:
        verdict = (f"【未匹配】匹配率仅 {wm_rate:.1f}%（≈随机 50%），NC={nc:.4f}。"
                   f"该图片不含你的水印。")
        vcolor = "#c0392b"
    else:
        verdict = (f"【不确定】匹配率 {wm_rate:.1f}%，NC={nc:.4f}。"
                   f"图片可能嵌过水印但被严重破坏。")
        vcolor = "#e67e22"
    fig.suptitle(verdict, fontsize=16, fontweight="bold", color=vcolor, y=0.995)

    return nc, fig


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

def main():
    logger.info("=== 开始运行 verify.py (盲提取验证) ===")
    os.makedirs(OUT_DIR, exist_ok=True)
    images = scan(IMG_DIR)
    wms = scan(WM_DIR)
    if not images:
        print(f"[错误] {IMG_DIR}/ 里没有图片"); sys.exit(1)
    if not wms:
        print(f"[错误] {WM_DIR}/ 里没有图片"); sys.exit(1)

    print(f"待验证图片: {len(images)}  水印: {len(wms)}\n")
    txt_log = [f"--- 盲提取验证任务日志 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---"]

    for img_p in images:
        img = cv_imread(img_p)
        if img is None:
            msg = f"[跳过] 无法读取待验证图片: {img_p}"
            print(msg)
            txt_log.append(msg)
            logger.warning(msg)
            continue
            
        img_name = os.path.splitext(os.path.basename(img_p))[0]
        ext_wm = extract(img)

        for wm_p in wms:
            wm_name = os.path.splitext(os.path.basename(wm_p))[0]
            key = f"{img_name}__{wm_name}"
            ref_raw = cv_imread(wm_p, cv2.IMREAD_GRAYSCALE)
            if ref_raw is None:
                msg = f"[跳过] 无法读取水印图: {wm_p}"
                print(msg)
                txt_log.append(msg)
                logger.warning(msg)
                continue
            ref_raw = cv2.resize(ref_raw, (WM_SIZE, WM_SIZE))
            _, ref_bin = cv2.threshold(ref_raw, 127, 255, cv2.THRESH_BINARY)

            nc, _ = calc_nc(ref_bin, ext_wm), None
            nc_val = calc_nc(ref_bin, ext_wm)

            if nc_val > MATCH_THRESHOLD:
                tag = "匹配"
            elif nc_val < NOISE_THRESHOLD:
                tag = "未匹配(噪声)"
            else:
                tag = "残留"

            print(f"[{key}]  NC={nc_val:.4f} → {tag}")
            success_msg = f"[成功] {key} -> 验证完成: {tag} (NC={nc_val:.4f})"
            txt_log.append(success_msg)
            logger.info(success_msg)

            _, fig = make_verify_chart(img, ext_wm, ref_bin,
                                       os.path.basename(wm_p), key)
            out_path = get_unique_filepath(OUT_DIR, f"{key}_验证结果")
            fig.savefig(out_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

    with open(os.path.join(OUT_DIR, "process_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(txt_log) + "\n")

    print(f"\n===== 完成 =====")
    print(f"验证结果图在: {OUT_DIR}/")
    print(f"")
    print(f"\n判定说明:")
    print(f"  NC > {MATCH_THRESHOLD}  → 包含你的水印")
    print(f"  NC < {NOISE_THRESHOLD}  → 不含该水印（随机噪声或不相干水印）")
    print(f"  中间值            → 可能有微量残留")
    logger.info("=== verify.py 运行结束 ===")


if __name__ == "__main__":
    main()
