import streamlit as st
import asyncio
import edge_tts
from moviepy import AudioFileClip, ColorClip, ImageClip, concatenate_videoclips
import os
import re

st.set_page_config(page_title="المخرج السينمائي التلقائي", page_icon="🎬", layout="wide")

st.title("🎬 تحويل السكربت إلى فيديو (مطابقة الصور بأسماء الشخصيات تلقائياً)")
st.write("ارفع صور الشخصيات بأسمائها من جهازك، والصق السكربت بنفس تنسيقه السينمائي ليتم إنشاء الفيديو فوراً!")

col1, col2 = st.columns([2, 1])

with col2:
    st.header("📸 رفع صور الشخصيات")
    st.info("💡 **ملاحظة:** سمّ كل صورة على جهازك باسم الشخصية (مثال: `الأم.png` أو `عبدالحميد.jpg` أو `الأب.png`) ثم ارفعها هنا.")
    
    # رفع مجموعة صور دفعة واحدة
    uploaded_files = st.file_uploader("ارفع كل صور الشخصيات هنا:", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    
    # حفظ الصور وربطها بأسماء الملفات بدون الامتداد
    images_dict = {}
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # استخراج الاسم الصافي للملف بدون الامتداد (مثل: "الأم" من "الأم.jpg")
            raw_name = os.path.splitext(uploaded_file.name)[0].strip().lower()
            save_path = f"temp_img_{uploaded_file.name}"
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            images_dict[raw_name] = save_path
        st.success(f"تم تحميل {len(images_dict)} صورة بنجاح! جاهزة للمطابقة.")

with col1:
    st.header("📜 السكربت السينمائي")
    script_text = st.text_area("أدخل السكربت السينمائي كاملاً هنا:", height=380, placeholder="ضع نص المسلسل أو المشهد هنا...")

# تصفية السكربت ومطابقة الصورة والشخصية
def clean_and_parse_script(raw_text, img_map):
    lines = raw_text.split("\n")
    parsed_dialogues = []
    
    IGNORE_PATTERNS = [
        r'^المشهد', r'^داخلي', r'^خارجي', r'^قطع إلى', r'^نهاية المشهد', 
        r'^مونتاج', r'^ملاحظة', r'^يتبع', r'^النوع:', r'^الحلقة:', r'^المسلسل'
    ]

    current_speaker = "الراوي"

    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("---") or line_str.startswith("-"):
            continue
            
        # تجاهل الإرشادات السينمائية والعناوين
        is_ignored = any(re.search(pat, line_str, re.IGNORECASE) for pat in IGNORE_PATTERNS)
        if is_ignored:
            continue

        voice = "ar-EG-ShakirNeural" # افتراضي ذكر
        speaker_name = ""

        # إذا كان السطر يحتوي على اسم شخصية (مثل: "الأم:" أو "عبدالحميد الطفل:")
        if ":" in line_str or "：" in line_str:
            parts = re.split(r'[:：]', line_str, maxsplit=1)
            speaker_name = parts[0].strip()
            clean_text = parts[1].strip()
            current_speaker = speaker_name
        else:
            clean_text = line_str

        # 1. تحديد الصوت بناءً على الكلمات أو اسم الشخصية
        combined_context = f"{speaker_name} {clean_text}"
        if any(w in combined_context for w in ["الأم", "أم", "هند", "سارة", "مريم", "ماما", "زوجة", "أنثى"]):
            voice = "ar-EG-SalmaNeural"

        # 2. مطابقة صورة الشخصية التلقائية عبر اسم الملف
        selected_image = None
        
        # البحث عن اسم الملف الأقرب لشخصية السطر
        for img_name, img_path in img_map.items():
            # إذا كان اسم الملف موجوداً داخل اسم المتحدث أو السطر
            if img_name in speaker_name.lower() or img_name in combined_context.lower():
                selected_image = img_path
                break

        # إذا لم يجد صورة مطابقة، يبحث عن صورة باسم "الراوي" أو يتركها لخلفية داكنة
        if not selected_image and "الراوي" in img_map:
            selected_image = img_map["الراوي"]

        if clean_text:
            parsed_dialogues.append({
                "text": clean_text,
                "voice": voice,
                "image": selected_image
            })
            
    return parsed_dialogues

if st.button("🚀 إنشاء الفيديو وتطبيق الصور"):
    if not script_text.strip():
        st.warning("رجاءً أدخل السكربت أولاً!")
    else:
        with st.spinner("جاري قراءة الصور، مطابقة الشخصيات، وتوليد المشاهد..."):
            try:
                dialogues = clean_and_parse_script(script_text, images_dict)
                video_clips = []
                temp_audio_files = []

                async def process_segments():
                    for idx, item in enumerate(dialogues):
                        # توليد الصوت
                        audio_path = f"audio_{idx}.mp3"
                        communicate = edge_tts.Communicate(item["text"], item["voice"])
                        await communicate.save(audio_path)
                        temp_audio_files.append(audio_path)

                        audio_clip = AudioFileClip(audio_path)
                        duration = audio_clip.duration

                        # استخدام صورة الشخصية المطابقة أو خلفية لونية
                        if item["image"] and os.path.exists(item["image"]):
                            clip = ImageClip(item["image"]).with_duration(duration)
                            clip = clip.resized(height=1920) # ضبط أبعاد الريلز/الشورتم
                        else:
                            clip = ColorClip(size=(1080, 1920), color=(25, 25, 30), duration=duration)

                        clip = clip.with_audio(audio_clip)
                        video_clips.append(clip)

                asyncio.run(process_segments())

                # دمج المشاهد بالتتابع
                final_video = concatenate_videoclips(video_clips, method="compose")
                output_path = "final_matched_video.mp4"
                final_video.write_videofile(output_path, fps=24)

                # تنظيف الملفات المؤقتة
                for c in video_clips: c.close()
                for f in temp_audio_files:
                    if os.path.exists(f): os.remove(f)

                st.success("تم إنشاء الفيديو ومطابقة صور جميع الشخصيات بنجاح! 🎉")
                st.video(output_path)
                
                with open(output_path, "rb") as file:
                    st.download_button("📥 تحميل الفيديو النهائي", data=file, file_name="matched_drama_video.mp4", mime="video/mp4")

            except Exception as e:
                st.error(f"حدث خطأ أثناء المعالجة: {e}")
