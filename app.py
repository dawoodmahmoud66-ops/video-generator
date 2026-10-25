import streamlit as st
import asyncio
import edge_tts
from moviepy import AudioFileClip, ColorClip, ImageClip, concatenate_videoclips
import os
import re
import urllib.parse
import requests

st.set_page_config(page_title="المخرج السينمائي بالذكاء الاصطناعي", page_icon="🎬", layout="wide")

st.title("🎬 تحويل السكربت إلى فيديو وتوليد صور الشخصيات بالذكاء الاصطناعي")
st.write("الصق السكربت كاملاً، وسيقوم النظام بتوليد صور سينمائية مناسبة لكل شخصية تلقائياً ورندر الفيديو!")

col1, col2 = st.columns([2, 1])

with col2:
    st.header("📸 صور الشخصيات (اختياري)")
    st.info("💡 **ملاحظة:** يمكنك رفع صور يدك، وإذا لم ترفع أي صورة وسيقوم **الذكاء الاصطناعي برسم الصور تلقائياً**!")
    
    uploaded_files = st.file_uploader("ارفع صور الشخصيات هنا (إن وجدت):", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    
    images_dict = {}
    if uploaded_files:
        for uploaded_file in uploaded_files:
            raw_name = os.path.splitext(uploaded_file.name)[0].strip().lower()
            save_path = f"temp_img_{uploaded_file.name}"
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            images_dict[raw_name] = save_path
        st.success(f"تم تحميل {len(images_dict)} صورة يدوياً.")

with col1:
    st.header("📜 السكربت السينمائي")
    script_text = st.text_area("أدخل السكربت النصي هنا:", height=380, placeholder="ضع نص المسلسل أو المشهد هنا...")

def generate_ai_image(prompt_text, file_filename):
    try:
        encoded_prompt = urllib.parse.quote(f"cinematic drama portrait, Egyptian realistic scene, {prompt_text}, highly detailed, 8k resolution")
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true"
        
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            with open(file_filename, "wb") as f:
                f.write(response.content)
            return file_filename
    except Exception as e:
        print(f"Error generating AI image: {e}")
    return None

def clean_and_parse_script(raw_text, img_map):
    lines = raw_text.split("\n")
    parsed_dialogues = []
    
    IGNORE_PATTERNS = [
        r'^المشهد', r'^داخلي', r'^خارجي', r'^قطع إلى', r'^نهاية المشهد', 
        r'^مونتاج', r'^ملاحظة', r'^يتبع', r'^النوع:', r'^الحلقة:', r'^المسلسل'
    ]

    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("---") or line_str.startswith("-"):
            continue
            
        is_ignored = any(re.search(pat, line_str, re.IGNORECASE) for pat in IGNORE_PATTERNS)
        if is_ignored:
            continue

        voice = "ar-EG-ShakirNeural"
        speaker_name = "راوي"

        if ":" in line_str or "：" in line_str:
            parts = re.split(r'[:：]', line_str, maxsplit=1)
            speaker_name = parts[0].strip()
            clean_text = parts[1].strip()
        else:
            clean_text = line_str

        combined_context = f"{speaker_name} {clean_text}"
        
        if any(w in combined_context for w in ["الأم", "أم", "هند", "سارة", "مريم", "ماما", "زوجة", "أنثى"]):
            voice = "ar-EG-SalmaNeural"

        selected_image = None
        for img_name, img_path in img_map.items():
            if img_name in speaker_name.lower() or img_name in combined_context.lower():
                selected_image = img_path
                break

        if clean_text:
            parsed_dialogues.append({
                "speaker": speaker_name,
                "text": clean_text,
                "voice": voice,
                "image": selected_image
            })
            
    return parsed_dialogues

if st.button("🚀 إنشاء الفيديو والتوليد بالذكاء الاصطناعي"):
    if not script_text.strip():
        st.warning("رجاءً أدخل السكربت أولاً!")
    else:
        with st.spinner("جاري تحليل الشخصيات، رسم الصور بالذكاء الاصطناعي، ورندر الفيديو..."):
            try:
                dialogues = clean_and_parse_script(script_text, images_dict)
                video_clips = []
                temp_files = []
                ai_generated_cache = {}

                async def process_segments():
                    for idx, item in enumerate(dialogues):
                        audio_path = f"audio_{idx}.mp3"
                        communicate = edge_tts.Communicate(item["text"], item["voice"])
                        await communicate.save(audio_path)
                        temp_files.append(audio_path)

                        audio_clip = AudioFileClip(audio_path)
                        duration = audio_clip.duration

                        image_to_use = item["image"]
                        
                        if not image_to_use:
                            speaker = item["speaker"]
                            if speaker in ai_generated_cache:
                                image_to_use = ai_generated_cache[speaker]
                            else:
                                ai_img_path = f"ai_img_{idx}.png"
                                generated_file = generate_ai_image(speaker, ai_img_path)
                                if generated_file:
                                    image_to_use = generated_file
                                    ai_generated_cache[speaker] = generated_file
                                    temp_files.append(generated_file)

                        if image_to_use and os.path.exists(image_to_use):
                            clip = ImageClip(image_to_use).with_duration(duration)
                            clip = clip.resized(height=1920)
                        else:
                            clip = ColorClip(size=(1080, 1920), color=(25, 25, 30), duration=duration)

                        clip = clip.with_audio(audio_clip)
                        video_clips.append(clip)

                asyncio.run(process_segments())

                final_video = concatenate_videoclips(video_clips, method="compose")
                output_path = "final_ai_video.mp4"
                final_video.write_videofile(output_path, fps=24)

                for c in video_clips: c.close()
                for f in temp_files:
                    if os.path.exists(f): os.remove(f)

                st.success("تم رسم الصور وتوليد الفيديو بالذكاء الاصطناعي بنجاح! 🎉")
                st.video(output_path)
                
                with open(output_path, "rb") as file:
                    st.download_button("📥 تحميل الفيديو النهائي", data=file, file_name="ai_drama_video.mp4", mime="video/mp4")

            except Exception as e:
                st.error(f"حدث خطأ أثناء المعالجة: {e}")
