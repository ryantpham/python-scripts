from gtts import gTTS
import playsound
import os

def text_to_speech(text, lang='en'):
    # Create a gTTS object
    tts = gTTS(text=text, lang=lang)
    
    # Save the converted audio to a file
    audio_file = 'output.mp3'
    tts.save(audio_file)
    
    # Play the audio file
    playsound.playsound(audio_file)
    
    # Remove the audio file after playing
    os.remove(audio_file)

if __name__ == "__main__":
    text = input("Enter the text you want to convert to speech: ")
    language = input("Enter the language code (default is 'en' for English): ") or 'en'
    
    text_to_speech(text, language)
