import streamlit as st
import asyncio
import edge_tts
import os
import re
import urllib.parse
import requests
import math

# استيراد MoviePy بطريقة متوافقة مع جميع الإصدارات (1.x و 2.x)
try:
    from moviepy.editor import AudioFileClip, ColorClip, ImageClip, concatenate_videoclips
except ImportError:
    from moviepy import AudioFileClip, ColorClip, ImageClip, concatenate_videoclips

st.set_page_config(page_title="المخرج السينمائي الذكي", page_icon="🎬", layout="wide")

st.title("🎬 صانع المسلسلات: التقسيم التلقائي (10 دقائق) وتحميل الأجزاء")
st.write("ضع السكربت كاملاً، وسيتم حساب المدة الزمنية وتقسيمه إلى فيديوهات لا تتجاوز 10 دقائق لتسهيل المعاينة والتحميل!")

col1, col2 = st.columns([2, 1])

with col2:
    st.header("⚙️ إعدادات الإنتاج")
    
    resolution_option = st.selectbox(
        "🎯 اختر دقة الفيديو قبل الإنشاء:",
        options=["480p (سريع جداً وخفيف)", "720p (سريع وموصى به)", "1080p (دقة عالية)"]
    )
    
    if "1080p" in resolution_option:
        target_h, target_w = 1080, 608
    elif "720p" in resolution_option:
        target_h, target_w = 720, 405
    else:
        target_h, target_w = 480, 270

    st.divider()
    st.header("📸 صور الشخصيات (اختياري)")
    uploaded_files = st.file_uploader("ارفع صور الشخصيات هنا:", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    
    images_dict = {}
    if uploaded_files:
        for uploaded_file in uploaded_files:
            raw_name = os.path.splitext(uploaded_file.name)[0].strip().lower()
            save_path = f"temp_img_{uploaded_file.name}"
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            images_dict[raw_name] = save_path
        st.success(f"تم تحميل {len(images_dict)} صورة.")

with col1:
    st.header("📜 السكربت السينمائي")
    script_text = st.text_area("أدخل السكربت النصي هنا:", height=420, placeholder="ضع نص المسلسل أو المشهد هنا...")

def generate_ai_image(prompt_text, file_filename, width, height):
    try:
        encoded_prompt = urllib.parse.quote(f"cinematic drama portrait, Egyptian realistic scene, {prompt_text}")
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
        
        response = requests.get(image_url, timeout=5)
        if response.status_code == 200:
            with open(file_filename, "wb") as f:
                f.write(response.content)
            return file_filename
    except Exception as e:
        print(f"Error generating AI image: {e}")
    return None

def parse_script_dialogues(raw_text, img_map):
    lines = raw_text.split("\n")
    dialogues = []

    IGNORE_PATTERNS = [
        r'^المشهد', r'^داخلي', r'^خارجي', r'^قطع إلى', r'^نهاية المشهد', 
        r'^مونتاج', r'^ملاحظة', r'^يتبع', r'^النوع:', r'^الحلقة:', r'^المسلسل'
    ]

    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("---") or line_str.startswith("-"):
            continue

        if any(re.search(pat, line_str, re.IGNORECASE) for pat in IGNORE_PATTERNS):
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
            dialogues.append({
                "speaker": speaker_name,
                "text": clean_text,
                "voice": voice,
                "image": selected_image
            })

    return dialogues

if st.button("🚀 بدء تحليل وإنشاء الفيديوهات"):
    if not script_text.strip():
        st.warning("رجاءً أدخل السكربت أولاً!")
    else:
        with st.spinner("جاري تحليل السكربت، إنشاء مقاطع الصوت، وتحديد المدة والأجزاء..."):
            try:
                dialogues = parse_script_dialogues(script_text, images_dict)
                if not dialogues:
                    st.error("لم يتم العثور على أسطر حوارية صالحة للرندر!")
                else:
                    audio_items = []
                    temp_files = []

                    async def generate_audios():
                        for idx, item in enumerate(dialogues):
                            audio_path = f"temp_audio_{idx}.mp3"
                            communicate = edge_tts.Communicate(item["text"], item["voice"])
                            await communicate.save(audio_path)
                            temp_files.append(audio_path)

                            clip = AudioFileClip(audio_path)
                            dur = clip.duration
                            
                            audio_items.append({
                                "item": item,
                                "audio_path": audio_path,
                                "clip": clip,
                                "duration": dur
                            })

                    asyncio.run(generate_audios())

                    total_duration = sum(x["duration"] for x in audio_items)
                    MAX_PART_DURATION = 600.0  # 10 دقائق كحد أقصى لكل جزء
                    num_parts = math.ceil(total_duration / MAX_PART_DURATION) if total_duration > 0 else 1

                    total_mins = round(total_duration / 60, 1)
                    st.info(f"📊 **تحليل السكربت:** المدة الإجمالية للسكربت حوالي **{total_mins} دقيقة**. تم تقسيمه إلى **{num_parts} فيديو/أجزاء** (الحد الأقصى لكل فيديو 10 دقائق).")

                    parts = []
                    current_part = []
                    current_part_dur = 0.0

                    for a_item in audio_items:
                        if current_part_dur + a_item["duration"] > MAX_PART_DURATION and current_part:
                            parts.append(current_part)
                            current_part = [a_item]
                            current_part_dur = a_item["duration"]
                        else:
                            current_part.append(a_item)
                            current_part_dur += a_item["duration"]

                    if current_part:
                        parts.append(current_part)

                    ai_generated_cache = {}

                    for p_idx, part in enumerate(parts):
                        st.subheader(f"🎬 الفيديو رقم ({p_idx + 1}) من {len(parts)} - المدة: {round(sum(x['duration'] for x in part)/60, 1)} دقيقة")
                        
                        video_clips = []
                        for idx, entry in enumerate(part):
                            item = entry["item"]
                            duration = entry["duration"]
                            audio_clip = entry["clip"]

                            image_to_use = item["image"]
                            if not image_to_use:
                                speaker = item["speaker"]
                                if speaker in ai_generated_cache:
                                    image_to_use = ai_generated_cache[speaker]
                                else:
                                    ai_img_path = f"ai_img_p{p_idx}_{idx}.png"
                                    generated_file = generate_ai_image(speaker, ai_img_path, target_w, target_h)
                                    if generated_file:
                                        image_to_use = generated_file
                                        ai_generated_cache[speaker] = generated_file
                                        temp_files.append(generated_file)

                            if image_to_use and os.path.exists(image_to_use):
                                # دعم دالتي التكبير/التصغير بحسب إصدار moviepy
                                try:
                                    clip = ImageClip(image_to_use).with_duration(duration).resized(height=target_h)
                                except AttributeError:
                                    clip = ImageClip(image_to_use).set_duration(duration).resize(height=target_h)
                            else:
                                clip = ColorClip(size=(target_w, target_h), color=(25, 25, 30), duration=duration)

                            try:
                                clip = clip.with_audio(audio_clip)
                            except AttributeError:
                                clip = clip.set_audio(audio_clip)
                                
                            video_clips.append(clip)

                        final_video = concatenate_videoclips(video_clips, method="compose")
                        out_file = f"video_part_{p_idx + 1}.mp4"
                        final_video.write_videofile(out_file, fps=15, preset="ultrafast", threads=2)

                        for c in video_clips: c.close()

                        st.video(out_file)
                        with open(out_file, "rb") as file:
                            st.download_button(
                                f"📥 تحميل الفيديو رقم ({p_idx + 1})", 
                                data=file, 
                                file_name=f"video_part_{p_idx + 1}.mp4", 
                                mime="video/mp4",
                                key=f"part_btn_{p_idx}"
                            )
                        st.divider()

                    for entry in audio_items: entry["clip"].close()
                    for f in temp_files:
                        if os.path.exists(f): os.remove(f)

            except Exception as e:
                st.error(f"حدث خطأ أثناء المعالجة: {e}")
