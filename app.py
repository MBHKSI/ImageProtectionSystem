import streamlit as st
import os
import shutil
import subprocess
import sys
import json
import re

# --- 辅助函数 ---
def clear_dir(dir_path):
    """清空指定目录下的所有文件，如果目录不存在则创建"""
    if os.path.exists(dir_path):
        for f in os.listdir(dir_path):
            fp = os.path.join(dir_path, f)
            if os.path.isfile(fp):
                try:
                    os.remove(fp)
                except Exception as e:
                    pass
    else:
        os.makedirs(dir_path, exist_ok=True)

def save_uploaded_file(uploaded_file, dir_path):
    """保存上传的文件到指定目录"""
    if uploaded_file is not None:
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def run_script(script_name):
    """在当前 Python 环境下运行指定的脚本"""
    try:
        result = subprocess.run([sys.executable, script_name], capture_output=True, text=True, encoding='utf-8')
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)

# --- 页面配置 ---
st.set_page_config(page_title="盲水印版权保护系统", page_icon="🛡️", layout="centered")

# --- 自定义 CSS 样式 (谷歌搜索简约风) ---
st.markdown("""
<style>
/* 顶部留白，模仿搜索引擎居中感 */
.block-container {
    padding-top: 12vh;
    max-width: 800px;
}
/* 标题居中 */
.main-title {
    text-align: center;
    font-size: 3.5rem;
    font-weight: 600;
    color: #202124;
    margin-bottom: 10px;
}
/* 副标题居中 */
.sub-title {
    text-align: center;
    color: #5f6368;
    font-size: 1rem;
    margin-bottom: 40px;
}
/* 强制整个 Radio 组件的外部容器居中 */
div[data-testid="stRadio"] {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    width: 100% !important;
    margin: 0 auto !important;
}
/* 改造单选框为三个独立的方形大按钮，居中对齐 */
div[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    gap: 111px !important; /* 调整按钮之间的间距，让它们更舒展 */
    margin: 0 auto !important;
    width: 100% !important; /* 确保容器占满宽度以便居中 */
}
/* 针对每个选项的样式 */
div[data-testid="stRadio"] > div[role="radiogroup"] > label {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 30px; /* 更圆的边角 (胶囊形) */
    width: 180px; /* 稍微加宽一点，让文字更居中 */
    height: 60px; /* 固定高度 */
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 0;
    padding: 0;
}
/* 鼠标悬浮效果 */
div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
    box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    border-color: #b0bec5;
    transform: translateY(-2px); /* 悬浮时微微抬起 */
}
/* 选中状态的样式 (兼容不同版本的 Streamlit) */
div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"],
div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
    border: 2px solid #1a73e8;
    background-color: #e8f0fe; /* 更明显的浅蓝色 */
    box-shadow: 0 4px 12px rgba(26,115,232,.2);
}
/* 选中状态的文字颜色也变成蓝色，增强视觉效果 */
div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] > div:last-child,
div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) > div:last-child {
    color: #1a73e8 !important;
    font-weight: 600 !important;
}
/* 隐藏默认的单选圆圈 */
div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {
    display: none;
}
/* 调整文字样式，确保文字在按钮内绝对居中 */
div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:last-child {
    font-size: 1.1rem;
    font-weight: 500;
    color: #3c4043;
    margin-left: 0 !important; /* 移除默认的左边距 */
    width: 100%;
    text-align: center;
}
/* 隐藏单选框的默认标题 */
label[data-testid="stWidgetLabel"] {
    display: none;
}
/* 隐藏 Streamlit 默认的工具栏和底部水印 */
header {visibility: hidden;}
footer {visibility: hidden;}
/* 分割线 */
hr {
    margin-top: 40px;
    margin-bottom: 40px;
    border: 0;
    border-top: 1px solid #eee;
}
</style>
""", unsafe_allow_html=True)

# --- 页面头部 ---
st.markdown('<div class="main-title">盲水印系统</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">本地运行 · 绝对安全 · 保护您的数字版权</div>', unsafe_allow_html=True)

# --- 居中导航菜单 (三个独立的方形框架) ---
st.markdown('<div style="display: flex; justify-content: center; width: 100%;">', unsafe_allow_html=True)
menu = st.radio(
    "导航菜单",
    ["水印嵌入", "快捷验证", "取证对比"],
    horizontal=True,
    label_visibility="collapsed"
)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ==========================================
# 页面 1: 水印嵌入
# ==========================================
if menu == "水印嵌入":
    st.header("水印嵌入")
    st.markdown("将Logo以黑白水印形式隐形嵌入到图片中，肉眼无法察觉。")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**上传原图**")
        cover_file = st.file_uploader("请选择彩色摄影原图", type=['png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'], key="fill_cover")
    with col2:
        st.markdown("**上传水印**")
        wm_file = st.file_uploader("请选择黑白水印Logo", type=['png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'], key="fill_wm")
        
    if st.button("✨ 打入隐形水印", type="primary"):
        if cover_file and wm_file:
            with st.spinner("正在处理中，请稍候..."):
                # 1. 清理旧数据
                clear_dir("input/filling_in/covers")
                clear_dir("input/filling_in/watermarks")
                clear_dir("output/filling_in")
                
                # 2. 保存新文件
                save_uploaded_file(cover_file, "input/filling_in/covers")
                save_uploaded_file(wm_file, "input/filling_in/watermarks")
                
                # 3. 调用后端脚本
                stdout, stderr = run_script("filling_in.py")
                
                # 4. 读取并展示结果
                out_dir = "output/filling_in"
                if os.path.exists(out_dir):
                    out_files = [f for f in os.listdir(out_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tif', '.tiff'))]
                    if out_files:
                        out_img_path = os.path.join(out_dir, out_files[0])
                        
                        st.success("✅ 水印嵌入成功！")
                        
                        # 提供下载按钮 (放在成功提示下方，图片上方)
                        with open(out_img_path, "rb") as f:
                            st.download_button(
                                label="⬇️ 点击下载含水印图",
                                data=f,
                                file_name=f"watermarked_{cover_file.name}",
                                mime="image/png",
                                use_container_width=True
                            )
                        st.markdown("---")
                        
                        # 读取 JSON 获取 PSNR
                        json_path = os.path.join(out_dir, "pairs.json")
                        if os.path.exists(json_path):
                            with open(json_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                if data:
                                    psnr = data[0].get("psnr_y", "N/A")
                                    st.metric(label="图像质量 (PSNR)", value=f"{psnr} dB", help=">30dB即为肉眼难以分辨差异")
                        
                        # 并排展示
                        disp_col1, disp_col2 = st.columns(2)
                        with disp_col1:
                            # 直接读取保存到本地的原图进行展示，避免 BytesIO 指针问题
                            saved_cover_path = os.path.join("input/filling_in/covers", cover_file.name)
                            if os.path.exists(saved_cover_path):
                                st.image(saved_cover_path, caption="原始图片", use_container_width=True)
                        with disp_col2:
                            st.image(out_img_path, caption="含水印图片（肉眼无差别）", use_container_width=True)
                    else:
                        # 检查 stderr 中是否有特定的错误信息
                        if "cannot identify image file" in stderr or "0字节" in stderr or "empty" in stderr.lower():
                            st.error("❌ 处理失败：上传的图片已损坏或为空文件（0字节），无法读取。")
                        elif "拒绝二次打入水印" in stdout or "already contains a watermark" in stdout or "防二次篡改" in stdout:
                            st.error("❌ 处理失败：原图已包含水印，被拒绝打入。")
                        else:
                            st.error("❌ 处理失败：未找到输出图片。请检查上传的图片格式是否正确，或查看下方日志了解详情。")
                            
                        with st.expander("查看后台日志"):
                            st.code(stdout + "\n" + stderr)
        else:
            st.warning("请先上传原图和水印Logo！")

# ==========================================
# 页面 2: 快捷验证
# ==========================================
elif menu == "快捷验证":
    st.header("快捷验证")
    st.markdown("从网上拿到的可疑盗图中提取水印并验证。")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**上传图片**")
        v_img = st.file_uploader("请选择可疑盗图", type=['png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'], key="v_img")
    with col2:
        st.markdown("**上传水印**")
        v_wm = st.file_uploader("请选择原始水印", type=['png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'], key="v_wm")
        
    if st.button("🕵️ 盲验证版权", type="primary"):
        if v_img and v_wm:
            with st.spinner("正在盲提取水印..."):
                clear_dir("input/verify/images")
                clear_dir("input/verify/watermarks")
                clear_dir("output/verify")
                
                save_uploaded_file(v_img, "input/verify/images")
                save_uploaded_file(v_wm, "input/verify/watermarks")
                
                stdout, stderr = run_script("verify.py")
                
                out_dir = "output/verify"
                if os.path.exists(out_dir):
                    out_files = [f for f in os.listdir(out_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                    if out_files:
                        out_img_path = os.path.join(out_dir, out_files[0])
                        
                        # 解析日志获取 NC 和判定标签
                        log_path = os.path.join(out_dir, "process_log.txt")
                        nc_val = "未知"
                        tag = "未知"
                        if os.path.exists(log_path):
                            with open(log_path, "r", encoding="utf-8") as f:
                                content = f.read()
                                match = re.search(r"验证完成: (.*?) \(NC=([0-9.]+)\)", content)
                                if match:
                                    tag = match.group(1)
                                    nc_val = float(match.group(2))
                        
                        # 输出判定结论
                        if nc_val != "未知":
                            if nc_val > 0.8:
                                st.success(f"✅ 结论：该图片包含你的水印！(判定: {tag})")
                                st.metric(label="NC 相关系数", value=f"{nc_val:.4f}")
                            elif nc_val < 0.6:
                                st.error(f"❌ 结论：该图片不含此水印！(判定: {tag})")
                                st.metric(label="NC 相关系数", value=f"{nc_val:.4f}")
                            else:
                                st.warning(f"⚠️ 结论：可能有微量残留。(判定: {tag})")
                                st.metric(label="NC 相关系数", value=f"{nc_val:.4f}")
                                
                        # 提供下载按钮
                        with open(out_img_path, "rb") as f:
                            st.download_button(
                                label="⬇️ 点击下载盲提取验证结果图",
                                data=f,
                                file_name=f"verify_result_{v_img.name}",
                                mime="image/png",
                                use_container_width=True
                            )
                        st.markdown("---")
                                
                        # 展示提取出来的水印轮廓图
                        st.image(out_img_path, caption="盲提取验证结果", use_container_width=True)
                    else:
                        if "cannot identify image file" in stderr or "0字节" in stderr or "empty" in stderr.lower():
                            st.error("❌ 验证失败：上传的图片已损坏或为空文件（0字节），无法读取。")
                        else:
                            st.error("❌ 验证失败：未生成结果图，请检查图片格式或查看下方日志。")
                        with st.expander("查看后台日志"):
                            st.code(stdout + "\n" + stderr)
        else:
            st.warning("请上传可疑盗图和原始水印！")

# ==========================================
# 页面 3: 取证对比
# ==========================================
elif menu == "取证对比":
    st.header("取证对比")
    st.markdown("生成证据对比图。")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**上传原图**")
        cp_cover = st.file_uploader("请选择原始图片", type=['png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'], key="cp_cover")
    with col2:
        st.markdown("**上传含水印图**")
        cp_wmed = st.file_uploader("请选择含水印图片", type=['png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'], key="cp_wmed")
    with col3:
        st.markdown("**上传水印**")
        cp_wm = st.file_uploader("请选择原始水印", type=['png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'], key="cp_wm")
        
    if st.button("⚖️ 开始版权取证", type="primary"):
        if cp_cover and cp_wmed and cp_wm:
            with st.spinner("正在生成证据链对比图..."):
                clear_dir("input/comparative_proof/covers")
                clear_dir("input/comparative_proof/watermarked")
                clear_dir("input/comparative_proof/watermarks")
                clear_dir("output/comparative_proof")
                
                save_uploaded_file(cp_cover, "input/comparative_proof/covers")
                save_uploaded_file(cp_wmed, "input/comparative_proof/watermarked")
                save_uploaded_file(cp_wm, "input/comparative_proof/watermarks")
                
                stdout, stderr = run_script("comparative_proof.py")
                
                out_dir = "output/comparative_proof"
                if os.path.exists(out_dir):
                    out_files = [f for f in os.listdir(out_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                    if out_files:
                        out_img_path = os.path.join(out_dir, out_files[0])
                        
                        # 解析日志获取 NC 值
                        log_path = os.path.join(out_dir, "process_log.txt")
                        nc_val = "未知"
                        is_mismatch = False
                        if os.path.exists(log_path):
                            with open(log_path, "r", encoding="utf-8") as f:
                                content = f.read()
                                match = re.search(r"NC=([0-9.]+)", content)
                                if match:
                                    nc_val = float(match.group(1))
                                if "原图和含水印图不匹配" in content:
                                    is_mismatch = True
                        
                        # 大字报显示判定结果
                        if nc_val != "未知":
                            if is_mismatch:
                                st.warning("⚠️ 原图和水印图不匹配，请检查是否是同一张图！")
                            if nc_val > 0.8:
                                st.success("✅ 【取证成功】该图片包含您的水印！")
                                st.metric(label="NC 相关系数 (越接近1越匹配)", value=f"{nc_val:.4f}")
                            else:
                                st.error("❌ 【不匹配】该图片未包含您的水印。")
                                st.metric(label="NC 相关系数", value=f"{nc_val:.4f}")
                                
                        # 提供下载按钮
                        with open(out_img_path, "rb") as f:
                            st.download_button(
                                label="⬇️ 点击下载法庭取证对比图",
                                data=f,
                                file_name=f"proof_result_{cp_cover.name}",
                                mime="image/png",
                                use_container_width=True
                            )
                        st.markdown("---")
                                
                        # 渲染证据链对比图
                        st.image(out_img_path, caption="法庭取证对比图", use_container_width=True)
                    else:
                        if "cannot identify image file" in stderr or "0字节" in stderr or "empty" in stderr.lower():
                            st.error("❌ 生成失败：上传的图片已损坏或为空文件（0字节），无法读取。")
                        else:
                            st.error("❌ 生成失败：未生成对比图，请检查图片格式或查看下方日志。")
                        with st.expander("查看后台日志"):
                            st.code(stdout + "\n" + stderr)
        else:
            st.warning("请上传完整的三个文件！")
