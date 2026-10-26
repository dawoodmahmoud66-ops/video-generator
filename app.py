import streamlit as st
import pandas as pd
import pypdf
import io
import os
import zipfile

st.set_page_config(page_title="حصر ملفات PDF وحساب الصفحات السريع", page_icon="⚡", layout="wide")

st.title("⚡ أداة حصر ملفات PDF السريعة واستخراج البيانات إلى Excel")
st.write("رفع الفولدر (كـ ZIP) أو الملفات وقراءة الصفحات بسرعة فائقة.")

st.divider()

uploaded_file_or_zip = st.file_uploader(
    "📁 ارفع الفولدر مضغوطاً (ZIP) لتحديده بنقرة واحدة من الخارج، أو اختر ملفات الـ PDF:", 
    type=["pdf", "zip"], 
    accept_multiple_files=True
)

if uploaded_file_or_zip:
    pdf_data = []
    total_pages = 0
    file_list = []

    # معالجة الملفات المرفوعة سواء كانت ZIP أو PDF
    for item in uploaded_file_or_zip:
        if item.name.lower().endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(item.read()), 'r') as z:
                for file_info in z.infolist():
                    if file_info.filename.lower().endswith('.pdf') and not file_info.filename.startswith('__MACOSX'):
                        file_bytes = z.read(file_info.filename)
                        clean_name = os.path.basename(file_info.filename)
                        file_list.append((clean_name, io.BytesIO(file_bytes)))
        elif item.name.lower().endswith('.pdf'):
            file_list.append((item.name, io.BytesIO(item.read())))

    total_files = len(file_list)

    if total_files > 0:
        st.info(f"📁 تم العثور على {total_files} ملف PDF. جاري الحصر السريع...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, (filename, file_stream) in enumerate(file_list, start=1):
            try:
                pdf_reader = pypdf.PdfReader(file_stream)
                num_pages = len(pdf_reader.pages)
                total_pages += num_pages
                
                pdf_data.append({
                    "م": idx,
                    "اسم الملف (رقم الملف)": filename,
                    "عدد الصفحات": num_pages
                })
            except Exception:
                pdf_data.append({
                    "م": idx,
                    "اسم الملف (رقم الملف)": filename,
                    "عدد الصفحات": "خطأ في القراءة"
                })
            
            if idx % 5 == 0 or idx == total_files:
                progress_bar.progress(idx / total_files)
                status_text.text(f"تمت معالجة {idx} من أصل {total_files} ملف...")
                
        status_text.empty()
        st.success(f"✅ تم الانتهاء بنجاح! إجمالي عدد الصفحات: **{total_pages} صفحة**")
        
        df = pd.DataFrame(pdf_data)
        
        st.subheader("📋 معاينة بيانات الملفات:")
        st.dataframe(df, use_container_width=True)

        # إنشاء شيت Excel للتحميل المباشر
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='حصر الـ PDF')
        processed_data = output.getvalue()

        st.download_button(
            label="📥 تحميل شيت الإكسيل (Excel)",
            data=processed_data,
            file_name="pdf_pages_count.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("لم يتم العثور على أي ملفات PDF داخل الملف المرفوع.")
