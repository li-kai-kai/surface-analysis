import streamlit as st
import os
import tempfile
from process_xyz import process_xyz
import matplotlib.pyplot as plt
from PIL import Image
import zipfile
import io

# 设置页面配置
st.set_page_config(page_title="面形分析工具", page_icon="", layout="wide")

# 自定义CSS - 中文化文件上传组件
st.markdown(
    """
<style>
[data-testid="stFileUploader"] section > div:first-child {
    font-size: 0;
}
[data-testid="stFileUploaderDropzoneInstructions"] > div > span {
    display: none;
}

[data-testid="stFileUploaderDropzoneInstructions"] > div::before {
    content: "拖拽文件到此处";
    font-size: 14px;
}

/* 侧边栏标题样式 */
[data-testid="stSidebar"] h1 {
    font-size: 22px !important;
    font-weight: 700 !important;
    padding: 0.3rem 0 0.6rem 0 !important;
    margin: 0 !important;
    border-bottom: 2px solid rgba(128, 128, 128, 0.2);
}

/* 侧边栏子标题样式 */
[data-testid="stSidebar"] h3 {
    font-size: 13px !important;
    font-weight: 600 !important;
    margin-top: 0.8rem !important;
    margin-bottom: 0.4rem !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    opacity: 0.8;
}

/* 输入框标签样式 */
[data-testid="stSidebar"] label {
    font-size: 14px !important;
    font-weight: 500 !important;
}

/* 文件上传区域样式 */
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    margin-bottom: 0.8rem;
}

/* 按钮样式优化 */
[data-testid="stSidebar"] button[kind="primary"] {
    margin-top: 0.8rem !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    padding: 0.6rem 1rem !important;
}

/* 数字输入框间距 */
[data-testid="stSidebar"] [data-testid="stNumberInput"] {
    margin-bottom: 0.5rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# 侧边栏 - 参数设置
with st.sidebar:
    st.title("面形分析工具")

    # 文件上传区域
    st.markdown("### 数据文件")
    uploaded_file = st.file_uploader(
        "上传zygo文件",
        type=["xyz"],
        help="请选择要分析的zygo文件",
        label_visibility="collapsed",
    )

    # 分析参数区域
    st.markdown("### 分析参数")

    slit_height = st.number_input(
        "调平狭缝宽度 (mm)",
        min_value=1.0,
        max_value=50.0,
        value=8.0,
        format="%.1f",
        step=0.1,
    )

    scale_mm = st.number_input(
        "数据分辨率 (mm)",
        min_value=0.01,
        max_value=1.0,
        value=0.175,
        format="%.3f",
        step=0.001,
        help="zygo数据的像素到物理坐标的转换比例",
    )

    # 子口径参数
    st.markdown("### 子口径尺寸")
    col1, col2 = st.columns(2)
    with col1:
        sub_x = st.number_input(
            "X方向 (mm)",
            min_value=0.1,
            max_value=10.0,
            value=3.4,
            format="%.1f",
            step=0.1,
        )
    with col2:
        sub_y = st.number_input(
            "Y方向 (mm)",
            min_value=0.01,
            max_value=5.0,
            value=0.5,
            format="%.1f",
            step=0.1,
        )

    # 分析按钮
    analyze_button = st.button("开始分析", type="primary", use_container_width=True)

# 主界面
if uploaded_file is None or not analyze_button:

    # 显示使用说明
    with st.expander("📖 使用说明", expanded=True):
        st.markdown(
            """
        ### 使用步骤:
        1. 点击左侧 **"上传zygo文件"** 按钮选择文件
        2. 调整参数
        3. 点击 **"开始分析"** 按钮
        4. 等待处理完成,查看分析结果
        5. 下载生成的结果文件
        
        ### 输出结果:
        - 去一阶面形
        - NCE面形
        - SFMA面形
        - 局部角分布
        - 处理后的数据文件
        """
        )

else:
    if analyze_button:
        # 创建临时目录保存文件
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存上传的文件
            input_path = os.path.join(temp_dir, uploaded_file.name)
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # 设置输出路径
            output_filename = uploaded_file.name.replace(".xyz", "-processed.txt")
            output_path = os.path.join(temp_dir, output_filename)
            file_name_suffix = uploaded_file.name.split(".")[0]
            # 显示进度
            with st.spinner("正在分析数据,请稍候..."):
                try:
                    # 调用处理函数,传递用户配置的参数
                    # 将mm转换为m
                    metrics = process_xyz(
                        input_path,
                        output_path,
                        scale=scale_mm * 0.001,  # mm -> m
                        step_x=sub_x * 0.001,  # mm -> m
                        step_y=sub_y * 0.001,  # mm -> m
                        slit_height=slit_height * 0.001,  # mm -> m
                    )

                    st.toast("分析完成!", icon="✅", duration=1)

                    # 显示结果
                    # 图片路径
                    img_base = output_path.replace(".txt", "")
                    img_tilt_removed = img_base + ".png"
                    img_nce = img_base + "-nce.png"
                    img_sfma = img_base + "-sfma.png"
                    img_tilt = img_base + "-tilt.png"
                    img_tilt_high = img_base + "-tilt-high.png"

                    # 准备所有图像的ZIP文件
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        if os.path.exists(img_tilt_removed):
                            zf.write(
                                img_tilt_removed, os.path.basename(img_tilt_removed)
                            )
                        if os.path.exists(img_nce):
                            zf.write(img_nce, os.path.basename(img_nce))
                        if os.path.exists(img_sfma):
                            zf.write(img_sfma, os.path.basename(img_sfma))
                        if os.path.exists(img_tilt):
                            zf.write(img_tilt, os.path.basename(img_tilt))
                        if os.path.exists(img_tilt_high):
                            zf.write(img_tilt_high, os.path.basename(img_tilt_high))

                    # 显示结果标题和下载按钮
                    h_col1, h_col2, h_col3 = st.columns([6, 1, 1])
                    with h_col1:
                        st.header("分析结果")
                    with h_col2:
                        st.download_button(
                            "保存图表",
                            data=zip_buffer.getvalue(),
                            file_name=f"{file_name_suffix}_images.zip",
                            mime="application/zip",
                            help="下载所有分析图表(ZIP)",
                        )
                    with h_col3:
                        if os.path.exists(output_path):
                            with open(output_path, "rb") as f:
                                st.download_button(
                                    "保存数据",
                                    f,
                                    file_name=output_filename,
                                    mime="text/plain",
                                    help="下载预处理数据(TXT)",
                                )

                    if metrics:
                        # 1. 展示指标值
                        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                        with m_col1:
                            st.metric("去一阶面形 PV", f"{metrics['pv']*1e6:.2f} μm")
                        with m_col2:
                            st.metric("NCE (3σ)", f"{metrics['nce']*1e9:.2f} nm")
                        with m_col3:
                            st.metric("SFMA (m+3σ)", f"{metrics['sfma']*1e9:.2f} nm")
                        with m_col4:
                            st.metric(
                                "局部角分布 (m+3σ)", f"{metrics['tilt']:.2f} μrad"
                            )

                        st.markdown("---")

                    # 3. 展示图表
                    # 第一行：去一阶面形 和 NCE面形
                    col1, col2 = st.columns(2)

                    with col1:
                        st.subheader("去一阶面形")
                        if os.path.exists(img_tilt_removed):
                            st.image(
                                img_tilt_removed,
                                caption="去一阶面形 (PV值)",
                                use_container_width=True,
                            )
                        else:
                            st.warning("未生成去一阶面形图")

                    with col2:
                        st.subheader("NCE面形")
                        if os.path.exists(img_nce):
                            st.image(
                                img_nce,
                                caption="NCE面形 (96场布局)",
                                use_container_width=True,
                            )
                        else:
                            st.warning("未生成NCE面形")

                    # 第二行：SFMA面形 和 局部角分布
                    col3, col4 = st.columns(2)

                    with col3:
                        st.subheader("SFMA面形")
                        if os.path.exists(img_sfma):
                            st.image(
                                img_sfma,
                                caption="SFMA面形",
                                use_container_width=True,
                            )
                        else:
                            st.warning("未生成SFMA面形")

                    with col4:
                        st.subheader("局部角分布")
                        if os.path.exists(img_tilt):
                            st.image(
                                img_tilt,
                                caption="局部角分布",
                                use_container_width=True,
                            )
                        else:
                            st.warning("未生成局部角分布")

                    # 第三行：局部角分布 (>12.5urad)
                    col5, col6 = st.columns(2)

                    with col5:
                        st.subheader("局部角分布 (>12.5μrad)")
                        img_tilt_high = img_base + "-tilt-high.png"
                        if os.path.exists(img_tilt_high):
                            st.image(
                                img_tilt_high,
                                caption="局部角分布 (>12.5μrad)",
                                use_container_width=True,
                            )
                        else:
                            st.warning("未生成高局部角分布图")

                    with col6:
                        # 占位，保持布局平衡
                        pass

                    st.markdown("---")

                    # 4. 数据下载 (底部保留一个备用)
                    # if os.path.exists(output_path):
                    #     # 下载按钮
                    #     with open(output_path, "rb") as f:
                    #         st.download_button(
                    #             "📥 下载预处理数据文件",
                    #             f,
                    #             file_name=output_filename,
                    #             mime="text/plain",
                    #             key="btn_data_bottom",
                    #             type="secondary",
                    #             use_container_width=True,
                    #         )
                    # else:
                    #     st.warning("未生成数据文件")

                except Exception as e:
                    st.error(f"❌ 分析过程中出现错误: {str(e)}")
                    st.exception(e)

# 页脚
# st.markdown("---")
# st.markdown(
#     """
#     <div style='text-align: center; color: gray;'>
#     面形分析工具 v1.0
#     </div>
#     """,
#     unsafe_allow_html=True,
# )
