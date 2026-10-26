import streamlit as st
import pandas as pd
import pypdf
import io
import os

st.set_page_config(page_title="حصر ملفات PDF وحساب الصفحات", page_icon="📊", layout="wide")

st.title("📊 أداة حصر ملفات PDF واستخراج البيانات إلى Excel")
st.write("اختر الفولدر مباشرة من جهازك، وسيتم قراءة جميع ملفات الـ PDF داخله وحساب عدد صفحاتها تلقائياً!")

st.divider()

# ميزة رفع المجلد بالكامل دون الحاجة للدخول لداخله أو ضغطه
uploaded_files = st.file_uploader(
    "📁 اختر الفولدر من جهازك مباشرة (قم بتحديد المجلد واضغط Upload):", 
    type=["pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    st.info(f"📁 تم العثور على {len(uploaded_files)} ملف PDF داخل المجلد.")
    
    pdf_data = []
    total_pages = 0
    
    progress_bar = st.progress(0)
    
    for idx, file in enumerate(uploaded_files, start=1):
        try:
            # قراءة ملف الـ PDF من الذاكرة وحساب صفحاته
            pdf_reader = pypdf.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            total_pages += num_pages
            
            pdf_data.append({
                "م": idx,
                "اسم الملف (رقم الملف)": file.name,
                "عدد الصفحات": num_pages
            })
        except Exception as e:
            pdf_data.append({
                "م": idx,
                "اسم الملف (رقم الملف)": file.name,
                "عدد الصفحات": "خطأ في قراءة الملف"
            })
            
        progress_bar.progress(idx / len(uploaded_files))
        
    st.success(f"✅ تم تحليل المجلد بنجاح! إجمالي عدد الصفحات: **{total_pages} صفحة**")
    
    df = pd.DataFrame(pdf_data)
    
    st.subheader("📋 معاينة جدول البيانات:")
    st.dataframe(df, use_container_width=True)

    # إنشاء شيت الإكسيل للتحميل
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
