import streamlit as st
import asyncio
import edge_tts
from moviepy import AudioFileClip, ColorClip, concatenate_audioclips
import os
import re

st.set_page_config(page_title="المحلل الذكي للأصوات", page_icon="🎙️")

st.title("🎙️ تحويل النص إلى فيديو مع التمييز التلقائي بين الذكر والأنثى")
st.write("اكتب السكربت وسيقوم النظام بتشخيص واكتشاف الجنس (ذكر/أنثى) تلقائياً لكل سطر بناءً على السياق والضمائر!")

st.info("""
💡 **طرق الكتابة المتاحة:**
1. **التمييز التلقائي عبر السياق والكلمات:** (مثال: `أنا سعيدة جداً اليوم` ➔ أنثى | `أنا سعيد جداً اليوم` ➔ ذكر)
2. **التحديد الصريح المباشر:** (مثال: `[أنثى] مرحباً بك` أو `[ذكر] السلام عليكم`)
3. **نظام الشخصيات:** (مثال: `عبدالحميد: ...` أو `هند: ...`)
""")

script_text = st.text_area("أدخل السكربت هنا:", height=220, placeholder="[ذكر] أهلاً بك يا هند.\nأنا سعيدة جداً بلقائك اليوم.\n[ذكر] وأنا أيضاً مسرور جداً.")

# كلمات مفتاحية للتأنيث والتذكير تلقائياً
FEMININE_INDICATORS = ["سعيدة", "مسرورة", "قالت", "ذهبت", "كنتُ", "تحدثت", "متأكدة", "مهتمة", "أنا أنثى", "بنت", "امرأة"]
MASCULINE_INDICATORS = ["سعيد", "مسرور", "قال", "ذهب", "تحدث", "متأكد", "مهتم", "أنا رجل", "ولد", "رجل"]

def detect_gender(line, default_voice="ar-EG-ShakirNeural"):
    clean_line = line.strip()
    
    # 1. التحديد الصريح بـ [ذكر] أو [أنثى] أو (ذكر) أو (أنثى)
    if re.search(r'\[أنثى\]|\[انثى\]|\(أنثى\)|\(انثى\)', clean_line, re.IGNORECASE):
        text = re.sub(r'\[أنثى\]|\[انثى\]|\(أنثى\)|\(انثى\)', '', clean_line).strip()
        return "ar-EG-SalmaNeural", text
    if re.search(r'\[ذكر\]|\(ذكر\)', clean_line, re.IGNORECASE):
        text = re.sub(r'\[ذكر\]|\(ذكر\)', '', clean_line).strip()
        return "ar-EG-ShakirNeural", text

    # 2. التحديد عبر اسم الشخصية إن وجد
    if ":" in clean_line or "：" in clean_line:
        parts = re.split(r'[:：]', clean_line, maxsplit=1)
        speaker = parts[0].strip()
        content = parts[1].strip()
        
        # فحص صيغة اسم الشخصية أو الكلمات الملحقة بها
        if any(word in speaker for word in ["أنثى", "انثى", "بنت", "سيدة", "دكتورة", "أستاذة"]):
            return "ar-EG-SalmaNeural", content
        if any(word in speaker for word in ["ذكر", "رجل", "ولد", "استاذ", "دكتور"]):
            return "ar-EG-ShakirNeural", content

    # 3. التحليل الذكي للضمائر والكلمات المفتاحية داخل السطر
    text_content = clean_line.split(":")[-1].strip() if ":" in clean_line else clean_line
    
    fem_score = sum(1 for word in FEMININE_INDICATORS if word in text_content)
    masc_score = sum(1 for word in MASCULINE_INDICATORS if word in text_content)

    if fem_score > masc_score:
        return "ar-EG-SalmaNeural", text_content
    elif masc_score > fem_score:
        return "ar-EG-ShakirNeural", text_content

    # الصوت الافتراضي عند عدم وجود مؤشرات حاسمة
    return default_voice, text_content

if st.button("🚀 إنشاء الفيديو"):
    if not script_text.strip():
        st.warning("رجاءً أدخل نص السكربت أولاً!")
    else:
        with st.spinner("جاري تحليل النص، تحديد جنس المتحدث، وتوليد الفيديو..."):
            try:
                lines = [l.strip() for l in script_text.split("\n") if l.strip()]
                audio_files = []

                async def generate_all_audio():
                    for idx, line in enumerate(lines):
                        voice, text = detect_gender(line)
                        if text:
                            file_name = f"temp_{idx}.mp3"
                            communicate = edge_tts.Communicate(text, voice)
                            await communicate.save(file_name)
                            audio_files.append(file_name)

                asyncio.run(generate_all_audio())

                # دمج المقاطع
                clips = [AudioFileClip(f) for f in audio_files]
                combined_audio = concatenate_audioclips(clips)
                combined_audio.write_audiofile("final_audio.mp3")

                duration = combined_audio.duration
                background = ColorClip(size=(1080, 1920), color=(20, 20, 20), duration=duration)
                video = background.with_audio(combined_audio)

                output_path = "generated_video.mp4"
                video.write_videofile(output_path, fps=24)

                # تنظيف
                combined_audio.close()
                for clip in clips: clip.close()
                for f in audio_files:
                    if os.path.exists(f): os.remove(f)

                st.success("تم تحليل الأسطر وتنسيق الأصوات بنجاح! 🎉")
                st.video(output_path)
                
                with open(output_path, "rb") as file:
                    st.download_button("📥 تحميل الفيديو", data=file, file_name="smart_gender_video.mp4", mime="video/mp4")

            except Exception as e:
                st.error(f"حدث خطأ أثناء المعالجة: {e}")
