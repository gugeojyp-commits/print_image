import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageOps
import io
import base64

st.set_page_config(page_title="학생 과제 A4 개별 인쇄기", layout="wide")

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

def reset_files():
    st.session_state.uploader_key += 1
    st.rerun()

st.title("🖨️ 학생 작품 A4 자동 맞춤 인쇄기")
st.write("학생들이 가로/세로 제각각 제출해도, **이미지 비율을 스스로 감지하여 A4 용지에 꽉 차게 자동 최적화**합니다.")

# 사이드바 설정
st.sidebar.header("⚙️ 인쇄 및 용지 설정")

auto_orientation_mode = st.sidebar.radio(
    "용지 방향 및 회전 방식",
    [
        "자동: 가로 그림은 90도 회전 (A4 세로 용지에 최대 크기로 출력 - 추천)",
        "자동: 그림 비율에 맞춰 PDF 페이지 방향 개별 설정 (가로/세로 혼합)",
        "고정: 모든 페이지를 A4 세로로 고정",
        "고정: 모든 페이지를 A4 가로로 고정"
    ],
    index=0
)

margin_mm = st.sidebar.slider("용지 여백 (mm)", min_value=0, max_value=30, value=8, step=1)
bg_color = st.sidebar.color_picker("배경 여백 색상", "#FFFFFF")

col_title, col_reset = st.columns([4, 1])
with col_reset:
    if st.button("🔄 전체 초기화", use_container_width=True, type="secondary"):
        reset_files()

uploaded_files = st.file_uploader(
    "학생 작품 이미지를 업로드하세요 (JPG, PNG - 다중 선택 가능)",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)

# 300 DPI 기준 A4 크기 (mm -> px)
DPI = 300
A4_SHORT = int(210 / 25.4 * DPI)  # 2480 px
A4_LONG = int(297 / 25.4 * DPI)   # 3508 px
margin_px = int(margin_mm * DPI / 25.4)

if uploaded_files:
    processed_pages = []

    with st.spinner("이미지 비율을 분석하여 A4 용지에 맞추는 중입니다..."):
        for file in uploaded_files:
            img = Image.open(file).convert("RGB")
            
            # EXIF 회전 정보 보정 (스마트폰으로 찍은 사진의 회전 정보 자동 반영)
            img = ImageOps.exif_transpose(img)

            img_w, img_h = img.size
            is_landscape = img_w > img_h  # 가로가 더 길면 True

            # 모드별 용지 크기 및 회전 결정
            if auto_orientation_mode.startswith("자동: 가로 그림은 90도 회전"):
                # 용지는 항상 세로, 가로 그림은 90도 돌려서 세로 A4에 꽉 채움
                page_w, page_h = A4_SHORT, A4_LONG
                if is_landscape:
                    img = img.rotate(90, expand=True)

            elif auto_orientation_mode.startswith("자동: 그림 비율에 맞춰 PDF"):
                # 가로 그림은 가로 A4, 세로 그림은 세로 A4
                if is_landscape:
                    page_w, page_h = A4_LONG, A4_SHORT
                else:
                    page_w, page_h = A4_SHORT, A4_LONG

            elif auto_orientation_mode == "고정: 모든 페이지를 A4 세로로 고정":
                page_w, page_h = A4_SHORT, A4_LONG

            else:  # 고정: 모든 페이지를 A4 가로로 고정
                page_w, page_h = A4_LONG, A4_SHORT

            # 여백을 제외한 실제 인쇄 가능 영역
            content_w = max(100, page_w - (margin_px * 2))
            content_h = max(100, page_h - (margin_px * 2))

            # A4 캔버스 생성
            canvas = Image.new("RGB", (page_w, page_h), bg_color)

            # 비율 유지 맞춤 (Letterbox: 잘림 없이 최대 크기)
            img_ratio = img.width / img.height
            target_ratio = content_w / content_h

            if img_ratio > target_ratio:
                new_w = content_w
                new_h = int(content_w / img_ratio)
            else:
                new_h = content_h
                new_w = int(content_h * img_ratio)

            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            offset_x = margin_px + (content_w - new_w) // 2
            offset_y = margin_px + (content_h - new_h) // 2
            canvas.paste(resized, (offset_x, offset_y))

            processed_pages.append(canvas)

    # 통합 PDF 생성
    pdf_buffer = io.BytesIO()
    if processed_pages:
        first_page = processed_pages[0]
        other_pages = processed_pages[1:] if len(processed_pages) > 1 else []
        first_page.save(
            pdf_buffer,
            format="PDF",
            save_all=True,
            append_images=other_pages,
            resolution=300.0
        )
    pdf_bytes = pdf_buffer.getvalue()
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    st.success(f"총 {len(processed_pages)}장의 이미지가 비율에 맞게 최적화되었습니다.")

    st.markdown("---")
    st.subheader("🖨️ 인쇄 및 다운로드")

    col_print, col_pdf = st.columns([1, 1])

    with col_print:
        print_html = f"""
        <button onclick="printAllPages()" style="
            width: 100%;
            height: 46px;
            background-color: #FF4B4B;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">🖨️ 전체 한 번에 바로 인쇄하기</button>

        <script>
        function printAllPages() {{
            const pdfData = 'data:application/pdf;base64,{b64_pdf}';
            const printWin = window.open(pdfData, '_blank');
            if (printWin) {{
                printWin.onload = function() {{
                    printWin.focus();
                    printWin.print();
                }};
            }} else {{
                alert('팝업 차단을 해제해 주세요.');
            }}
        }}
        </script>
        """
        components.html(print_html, height=55)

    with col_pdf:
        st.download_button(
            label="📄 통합 인쇄용 PDF 다운로드",
            data=pdf_bytes,
            file_name=f"students_work_all_{len(processed_pages)}pages.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    st.markdown("---")
    st.subheader("🖼️ 페이지별 미리보기")
    page_tabs = st.tabs([f"학생 {i+1} (p.{i+1})" for i in range(len(processed_pages))])
    for idx, tab in enumerate(page_tabs):
        with tab:
            st.image(
                processed_pages[idx],
                caption=f"A4 페이지 {idx + 1} - 원본 파일: {uploaded_files[idx].name}",
                use_container_width=True
            )
else:
    st.info("학생들이 제출한 이미지 파일들을 업로드해 주세요.")