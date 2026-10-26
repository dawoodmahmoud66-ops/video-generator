import streamlit as st
import pandas as pd
import PyPDF2
import io
import os
import zipfile

st.set_page_config(page_title="عدّاد صفحات الـ PDF وإنشاء الإكسيل", page_icon="📊", layout="wide")

st.title("📊 أداة حصر واستخراج بيانات ملفات PDF إلى Excel")
st.write("قم برفع ملفات الـ PDF الخاصة بك (أو ملف ZIP يحتوي عليها) وسيتم حصر عدد الصفحات وإنشاء شيت Excel تلقائياً.")

st.divider()

# خيار طريقة الرفع
upload_type = st.radio("اختر طريقة الرفع:", ["رفع مجموعة ملفات PDF دفعة واحدة", "رفع مجلد مضغوط (ZIP) يحتوي على الملفات"])

pdf_data = []

if upload_type == "رفع مجموعة ملفات PDF دفعة واحدة":
    uploaded_files = st.file_uploader(
        "اختر جميع ملفات الـ PDF من الفولدر (Ctrl + A داخل الفولدر):", 
        type=["pdf"], 
        accept_multiple_files=True
    )

    if uploaded_files:
        st.info(f"📁 تم تحديد {len(uploaded_files)} ملف.")
        
        for idx, file in enumerate(uploaded_files, start=1):
            try:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
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

else:
    uploaded_zip = st.file_uploader("ارفع ملف الـ ZIP الذي يحتوي على الفولدر:", type=["zip"])

    if uploaded_zip:
        with zipfile.ZipFile(uploaded_zip, 'r') as z:
            pdf_files = [f for f in z.namelist() if f.lower().endswith('.pdf') and not f.startswith('__MACOSX')]
            st.info(f"📁 تم العثور على {len(pdf_files)} ملف PDF داخل المجلد المضغوط.")

            for idx, file_path in enumerate(pdf_files, start=1):
                try:
                    filename = os.path.basename(file_path)
                    with z.open(file_path) as file:
                        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
                        num_pages = len(pdf_reader.pages)
                        
                        pdf_data.append({
                            "م": idx,
                            "اسم الملف (رقم الملف)": filename,
                            "عدد الصفحات": num_pages
                        })
                except Exception as e:
                    pdf_data.append({
                        "م": idx,
                        "اسم الملف (رقم الملف)": os.path.basename(file_path),
                        "عدد الصفحات": "خطأ في قراءة الملف"
                    })

# عرض الجدول وزر التحميل
if pdf_data:
    df = pd.DataFrame(pdf_data)
    
    # حساب إجمالي الصفحات
    total_pages = df[pd.to_numeric(df["عدد الصفحات"], errors='coerce').notnull()]["عدد الصفحات"].sum()
    
    st.success(f"✅ تم تحليل جميع الملفات بنجاح! إجمالي عدد الصفحات: **{int(total_pages)} صفحة**")
    
    st.subheader("📋 معاينة البيانات:")
    st.dataframe(df, use_container_width=True)

    # إنشاء ملف الإكسيل في الذاكرة للتحميل المباشر
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
