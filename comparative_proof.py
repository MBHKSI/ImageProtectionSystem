#!/usr/bin/env python3
"""
comparative_proof.py — 证据对比图
从 comparative_proof/covers/ comparative_proof/watermarked/ comparative_proof/watermarks/ 读取，
生成全证据链对比图 → output/comparative_proof/

布局 (上三栏 + 下三栏):
  上左: 含水印图          上中: 原图vs含水印差异(红点)   上右: 水印差异(红点)
  下左: 我的水印(签名)    下中: 盲提取出的水印          下右: 证据链注释
  底部: NC系数 + 水印匹配率绿条
"""
import cv2, numpy as np, matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
import os, sys, json, io, datetime
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

COVER_DIR = os.path.join("input", "comparative_proof", "covers")
WMED_DIR = os.path.join("input", "comparative_proof", "watermarked")
WM_DIR = os.path.join("input", "comparative_proof", "watermarks")
OUT_DIR = os.path.join("output", "comparative_proof")
WM_SIZE, COVER_SIZE, BLOCK_SIZE = 64, 512, 8

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


def make_chart(cover, wmed, ref_bin, extracted_wm, ref_name, key):
    nc = calc_nc(ref_bin, extracted_wm)
    total_wm = WM_SIZE * WM_SIZE
    r = ref_bin.astype(np.float32) / 255.0
    e = extracted_wm.astype(np.float32) / 255.0
    wm_matched = int(np.sum(np.abs(r - e) < 0.5))
    wm_mismatched = total_wm - wm_matched
    wm_rate = wm_matched / total_wm * 100

    # ---- 图像级差异(原图 vs 含水印)——标红 ----
    orig_rgb = cv2.cvtColor(cover, cv2.COLOR_BGR2RGB)
    wmed_rgb = cv2.cvtColor(wmed, cv2.COLOR_BGR2RGB)
    orig_y = cv2.cvtColor(cover, cv2.COLOR_BGR2YCrCb)[:, :, 0]
    wmed_y = cv2.cvtColor(wmed, cv2.COLOR_BGR2YCrCb)[:, :, 0]
    img_diff_mask = np.abs(orig_y.astype(np.int16) - wmed_y.astype(np.int16)) > 3
    img_changed = int(np.sum(img_diff_mask))
    img_total = img_diff_mask.size
    img_changed_pct = img_changed / img_total * 100

    # 显示图: 含水印图当底, 差异像素标红
    img_diff_disp = wmed_rgb.copy()
    img_diff_disp[img_diff_mask, 0] = 255
    img_diff_disp[img_diff_mask, 1] = 0
    img_diff_disp[img_diff_mask, 2] = 0

    # ---- 水印级差异图(原始水印 vs 提取水印)——仅红点 ----
    wm_diff_map = np.full((WM_SIZE, WM_SIZE, 3), 255, dtype=np.uint8)
    wm_diff_mask = np.abs(r - e) >= 0.5
    wm_diff_map[wm_diff_mask, 0] = 255
    wm_diff_map[wm_diff_mask, 1] = 0
    wm_diff_map[wm_diff_mask, 2] = 0

    # ==============================================================
    # 画图: 上三栏 + 下三栏 + 底部判定条
    # ==============================================================
    fig = plt.figure(figsize=(20, 11))
    gs = fig.add_gridspec(3, 3, height_ratios=[3, 3, 0.7], hspace=0.5, wspace=0.15)

    # ---- 上排 ----
    # 上左: 含水印图
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.imshow(wmed_rgb)
    ax1.set_title("含水印图（肉眼与原始无差别）", fontsize=11, fontweight="bold")
    ax1.axis("off")

    # 上中: 原图vs含水印差异（红点）
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.imshow(img_diff_disp)
    ax2.set_title(
        f"原图 vs 含水印：像素级差异\n"
        f"红色=被嵌入修改的像素（{img_changed}/{img_total}，{img_changed_pct:.1f}%）",
        fontsize=10, fontweight="bold", color="#c0392b")
    ax2.axis("off")

    # 上右: 水印差异图（仅红点）
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.imshow(wm_diff_map)
    ax3.set_title(
        f"水印差异：原始 vs 提取\n"
        f"红色=不一致（{wm_mismatched}/{total_wm}）",
        fontsize=10, fontweight="bold")
    ax3.axis("off")

    # ---- 下排 ----
    # 下左: 我的水印（签名）
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.imshow(ref_bin, cmap="gray")
    ax4.set_title(f"我的水印（签名）\n{ref_name}", fontsize=11, fontweight="bold")
    ax4.axis("off")

    # 下中: 盲提取出的水印
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.imshow(extracted_wm, cmap="gray")
    ax5.set_title("盲提取出的水印\n", fontsize=11, fontweight="bold")
    ax5.axis("off")

    # 下右: 证据链注释
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis("off")
    if nc > 0.8:
        explanation = (
            "证据链说明\n\n"
            "① 含水印图与原图肉眼无区别\n"
            "② 差异图证明图像被修改过\n"
            "   （红点散布全图每个8×8小块）\n"
            "③ 盲提取出的水印图案\n"
            "④ 水印差异图：逐像素比对\n"
            "   白色=一致，红色=不一致\n\n"
            f"水印共 {total_wm} 个像素\n"
            f"一致: {wm_matched}  不一致: {wm_mismatched}\n"
            f"匹配率: {wm_rate:.1f}%\n\n"
            "结论：散布全图的微小修改\n"
            "此图编码了我的水印"
        )
        box_color = "#d5f5e3"
    else:
        explanation = (
            "证据链说明\n\n"
            "① 含水印图与原图肉眼无区别\n"
            "② 差异图证明图像被修改过\n"
            "   （红点散布全图每个8×8小块）\n"
            "③ 盲提取出的水印图案\n"
            "④ 水印差异图：逐像素比对\n"
            "   白色=一致，红色=不一致\n\n"
            f"水印共 {total_wm} 个像素\n"
            f"一致: {wm_matched}  不一致: {wm_mismatched}\n"
            f"匹配率: {wm_rate:.1f}%（≈随机50%）\n\n"
            "结论：提取结果与该水印不匹配\n"
            "此图未嵌入我的水印"
        )
        box_color = "#fadbd8"
    ax6.text(0.5, 0.5, explanation, transform=ax6.transAxes,
             fontsize=10, ha="center", va="center",
             bbox=dict(boxstyle="round,pad=0.8", facecolor=box_color,
                       edgecolor="gray", alpha=0.95))

    # ---- 底部判定条 ----
    ax_bar = fig.add_subplot(gs[2, :])
    bar_color = "#2ecc71" if wm_rate > 90 else "#f39c12" if wm_rate > 50 else "#e74c3c"
    ax_bar.barh(["水印像素匹配率"], [wm_rate], height=0.5, color=[bar_color])
    ax_bar.barh(["水印像素匹配率"], [100], height=0.5, color=["#ecf0f1"], zorder=0)
    ax_bar.set_xlim(0, 100)
    ax_bar.set_xlabel(
        f"水印像素匹配率: {wm_rate:.1f}%  |  NC 相关系数: {nc:.4f}  |  "
        f"全图被修改像素占比: {img_changed_pct:.2f}%（肉眼无法察觉）",
        fontsize=12, fontweight="bold")
    ax_bar.xaxis.set_ticks_position("top")
    ax_bar.xaxis.set_label_position("top")
    ax_bar.tick_params(left=False, labelleft=False)

    # 顶部总结
    if nc > 0.8:
        verdict = (f"【取证成功】水印像素匹配率 {wm_rate:.1f}%，"
                   f"NC={nc:.4f}。该图片可以证明出自你的作品！")
        vcolor = "#27ae60"
    else:
        verdict = (f"【不匹配】匹配率仅 {wm_rate:.1f}%（≈随机50%），"
                   f"NC={nc:.4f}。该图片未嵌入此水印。")
        vcolor = "#c0392b"
    fig.suptitle(verdict, fontsize=18, fontweight="bold", color=vcolor, y=0.995)

    return nc, fig


def main():
    logger.info("=== 开始运行 comparative_proof.py (取证对比) ===")
    os.makedirs(OUT_DIR, exist_ok=True)
    covers = scan(COVER_DIR)
    wmeds = scan(WMED_DIR)
    wms = scan(WM_DIR)
    if not covers:
        print(f"[错误] {COVER_DIR}/ 里没有图片"); sys.exit(1)
    if not wmeds:
        print(f"[错误] {WMED_DIR}/ 里没有图片"); sys.exit(1)
    if not wms:
        print(f"[错误] {WM_DIR}/ 里没有图片"); sys.exit(1)

    print(f"原图: {len(covers)}  含水印图: {len(wmeds)}  水印: {len(wms)}\n")
    txt_log = [f"--- 取证对比任务日志 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---"]

    for wmed_p in wmeds:
        wmed = cv_imread(wmed_p)
        if wmed is None:
            msg = f"[跳过] 无法读取含水印图: {wmed_p}"
            print(msg)
            txt_log.append(msg)
            logger.warning(msg)
            continue
            
        wmed_name = os.path.splitext(os.path.basename(wmed_p))[0]
        ext_wm = extract(wmed)

        # 尝试匹配 cover（按文件名前缀）
        matched_cover = None
        for cp in covers:
            cn = os.path.basename(cp)
            if cn in os.path.basename(wmed_p) or os.path.splitext(cn)[0] in wmed_name:
                tmp_cover = cv_imread(cp)
                if tmp_cover is not None:
                    matched_cover = cv2.resize(tmp_cover, (COVER_SIZE, COVER_SIZE))
                break
                
        if matched_cover is None:
            tmp_cover = cv_imread(covers[0])
            if tmp_cover is not None:
                matched_cover = cv2.resize(tmp_cover, (COVER_SIZE, COVER_SIZE))
            else:
                msg = f"[跳过] 无法读取默认原图，跳过当前水印图处理"
                print(msg)
                txt_log.append(msg)
                logger.warning(msg)
                continue

        for wm_p in wms:
            wm_name = os.path.splitext(os.path.basename(wm_p))[0]
            key = f"{wmed_name}__{wm_name}"
            ref_raw = cv_imread(wm_p, cv2.IMREAD_GRAYSCALE)
            if ref_raw is None:
                msg = f"[跳过] 无法读取水印图: {wm_p}"
                print(msg)
                txt_log.append(msg)
                logger.warning(msg)
                continue
            ref_raw = cv2.resize(ref_raw, (WM_SIZE, WM_SIZE))
            _, ref_bin = cv2.threshold(ref_raw, 127, 255, cv2.THRESH_BINARY)

            print(f"[{key}]")
            nc, fig = make_chart(matched_cover, wmed, ref_bin, ext_wm,
                                 os.path.basename(wm_p), key)
            out_path = get_unique_filepath(OUT_DIR, f"{key}_证据对比图")
            fig.savefig(out_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"  NC={nc:.4f} → {out_path}")
            success_msg = f"[成功] {key} -> 生成对比图 (NC={nc:.4f})"
            txt_log.append(success_msg)
            logger.info(success_msg)

    with open(os.path.join(OUT_DIR, "process_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(txt_log) + "\n")

    print(f"\n===== 完成 =====")
    print(f"证据对比图在: {OUT_DIR}/")
    logger.info("=== comparative_proof.py 运行结束 ===")


if __name__ == "__main__":
    main()
