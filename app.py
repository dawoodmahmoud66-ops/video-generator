import streamlit as st
import pandas as pd
import pypdf
import io

st.set_page_config(page_title="حصر ملفات PDF وحساب الصفحات السريع", page_icon="⚡", layout="wide")

st.title("⚡ أداة حصر ملفات PDF السريعة واستخراج البيانات إلى Excel")
st.write("رفع المجلد وقراءة الصفحات بسرعة فائقة بدون تهنيج أو بطء في التحميل.")

st.divider()

uploaded_files = st.file_uploader(
    "📁 اختر الفولدر مباشرة من جهازك (يمكنك رفع ملفات مجتمعة حتى 1 جيجابايت):", 
    type=["pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    total_files = len(uploaded_files)
    st.info(f"📁 تم العثور على {total_files} ملف PDF. جاري الحصر السريع...")
    
    pdf_data = []
    total_pages = 0
    
    # شريط تقدم خفيف وسريع
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, file in enumerate(uploaded_files, start=1):
        try:
            # استخدام io.BytesIO لتسريع قراءة الملف مباشرة دون حفظه
            file_stream = io.BytesIO(file.read())
            pdf_reader = pypdf.PdfReader(file_stream)
            num_pages = len(pdf_reader.pages)
            total_pages += num_pages
            
            pdf_data.append({
                "م": idx,
                "اسم الملف (رقم الملف)": file.name,
                "عدد الصفحات": num_pages
            })
        except Exception:
            pdf_data.append({
                "م": idx,
                "اسم الملف (رقم الملف)": file.name,
                "عدد الصفحات": "خطأ في القراءة"
            })
        
        # تحديث شريط التقدم كل بضع ملفات لتقليل الضغط
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
