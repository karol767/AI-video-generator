import json
import openai
import requests
from moviepy.editor import *
from gtts import gTTS
import os
from bs4 import BeautifulSoup
import random

# Set up OpenAI API key
openai.api_key = 'your-api-key-here'

def get_person_facts(name):
    prompt = f"Give me 10 interesting facts about {name}. For each fact, provide a title, a brief description, and a detailed text for audio narration."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that provides interesting facts about people."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message['content']

def parse_gpt_response(response):
    facts = []
    lines = response.split('\n')
    current_fact = {}
    for line in lines:
        if line.startswith("Title:"):
            if current_fact:
                facts.append(current_fact)
            current_fact = {"title": line[6:].strip()}
        elif line.startswith("Description:"):
            current_fact["description"] = line[12:].strip()
        elif line.startswith("Text for audio:"):
            current_fact["text_for_audio"] = line[15:].strip()
    if current_fact:
        facts.append(current_fact)
    return facts

def get_wikimedia_image(query):
    url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrnamespace=6&gsrsearch={query}&gsrlimit=1&prop=imageinfo&iiprop=url&format=json"
    response = requests.get(url)
    data = response.json()
    
    if 'query' in data and 'pages' in data['query']:
        for page in data['query']['pages'].values():
            if 'imageinfo' in page:
                return page['imageinfo'][0]['url']
    
    return None

def get_pixabay_video(query):
    pixabay_api_key = 'your-pixabay-api-key-here'  # Replace with your Pixabay API key
    url = f"https://pixabay.com/api/videos/?key={pixabay_api_key}&q={query}&per_page=3"
    response = requests.get(url)
    data = response.json()
    
    if 'hits' in data and len(data['hits']) > 0:
        video = random.choice(data['hits'])
        return video['videos']['medium']['url']
    
    return None

def create_person_data(name):
    gpt_response = get_person_facts(name)
    facts = parse_gpt_response(gpt_response)
    for fact in facts:
        fact["image_src"] = get_wikimedia_image(f"{name} {fact['title']}")
        fact["video_src"] = get_pixabay_video(fact['title'])
    return {"name": name, "facts": facts}

def download_media(url, filename):
    response = requests.get(url)
    with open(filename, 'wb') as f:
        f.write(response.content)

def create_audio(text, filename):
    tts = gTTS(text)
    tts.save(filename)
    return AudioFileClip(filename)

def create_video(person_data):
    clips = []
    for i, fact in enumerate(person_data["facts"]):
        # Create audio from text_for_audio
        audio_file = f"temp_audio_{i}.mp3"
        audio = create_audio(fact["text_for_audio"], audio_file)
        
        # Create video clip
        if fact["video_src"]:
            try:
                video_file = f"temp_video_{i}.mp4"
                download_media(fact["video_src"], video_file)
                video = VideoFileClip(video_file).subclip(0, audio.duration)
            except:
                video = None
        else:
            video = None
        
        if video is None and fact["image_src"]:
            try:
                image_file = f"temp_image_{i}.jpg"
                download_media(fact["image_src"], image_file)
                img = ImageClip(image_file).set_duration(audio.duration)
                video = img.set_audio(audio)
            except:
                video = None
        
        if video is None:
            # If both video and image fail, create a colored background
            video = ColorClip(size=(640, 480), color=(0, 0, 0)).set_duration(audio.duration)
        
        # Add text
        txt_clip = TextClip(fact["title"], fontsize=24, color='white', font='Arial')
        txt_clip = txt_clip.set_pos('top').set_duration(audio.duration)
        
        final_clip = CompositeVideoClip([video, txt_clip]).set_audio(audio)
        clips.append(final_clip)
    
    # Concatenate all clips
    final_video = concatenate_videoclips(clips)
    
    # Write the result to a file
    final_video.write_videofile(f"{person_data['name']}_facts.mp4")
    
    # Clean up temporary files
    for file in os.listdir():
        if file.startswith("temp_"):
            os.remove(file)

# Main execution
if __name__ == "__main__":
    person_name = input("Enter the name of the person: ")
    person_data = create_person_data(person_name)
    
    # Save data to JSON file
    with open(f"{person_name}_data.json", "w") as f:
        json.dump(person_data, f, indent=2)
    
    # Create video
    create_video(person_data)
