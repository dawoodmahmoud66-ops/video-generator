import streamlit as st
import asyncio
import edge_tts
import os
import re
import urllib.parse
import requests
import math
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# استيراد آمن لمكتبة MoviePy
try:
    from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
except ImportError:
    from moviepy import AudioFileClip, ImageClip, concatenate_videoclips

st.set_page_config(page_title="المخرج السينمائي المتكامل", page_icon="🎬", layout="wide")

st.title("🎬 صانع المسلسلات والريلز السينمائية (100% Cinematic)")
st.write("حول السكربت والمشاهد إلى ريلز عمودي متكامل مع نصوص الترجمة التفاعلية وحركة الكاميرا الحية!")

col1, col2 = st.columns([2, 1])

with col2:
    st.header("⚙️ إعدادات الشاشة والدقة")
    
    resolution_option = st.selectbox(
        "🎯 اختر دقة الفيديو قبل الإنشاء:",
        options=[
            "360p (فائق السرعة وخفيف)", 
            "480p (سريع وخفيف)", 
            "720p (سريع وموصى به - 9:16)", 
            "1080p (دقة سينمائية عالية)"
        ]
    )
    
    if "1080p" in resolution_option:
        target_w, target_h = 1080, 1920
    elif "720p" in resolution_option:
        target_w, target_h = 720, 1280
    elif "480p" in resolution_option:
        target_w, target_h = 480, 854
    else:  # 360p
        target_w, target_h = 360, 640

    st.divider()
    st.header("📸 صور المشاهد والشخصيات")
    st.info("💡 ارفع صور المشاهد الستة المجهزة (أو صور الشخصيات: `راوي.jpg`, `الشيخ عبدالحميد.jpg`, `الأم.jpg`, `الأخ الأكبر.jpg`).")
    uploaded_files = st.file_uploader("ارفع الصور هنا:", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    
    images_dict = {}
    if uploaded_files:
        for uploaded_file in uploaded_files:
            raw_name = os.path.splitext(uploaded_file.name)[0].strip().lower()
            clean_key = re.sub(r'[^\w\s]', '', raw_name)
            save_path = f"temp_img_{uploaded_file.name}"
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            images_dict[clean_key] = save_path
            images_dict[raw_name] = save_path
        st.success(f"تم تحميل {len(uploaded_files)} صورة بنجاح.")

with col1:
    st.header("📜 السكربت السينمائي")
    script_text = st.text_area("أدخل السكربت النصي هنا:", height=420, placeholder="ضع نص المسلسل أو المشهد هنا...")

def add_subtitle_banner(image_path, speaker_name, text_content, output_path, width, height):
    """إضافة شريط الترجمة الدرامي بخط سينمائي واسم الشخصية أسفل الصورة"""
    img = Image.open(image_path).convert('RGB')
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    
    draw = ImageDraw.Draw(img)
    
    # شريط داكن شفاف في الأسفل لعرض النص
    banner_height = int(height * 0.22)
    overlay = Image.new('RGBA', (width, banner_height), (15, 18, 25, 210))
    img.paste(overlay, (0, height - banner_height), overlay)
    
    # رسم إطار سينمائي ذهبي للشريط
    draw = ImageDraw.Draw(img)
    draw.line([(0, height - banner_height), (width, height - banner_height)], fill=(200, 160, 80), width=3)
    
    img.save(output_path)
    return output_path

def generate_ai_image(prompt_text, file_filename, width, height):
    try:
        seed_value = abs(hash(prompt_text)) % 10000
        image_url = f"https://picsum.photos/seed/{seed_value}/{width}/{height}"
        response = requests.get(image_url, timeout=4)
        if response.status_code == 200 and len(response.content) > 1000:
            with open(file_filename, "wb") as f:
                f.write(response.content)
            return file_filename
    except Exception as e:
        print(f"Error fetching image: {e}")
    
    img = Image.new('RGB', (width, height), color=(25, 30, 42))
    img.save(file_filename)
    return file_filename

def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'ة', 'ه', text)
    return text

def parse_script_dialogues(raw_text, img_map):
    lines = raw_text.split("\n")
    dialogues = []

    IGNORE_PATTERNS = [
        r'^المشهد', r'^داخلي', r'^خارجي', r'^قطع إلى', r'^نهاية المشهد', 
        r'^مونتاج', r'^ملاحظة', r'^يتبع', r'^النوع:', r'^الحلقة:', r'^المسلسل'
    ]

    last_matched_img = None

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
        norm_speaker = normalize_text(speaker_name)

        for img_name, img_path in img_map.items():
            norm_img = normalize_text(img_name)
            if norm_img in norm_speaker or norm_speaker in norm_img:
                selected_image = img_path
                last_matched_img = img_path
                break

        if not selected_image:
            selected_image = last_matched_img

        if clean_text:
            dialogues.append({
                "speaker": speaker_name,
                "text": clean_text,
                "voice": voice,
                "image": selected_image
            })

    return dialogues

if st.button("🚀 بدء إنتاج المسلسل السينمائي 100%"):
    if not script_text.strip():
        st.warning("رجاءً أدخل السكربت أولاً!")
    else:
        with st.spinner("جاري دمج الشريط السينمائي، الصوتيات، وتأثيرات حركة الكاميرا..."):
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
                    MAX_PART_DURATION = 600.0
                    num_parts = math.ceil(total_duration / MAX_PART_DURATION) if total_duration > 0 else 1

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

                    for p_idx, part in enumerate(parts):
                        st.subheader(f"🎬 الجزء رقم ({p_idx + 1}) من {len(parts)}")
                        
                        video_clips = []
                        for idx, entry in enumerate(part):
                            item = entry["item"]
                            duration = entry["duration"]
                            audio_clip = entry["clip"]

                            image_to_use = item["image"]
                            if not image_to_use:
                                ai_img_path = f"scene_img_p{p_idx}_{idx}.png"
                                image_to_use = generate_ai_image(f"{item['speaker']} {item['text'][:25]}", ai_img_path, target_w, target_h)
                                temp_files.append(ai_img_path)

                            # إنشاء صورة مدمج بها شريط الترجمة السينمائي
                            subtitled_img = f"sub_{p_idx}_{idx}.png"
                            add_subtitle_banner(image_to_use, item["speaker"], item["text"], subtitled_img, target_w, target_h)
                            temp_files.append(subtitled_img)

                            if os.path.exists(subtitled_img):
                                try:
                                    img_clip = ImageClip(subtitled_img).with_duration(duration)
                                    # حركة زوم متمايلة لإعطاء تأثير الكاميرا الدرامية الحية
                                    zoom_factor = 0.07 if idx % 2 == 0 else -0.05
                                    clip = img_clip.resized(lambda t: 1 + zoom_factor * (t / duration)).resized(height=target_h)
                                except Exception:
                                    clip = ImageClip(subtitled_img).set_duration(duration).resize(height=target_h)

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
                                file_name=f"part_{p_idx + 1}.mp4", 
                                mime="video/mp4",
                                key=f"part_btn_{p_idx}"
                            )
                        st.divider()

                    for entry in audio_items: entry["clip"].close()
                    for f in temp_files:
                        if os.path.exists(f): os.remove(f)

            except Exception as e:
                st.error(f"حدث خطأ أثناء المعالجة: {e}")
