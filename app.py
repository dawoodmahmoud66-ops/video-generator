import streamlit as st
import asyncio
import edge_tts
from moviepy import AudioFileClip, ColorClip, TextClip, CompositeVideoClip
import os

st.set_page_config(page_title="مولد الفيديوهات التلقائي", page_icon="🎬")

st.title("🎬 تحويل النص إلى فيديو تلقائياً")
st.write("أدخل السكربت الخاص بك أدناه لإنشاء فيديو بصوت طبيعي وخلفية مخصصة.")

# صندوق إدخال السكربت
script_text = st.text_area("أدخل أو الصق السكربت هنا:", height=150, placeholder="اكتب النص هنا...")

# خيارات الصوت والنسبة
voice_option = st.selectbox("اختر الصوت:", ["ar-EG-SalmaNeural (أنثى)", "ar-EG-ShakirNeural (ذكر)"])
voice_code = "ar-EG-SalmaNeural" if "Salma" in voice_option else "ar-EG-ShakirNeural"

if st.button("🚀 إنشاء الفيديو"):
    if not script_text.strip():
        st.warning("رجاءً أدخل نص السكربت أولاً!")
    else:
        with st.spinner("جاري إنشاء الصوت والفيديو... قد يستغرق ذلك ثوانٍ"):
            try:
                # 1. إنشاء الصوت
                async def generate_audio():
                    communicate = edge_tts.Communicate(script_text, voice_code)
                    await communicate.save("temp_audio.mp3")

                asyncio.run(generate_audio())

                # 2. إنشاء الفيديو
                audio_clip = AudioFileClip("temp_audio.mp3")
                duration = audio_clip.duration

                # خلفية سوداء بتنسيق 9:16 (Shorts/Reels)
                background = ColorClip(size=(1080, 1920), color=(20, 20, 20), duration=duration)
                video = background.with_audio(audio_clip)

                output_path = "generated_video.mp4"
                video.write_videofile(output_path, fps=24)

                st.success("تم إنشاء الفيديو بنجاح! 🎉")
                
                # عرض الفيديو وإمكانية التنزيل
                st.video(output_path)
                with open(output_path, "rb") as file:
                    st.download_button(
                        label="📥 تحميل الفيديو",
                        data=file,
                        file_name="script_video.mp4",
                        mime="video/mp4"
                    )

            except Exception as e:
                st.error(f"حدث خطأ أثناء المعالجة: {e}")